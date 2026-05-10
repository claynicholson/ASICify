"""Attention building blocks: int softmax + KV cache helpers.

The full attention block in hardware is a composition of:
  - Q, K, V linear projections    (worker.kernels.quantize Linear path)
  - K-cache, V-cache               (BRAM modules emitted from kv_cache.v.j2)
  - Q * K^T integer matmul         (linear_layer pattern, dynamic operand)
  - Softmax with LUT-based exp     (this module's softmax_int)
  - Softmax * V                     (linear_layer pattern)
  - Output projection               (worker.kernels.quantize Linear path)

The auto-parser does not yet recognize an entire attention block as a unit,
so production use today involves wiring four `layer_<symbol>` modules and
this softmax submodule by hand at the top level. The kernel functions here
let unit tests verify each piece in isolation.
"""

from __future__ import annotations

import math

import torch


# ---------------------------------------------------------------------------
# Softmax LUT
# ---------------------------------------------------------------------------


def build_softmax_lut(input_bits: int = 8, output_q: int = 15) -> torch.Tensor:
    """LUT mapping integer logit-difference -> exp(d), as Q-format int.

    The LUT covers d in [-(2^input_bits - 1), 0]. Indices 0..255 (for 8-bit)
    correspond to d = -255..0 in even steps of 1.

    Output is unsigned Q15 in int32 (range [0, 2^output_q]). exp(0)=1.0 is
    represented as 2^output_q.
    """
    n = 1 << input_bits
    d = torch.arange(-(n - 1), 1, dtype=torch.float32)
    e = torch.exp(d)
    return (e * (1 << output_q)).round().clamp(0, (1 << output_q)).to(torch.int32)


_DEFAULT_LUT = build_softmax_lut()


def softmax_int(logits_int32: torch.Tensor, lut: torch.Tensor | None = None) -> torch.Tensor:
    """Integer softmax that mirrors the hardware module.

    Steps:
      1. Find max(logits) (int32).
      2. Compute d = logits - max  (always <= 0, fits in int32).
      3. Saturate d below -(N-1) where N is the LUT size.
      4. Look up exp_q15[i] = LUT[d + (N-1)].
      5. sum = sum(exp_q15)
      6. weights_q15[i] = (exp_q15[i] << 15) / sum     (Q15 normalized)

    Returns Q15 unsigned weights in int32 of the same shape as input.
    """
    if logits_int32.dim() != 1:
        raise ValueError("softmax_int expects 1D logits")
    if lut is None:
        lut = _DEFAULT_LUT
    n = lut.numel()
    max_val = logits_int32.max()
    d = (logits_int32 - max_val).clamp(min=-(n - 1), max=0)
    idx = (d + (n - 1)).to(torch.long)
    exp_q15 = lut[idx]
    total = exp_q15.sum().clamp_min(1)
    weights_q15 = ((exp_q15.to(torch.int64) << 15) // total.to(torch.int64)).to(torch.int32)
    return weights_q15


# ---------------------------------------------------------------------------
# Reference attention forward (single head)
# ---------------------------------------------------------------------------


def attention_int_forward(
    q_int32: torch.Tensor,
    k_int32: torch.Tensor,
    v_int32: torch.Tensor,
) -> torch.Tensor:
    """Single-head dot-product attention in integer form.

    Args:
        q_int32: shape (head_dim,) int32, the query for one position.
        k_int32: shape (seq_len, head_dim) int32, all keys including past.
        v_int32: shape (seq_len, head_dim) int32, all values including past.

    Returns:
        context: shape (head_dim,) int32 — the attended value.

    Implementation matches what the RTL does:
      1. logits = K @ Q              (int64)
      2. logits >>= log2(head_dim)/2  via approximate scale by sqrt(d)
      3. softmax (int)
      4. ctx[d] = sum_t weights_q15[t] * v[t, d] >> 15
    """
    seq_len, head_dim = k_int32.shape
    if q_int32.shape != (head_dim,):
        raise ValueError("q shape mismatch")
    if v_int32.shape != (seq_len, head_dim):
        raise ValueError("v shape mismatch")

    q64 = q_int32.to(torch.int64)
    k64 = k_int32.to(torch.int64)
    v64 = v_int32.to(torch.int64)

    logits = k64 @ q64  # (seq_len,)
    # Right-shift by log2(sqrt(head_dim)) ≈ ceil(log2(head_dim) / 2)
    shift = max(1, int(math.ceil(math.log2(max(head_dim, 2)) / 2)))
    logits = logits >> shift

    weights_q15 = softmax_int(logits.to(torch.int32))

    # ctx = (weights @ v) >> 15
    ctx = ((weights_q15.to(torch.int64).unsqueeze(0) @ v64) >> 15).squeeze(0)
    return ctx.to(torch.int32)
