"""Tests for tensor -> SystemVerilog constant packing."""

from __future__ import annotations

import re

import torch

from worker.kernels.pack import (
    bias_q_array_to_sv,
    int8_array_to_sv,
    pack_layer,
    scale_q15_array_to_sv,
)
from worker.kernels.quantize import quantize_linear_int8


def test_int8_array_to_sv_round_trip():
    """The emitted Verilog literal contains every int value from the source tensor."""
    t = torch.tensor([[1, -127, 0], [127, -1, 42]], dtype=torch.int8)
    sv = int8_array_to_sv("W_test", t)
    assert "reg signed [7:0] W_test [0:1][0:2];" in sv
    assert "initial begin" in sv
    # Values present and signed correctly.
    for v in [1, 127, 42]:
        assert f"8'sd{v}" in sv
    for v in [127, 1]:
        assert f"-8'sd{v}" in sv
    assert "8'sd0" in sv


def test_int8_array_to_sv_rejects_non_int8():
    t = torch.tensor([[1, 2]], dtype=torch.float32)
    try:
        int8_array_to_sv("W", t)
    except ValueError:
        return
    raise AssertionError("expected ValueError on non-int8 tensor")


def test_scale_q31_array_in_range():
    """All emitted scale values fit in unsigned 31 bits."""
    scale = torch.tensor([0.0001, 0.5, 0.999, 1e-8])
    sv = scale_q15_array_to_sv("S", scale)
    nums = [int(m) for m in re.findall(r"32'd(\d+)", sv)]
    assert len(nums) == 4
    assert all(0 <= n < (1 << 31) for n in nums)
    # 0.5 * 2^31 = 1073741824
    assert 1073741824 in nums


def test_bias_q_handles_none():
    sv = bias_q_array_to_sv("B", None, torch.tensor([0.1]))
    assert "no bias" in sv


def test_pack_layer_emits_all_three_arrays():
    torch.manual_seed(0)
    q = quantize_linear_int8(torch.randn(4, 3), torch.randn(4))
    out = pack_layer("test", q)
    assert "W_test" in out
    assert "SCALE_Q31_test" in out
    assert "BIAS_Q_test" in out
    # Comment header with shape info is present.
    assert "in=3" in out and "out=4" in out
