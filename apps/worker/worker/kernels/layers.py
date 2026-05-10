"""Non-linear layer kernels: LayerNorm, Embedding, Attention.

Each kernel returns a `Quantized<Layer>` dataclass that mirrors the integer
state used by the generated Verilog. The pack module reads these and emits
matching `localparam` declarations.

Numerical conventions:
  - LayerNorm gamma/beta are stored as Q15 fixed-point signed int16
    (one sign bit + 15 fractional bits). The runtime applies them after the
    integer normalize step.
  - Embedding is a literal int8 lookup table of shape (vocab, dim). At
    inference, integer token id -> int8 row.
  - Attention reuses three QuantizedLinear records (Q, K, V) plus an output
    projection, plus a softmax LUT. The softmax LUT is a 256-entry int16
    table mapping integer logit-difference to a normalized weight.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from worker.kernels.quantize import QuantizedLinear, quantize_linear_int8


# ---------------------------------------------------------------------------
# LayerNorm
# ---------------------------------------------------------------------------


@dataclass
class QuantizedLayerNorm:
    """LayerNorm with Q15 gamma/beta stored as int32 (range covers gamma > 1).

    Storage uses int32 with 15 fractional bits, so gamma can comfortably hold
    values up to ~65k (float). Real layernorm gammas init near 1.0 and rarely
    exceed a few units.

    Verilog computes:
        mean   = sum(x) / N
        var    = sum((x - mean)^2) / N
        norm   = (x - mean) * inv_std_q15 >> 15
        y      = (norm * gamma_q15 + beta_q15) >> 15
    """

    gamma_q15: torch.Tensor   # int32, shape (dim,)
    beta_q15: torch.Tensor    # int32, shape (dim,)
    eps_q15: int              # int, eps * 2^15
    dim: int


def quantize_layernorm(module: torch.nn.LayerNorm) -> QuantizedLayerNorm:
    dim = module.normalized_shape[0]
    gamma = (
        module.weight.detach().to(torch.float32)
        if module.weight is not None
        else torch.ones(dim)
    )
    beta = (
        module.bias.detach().to(torch.float32)
        if module.bias is not None
        else torch.zeros(dim)
    )
    eps = float(module.eps)

    gamma_q15 = (
        (gamma * (1 << 15)).round().clamp(-(2**31), 2**31 - 1).to(torch.int32)
    )
    beta_q15 = (
        (beta * (1 << 15)).round().clamp(-(2**31), 2**31 - 1).to(torch.int32)
    )
    eps_q15 = int(round(eps * (1 << 15)))
    return QuantizedLayerNorm(gamma_q15=gamma_q15, beta_q15=beta_q15, eps_q15=eps_q15, dim=dim)


def layernorm_int_forward(x_int8: torch.Tensor, qln: QuantizedLayerNorm) -> torch.Tensor:
    """Bit-exact LayerNorm in fixed-point.

    Promotes to int32 for sums, computes mean+variance in Q15, and outputs
    int8 again. The exact arithmetic is what the Verilog does.

    Returns int8 of shape (dim,).
    """
    if x_int8.dim() != 1 or x_int8.shape[0] != qln.dim:
        raise ValueError(f"x must be 1D with shape ({qln.dim},)")

    x32 = x_int8.to(torch.int64)
    n = qln.dim
    sum_x = x32.sum().item()
    mean = sum_x // n  # truncating integer division to match HW
    centered = x32 - mean
    var = (centered * centered).sum().item() // n
    # var is in (int8)^2 units; eps_q15 is in fp units (Q15). Convert eps to
    # the same scale: eps_in_int_units = eps_q15 * 2^-15 -> negligible at int8 scale.
    # We just add eps_q15 / 2^15 truncated to int as a small constant.
    var_term = var + max(1, qln.eps_q15 // (1 << 15))

    # 1 / sqrt(var) in Q15.
    inv_std_float = 1.0 / (float(var_term) ** 0.5)
    inv_std_q15 = int(round(inv_std_float * (1 << 15)))

    # norm = centered * inv_std_q15 (>>15 to keep Q0)
    norm = (centered * inv_std_q15) >> 15

    # y = (norm * gamma_q15 + beta_q15) >> 15  (one fixed-point multiply + add)
    y = (norm * qln.gamma_q15.to(torch.int64) + qln.beta_q15.to(torch.int64)) >> 15

    # Saturate to int8
    return y.clamp(-128, 127).to(torch.int8)


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


@dataclass
class QuantizedEmbedding:
    """Embedding stored as an int8 lookup table per vocabulary entry."""

    table_int8: torch.Tensor  # shape (vocab, dim), dtype int8
    scale: torch.Tensor       # shape (dim,), float32 — per-dim scale (column scale)
    vocab_size: int
    embedding_dim: int


def quantize_embedding(module: torch.nn.Embedding) -> QuantizedEmbedding:
    """Per-column INT8: each embedding dimension gets its own scale.

    This matches the convention for Linear layers where each output channel
    has its own scale.
    """
    w = module.weight.detach().to(torch.float32)  # (vocab, dim)
    vocab, dim = w.shape
    max_abs = w.abs().amax(dim=0).clamp_min(1e-12)  # (dim,)
    scale = max_abs / 127.0
    table = (w / scale.unsqueeze(0)).round().clamp(-128, 127).to(torch.int8)
    return QuantizedEmbedding(
        table_int8=table,
        scale=scale.to(torch.float32),
        vocab_size=vocab,
        embedding_dim=dim,
    )


def embedding_int_forward(token_ids: torch.Tensor, qe: QuantizedEmbedding) -> torch.Tensor:
    """Look up int8 rows. Returns int8 of shape (seq_len, dim)."""
    if token_ids.dim() != 1:
        raise ValueError("token_ids must be 1D")
    return qe.table_int8[token_ids]


# ---------------------------------------------------------------------------
# Attention (single head, simplified)
# ---------------------------------------------------------------------------


@dataclass
class QuantizedAttention:
    """Single-head attention block.

    Stored as four QuantizedLinear records (Q, K, V, O) plus a softmax LUT.
    The Verilog template instantiates four `layer_*` modules and a small
    softmax submodule that does an integer max-subtract + exp-LUT + normalize.
    """

    q_proj: QuantizedLinear
    k_proj: QuantizedLinear
    v_proj: QuantizedLinear
    o_proj: QuantizedLinear
    embed_dim: int
    num_heads: int
    head_dim: int
    softmax_lut: torch.Tensor  # int16, length 256, mapping logit-diff -> exp


def _build_softmax_lut() -> torch.Tensor:
    """LUT for exp(d) with d in [-8, 0] mapped to 256 entries.

    The Verilog softmax computes max-subtract, then looks up exp(d - d_max)
    in this table. Index 0 = exp(-8) ~= 0.0003, index 255 = exp(0) = 1.0.
    Values in Q15 unsigned int16.
    """
    d = torch.linspace(-8.0, 0.0, 256)
    e = torch.exp(d)
    return (e * (1 << 15)).round().clamp(0, 2**15 - 1).to(torch.int16)


def quantize_attention(
    q_weight: torch.Tensor,
    k_weight: torch.Tensor,
    v_weight: torch.Tensor,
    o_weight: torch.Tensor,
    q_bias: torch.Tensor | None,
    k_bias: torch.Tensor | None,
    v_bias: torch.Tensor | None,
    o_bias: torch.Tensor | None,
    embed_dim: int,
    num_heads: int,
) -> QuantizedAttention:
    return QuantizedAttention(
        q_proj=quantize_linear_int8(q_weight, q_bias),
        k_proj=quantize_linear_int8(k_weight, k_bias),
        v_proj=quantize_linear_int8(v_weight, v_bias),
        o_proj=quantize_linear_int8(o_weight, o_bias),
        embed_dim=embed_dim,
        num_heads=num_heads,
        head_dim=embed_dim // num_heads,
        softmax_lut=_build_softmax_lut(),
    )
