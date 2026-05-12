"""Tests for the FP16 quantization path."""

from __future__ import annotations

from pathlib import Path

import importlib.util
import numpy as np
import torch
from torch import nn

from worker.cli import _default_config
from worker.kernels.quantize import (
    linear_fp16_forward,
    linear_int8_forward,
    quantize_linear,
    quantize_linear_fp16,
)
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory
from worker.types import CompressionConfig, DecompositionConfig, SparsityConfig


def _config_fp16() -> CompressionConfig:
    return CompressionConfig(
        quantization="fp16",
        sparsity=SparsityConfig(type="none", ratio=0.0),
        decomposition=DecompositionConfig(type="none"),
    )


def test_fp16_kernel_stores_float16():
    torch.manual_seed(0)
    w = torch.randn(8, 4)
    q = quantize_linear_fp16(w, None)
    assert q.quantization == "fp16"
    assert q.weight_int8.dtype == torch.float16
    assert q.weight_int8.shape == (8, 4)


def test_fp16_dequantize_is_close_to_original():
    torch.manual_seed(0)
    w = torch.randn(16, 32)
    q = quantize_linear_fp16(w, None)
    err = q.reconstruction_error(w)
    # FP16 has about 11 bits of mantissa; relative error should be tiny.
    assert err < 1e-3


def test_fp16_forward_dispatches_via_linear_int8_forward():
    """The unified forward function should route fp16 to linear_fp16_forward."""
    torch.manual_seed(0)
    w = torch.randn(4, 8) * 0.3
    q = quantize_linear(w, torch.zeros(4), "fp16")
    x = torch.tensor([1, -2, 3, -4, 5, -6, 7, -8], dtype=torch.int8)
    y_unified = linear_int8_forward(x, q)
    y_direct = linear_fp16_forward(x, q)
    assert torch.equal(y_unified, y_direct)
    assert y_unified.dtype == torch.int32


def test_fp16_pipeline_renders_separate_template(tmp_path: Path):
    """The fp16 path should render fp16_layer.v.j2, not linear_layer.v.j2."""
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(8, 4)

        def forward(self, x):
            return self.fc(x)

    graph = parse_module(M(), name="m", task="classification")
    graph = quantize_graph(graph, _config_fp16())
    out_dir = tmp_path / "rtl"
    render_to_directory(graph, _config_fp16(), out_dir)

    rtl = (out_dir / "modules/layer_fc.v").read_text()
    # Should reference the fp16 paths.
    assert "fp16_to_real" in rtl or "shortrealtobits" in rtl
    weights_vh = (out_dir / "weights.vh").read_text()
    # FP16 weights are emitted as 16'h.... literals.
    assert "16'h" in weights_vh


def test_fp16_reference_matches_kernel_bit_exact(tmp_path: Path):
    """The generated reference.py for fp16 should produce identical int32 output
    to linear_fp16_forward on the same input.
    """
    torch.manual_seed(7)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(8, 4)

        def forward(self, x):
            return self.fc(x)

    graph = parse_module(M(), name="m", task="classification")
    graph = quantize_graph(graph, _config_fp16())
    out_dir = tmp_path / "rtl"
    render_to_directory(graph, _config_fp16(), out_dir)

    spec = importlib.util.spec_from_file_location(
        "asicify_test_ref_fp16", out_dir / "reference.py"
    )
    assert spec is not None and spec.loader is not None
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)

    rng = torch.Generator().manual_seed(99)
    quant = graph.metadata["_quantized"]["fc"]

    for trial in range(8):
        x = torch.randint(-50, 50, (8,), generator=rng, dtype=torch.int8)
        expected = linear_fp16_forward(x, quant).numpy()
        actual = np.asarray(ref.reference_forward(x.tolist()), dtype=np.int32)
        assert np.array_equal(actual, expected), (
            f"trial {trial}: actual {actual.tolist()} != expected {expected.tolist()}"
        )
