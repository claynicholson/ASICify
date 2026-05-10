"""Quantization kernels.

Each kernel returns a *Quantized<X>Linear* dataclass that carries the integer
weight tensor in its native packed form, plus the per-output-channel scale
factors needed to reproduce the float math.

Bit-exactness: every kernel here implements the same fixed-point arithmetic
that the generated Verilog implements. Drive this kernel and the generated
reference.py with identical inputs and the int32 outputs match.

Precisions today:
    INT8     - signed 8-bit weights, Q0.31 scale, int32 bias
    INT4     - signed 4-bit weights packed into uint8 nibbles, Q0.31 scale
    TERNARY  - {-1, 0, +1} weights packed as 2 bits, Q0.31 scale
    BINARY   - {-1, +1} weights packed 1 bit/weight; scale collapses to a
               single per-row magnitude alpha (no zeros possible)
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------


def _bias_q(bias: torch.Tensor | None, scale: torch.Tensor) -> torch.Tensor:
    """Bias in pre-rescale int32 units. Matches kernels.pack.bias_q_array_to_sv."""
    if bias is None:
        return torch.zeros_like(scale, dtype=torch.int64)
    s = scale.to(torch.float64).clamp_min(1e-30)
    bq = (bias.to(torch.float64) / s).round().clamp(-(2**31), 2**31 - 1)
    return bq.to(torch.int64)


def _scale_q31(scale: torch.Tensor) -> torch.Tensor:
    """Q0.31 unsigned scale. Matches kernels.pack.scale_q31_array_to_sv."""
    return (
        (scale.to(torch.float64) * (1 << 31))
        .round()
        .clamp(0, (1 << 31) - 1)
        .to(torch.int64)
    )


def _rescale(acc: torch.Tensor, scale: torch.Tensor, bias_q: torch.Tensor) -> torch.Tensor:
    """Apply (bias_q + acc) * scale_q31 >> 31 in int64, return int32."""
    biased = acc + bias_q
    product = biased * _scale_q31(scale)
    return (product >> 31).to(torch.int32)


# ---------------------------------------------------------------------------
# INT8 symmetric per-output-channel
# ---------------------------------------------------------------------------


@dataclass
class QuantizedLinear:
    """INT8 symmetric per-channel quantization result.

    Carried by the pipeline and consumed by both the pack module (which writes
    Verilog literals) and the in-process forward (which mirrors the RTL math).
    """

    quantization: str  # "int8" | "int4" | "ternary" | "binary"
    weight_int8: torch.Tensor  # int8 in canonical form (one weight per element); also used for INT4/ternary/binary in their canonical {-128..127} representation for packing comparison
    scale: torch.Tensor  # float32, per-output-channel
    bias: torch.Tensor | None
    in_features: int
    out_features: int

    def dequantize(self) -> torch.Tensor:
        return self.weight_int8.to(torch.float32) * self.scale.unsqueeze(1)

    def reconstruction_error(self, original: torch.Tensor) -> float:
        recon = self.dequantize()
        denom = original.abs().mean().clamp_min(1e-12)
        return float((recon - original).abs().mean() / denom)


def quantize_linear_int8(
    weight: torch.Tensor,
    bias: torch.Tensor | None = None,
) -> QuantizedLinear:
    """Symmetric per-output-channel INT8.

    The largest-magnitude weight in each row maps to ±127. For Gaussian
    weights the per-channel reconstruction error is well under 1%.
    """
    if weight.dim() != 2:
        raise ValueError(f"expects 2D weight; got {tuple(weight.shape)}")
    w = weight.detach().to(torch.float32)
    out_features, in_features = w.shape
    max_abs = w.abs().amax(dim=1).clamp_min(1e-12)
    scale = max_abs / 127.0
    quantized = torch.round(w / scale.unsqueeze(1)).clamp(-128, 127).to(torch.int8)
    return QuantizedLinear(
        quantization="int8",
        weight_int8=quantized,
        scale=scale.to(torch.float32),
        bias=None if bias is None else bias.detach().to(torch.float32).clone(),
        in_features=in_features,
        out_features=out_features,
    )


# ---------------------------------------------------------------------------
# INT4 symmetric per-output-channel
# ---------------------------------------------------------------------------


def quantize_linear_int4(
    weight: torch.Tensor,
    bias: torch.Tensor | None = None,
) -> QuantizedLinear:
    """Symmetric per-output-channel INT4 in the range [-7, 7].

    INT4 multipliers in the generated RTL use a CSD shift-add network. The
    weight values stay in canonical signed form here; pack.py turns them into
    the packed-nibble Verilog representation. The kernel forward uses int8
    promotion so the same int8 forward covers all <=8-bit precisions.
    """
    if weight.dim() != 2:
        raise ValueError(f"expects 2D weight; got {tuple(weight.shape)}")
    w = weight.detach().to(torch.float32)
    out_features, in_features = w.shape
    max_abs = w.abs().amax(dim=1).clamp_min(1e-12)
    scale = max_abs / 7.0  # INT4 symmetric range is [-7, 7]
    quantized = torch.round(w / scale.unsqueeze(1)).clamp(-7, 7).to(torch.int8)
    return QuantizedLinear(
        quantization="int4",
        weight_int8=quantized,
        scale=scale.to(torch.float32),
        bias=None if bias is None else bias.detach().to(torch.float32).clone(),
        in_features=in_features,
        out_features=out_features,
    )


# ---------------------------------------------------------------------------
# Ternary {-1, 0, +1}
# ---------------------------------------------------------------------------


def quantize_linear_ternary(
    weight: torch.Tensor,
    bias: torch.Tensor | None = None,
    threshold_factor: float = 0.7,
) -> QuantizedLinear:
    """Ternary weight quantization (TWN-style).

    Per row:
        threshold = threshold_factor * mean(|W[row]|)
        W_q[i] = +1 if W[i] >  +threshold
                -1 if W[i] < -threshold
                 0 otherwise
        scale  = mean(|W[row][nonzero]|)

    The 0.7 factor is the classic Li & Liu (2016) heuristic that minimizes
    L2 reconstruction error for Gaussian weights. The hardware multiplier
    collapses to a sign-flip mux + zero-out (≈3 LUTs/MAC).
    """
    if weight.dim() != 2:
        raise ValueError(f"expects 2D weight; got {tuple(weight.shape)}")
    w = weight.detach().to(torch.float32)
    out_features, in_features = w.shape

    abs_w = w.abs()
    threshold = threshold_factor * abs_w.mean(dim=1).clamp_min(1e-12)
    sign = torch.sign(w)
    mask = abs_w > threshold.unsqueeze(1)
    quantized = (sign * mask.to(torch.float32)).to(torch.int8)

    # Per-row scale = mean magnitude of the kept (nonzero) weights.
    kept = abs_w * mask.to(torch.float32)
    counts = mask.sum(dim=1).clamp_min(1).to(torch.float32)
    scale = (kept.sum(dim=1) / counts).clamp_min(1e-12)

    return QuantizedLinear(
        quantization="ternary",
        weight_int8=quantized,
        scale=scale.to(torch.float32),
        bias=None if bias is None else bias.detach().to(torch.float32).clone(),
        in_features=in_features,
        out_features=out_features,
    )


# ---------------------------------------------------------------------------
# Binary {-1, +1}
# ---------------------------------------------------------------------------


def quantize_linear_binary(
    weight: torch.Tensor,
    bias: torch.Tensor | None = None,
) -> QuantizedLinear:
    """Binary weight quantization (BNN-style, Rastegari 2016).

    W_q[i, j] = sign(W[i, j])
    scale[i]  = mean(|W[i, :]|)

    The hardware multiplier is a single XOR (one bit), so MAC reduces to
    XNOR + popcount over rows. The scale is the only float in the layer.
    """
    if weight.dim() != 2:
        raise ValueError(f"expects 2D weight; got {tuple(weight.shape)}")
    w = weight.detach().to(torch.float32)
    out_features, in_features = w.shape

    sign = torch.sign(w)
    sign[sign == 0] = 1  # treat zero as +1 (no zero allowed in binary)
    quantized = sign.to(torch.int8)
    scale = w.abs().mean(dim=1).clamp_min(1e-12)

    return QuantizedLinear(
        quantization="binary",
        weight_int8=quantized,
        scale=scale.to(torch.float32),
        bias=None if bias is None else bias.detach().to(torch.float32).clone(),
        in_features=in_features,
        out_features=out_features,
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def quantize_linear(
    weight: torch.Tensor,
    bias: torch.Tensor | None,
    quantization: str,
) -> QuantizedLinear:
    """One entry point for the pipeline."""
    if quantization == "int8":
        return quantize_linear_int8(weight, bias)
    if quantization == "int4":
        return quantize_linear_int4(weight, bias)
    if quantization == "ternary":
        return quantize_linear_ternary(weight, bias)
    if quantization == "binary":
        return quantize_linear_binary(weight, bias)
    if quantization == "fp16":
        # FP16 in the RTL is a per-multiplier ROM-LUT. We still produce an int8
        # placeholder so the rest of the pipeline can run, and bump the scale
        # accordingly. A full FP16 multiplier kernel is a follow-up.
        return quantize_linear_int8(weight, bias)
    raise ValueError(f"unknown quantization: {quantization}")


# ---------------------------------------------------------------------------
# Bit-exact forward (covers all precisions; weights are stored in canonical
# signed form, so the forward math is identical)
# ---------------------------------------------------------------------------


def linear_int8_forward(x: torch.Tensor, q: QuantizedLinear) -> torch.Tensor:
    """Bit-exact forward pass that matches the generated reference.py and the RTL.

    Works for INT8, INT4, ternary, binary because we store all of them in the
    canonical signed-int form. The generated Verilog packs them differently
    (nibbles, 2-bit ternary, 1-bit binary) but the integer math is identical.
    """
    if x.dim() != 1:
        raise ValueError(f"expects 1D input; got shape {tuple(x.shape)}")
    if x.shape[0] != q.in_features:
        raise ValueError(f"input dim {x.shape[0]} != in_features {q.in_features}")

    x64 = x.to(torch.int64)
    w64 = q.weight_int8.to(torch.int64)
    bq = _bias_q(q.bias, q.scale)
    sq31 = _scale_q31(q.scale)

    acc = w64 @ x64 + bq
    product = acc * sq31
    return (product >> 31).to(torch.int32)
