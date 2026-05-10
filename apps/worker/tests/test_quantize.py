"""Tests for INT8 symmetric per-channel quantization."""

from __future__ import annotations

import torch

from worker.kernels.quantize import (
    QuantizedLinear,
    linear_int8_forward,
    quantize_linear_int8,
)


def test_quantize_shapes_and_dtypes():
    w = torch.randn(8, 4)
    b = torch.randn(8)
    q = quantize_linear_int8(w, b)
    assert isinstance(q, QuantizedLinear)
    assert q.weight_int8.shape == (8, 4)
    assert q.weight_int8.dtype == torch.int8
    assert q.scale.shape == (8,)
    assert q.scale.dtype == torch.float32
    assert q.bias is not None and q.bias.shape == (8,)
    assert q.in_features == 4 and q.out_features == 8


def test_quantize_scale_concentrates_on_max():
    """Per-row max-abs gets mapped to ±127 exactly."""
    w = torch.tensor([[0.1, 0.5, -2.0, 1.5], [0.3, 3.0, 0.05, -0.05]])
    q = quantize_linear_int8(w, None)
    # Row 0: max abs is 2.0, so 2.0 / scale[0] should round to 127.
    assert q.weight_int8[0].abs().max().item() == 127
    assert q.weight_int8[1].abs().max().item() == 127


def test_dequantization_error_is_small():
    torch.manual_seed(0)
    w = torch.randn(64, 32)
    q = quantize_linear_int8(w, None)
    err = q.reconstruction_error(w)
    # Per-channel INT8 should be well under 1% normalized error on Gaussian weights.
    assert err < 0.01, f"reconstruction error {err} too large"


def test_zero_row_handled():
    w = torch.zeros(2, 3)
    w[1] = torch.tensor([1.0, -2.0, 0.5])
    q = quantize_linear_int8(w, None)
    # Zero row should produce all-zero quantized weights without NaN.
    assert (q.weight_int8[0] == 0).all()
    assert q.scale[0] > 0  # never exactly zero (clamped)


def test_forward_matches_reference_arithmetic():
    """The kernel's forward pass must equal the bit-level fixed-point ops.

    We hand-compute the expected int32 output and assert exact equality.
    """
    torch.manual_seed(42)
    in_features, out_features = 5, 3
    w = torch.randn(out_features, in_features) * 0.5
    b = torch.randn(out_features) * 0.1
    q = quantize_linear_int8(w, b)

    x_int8 = torch.tensor([12, -34, 0, 7, -125], dtype=torch.int8)
    y = linear_int8_forward(x_int8, q)

    # Recompute the same thing the Verilog does.
    bias_q = (b.to(torch.float64) / q.scale.to(torch.float64)).round().to(torch.int64)
    scale_q31 = (q.scale.to(torch.float64) * (1 << 31)).round().to(torch.int64)

    x64 = x_int8.to(torch.int64)
    w64 = q.weight_int8.to(torch.int64)
    acc = w64 @ x64 + bias_q
    expected = ((acc * scale_q31) >> 31).to(torch.int32)

    assert torch.equal(y, expected)


def test_forward_output_dtype_and_shape():
    torch.manual_seed(0)
    q = quantize_linear_int8(torch.randn(7, 11), torch.randn(7))
    x = torch.randint(-50, 50, (11,), dtype=torch.int8)
    y = linear_int8_forward(x, q)
    assert y.shape == (7,)
    assert y.dtype == torch.int32
