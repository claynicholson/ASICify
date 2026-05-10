"""Bit-exactness tests across all quantization precisions.

Each precision is checked the same way:
  1. Quantize a random Linear weight.
  2. Run the in-process kernel forward.
  3. Render the layer to RTL + reference.py.
  4. Run reference.py on the same input.
  5. Assert the int32 outputs are identical.

The kernel forward is the source of truth for the integer math; the reference
is generated from the same packed weights. If they disagree, the bug is in
the pack module or the reference template.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from worker.cli import _default_config
from worker.kernels.quantize import (
    linear_int8_forward,
    quantize_linear,
    quantize_linear_binary,
    quantize_linear_int4,
    quantize_linear_int8,
    quantize_linear_ternary,
)
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory
from worker.types import CompressionConfig, DecompositionConfig, SparsityConfig


def _config(quantization: str) -> CompressionConfig:
    return CompressionConfig(
        quantization=quantization,
        sparsity=SparsityConfig(type="none", ratio=0.0),
        decomposition=DecompositionConfig(type="none"),
    )


@pytest.mark.parametrize("quantization", ["int8", "int4", "ternary", "binary"])
def test_kernel_quantize_dispatch(quantization: str):
    torch.manual_seed(7)
    w = torch.randn(6, 8)
    b = torch.randn(6)
    q = quantize_linear(w, b, quantization)
    assert q.quantization == quantization
    assert q.weight_int8.shape == (6, 8)
    assert q.scale.shape == (6,)


def test_int4_weights_in_range():
    torch.manual_seed(0)
    q = quantize_linear_int4(torch.randn(4, 16))
    assert q.weight_int8.max() <= 7
    assert q.weight_int8.min() >= -7


def test_ternary_weights_only_three_values():
    torch.manual_seed(0)
    q = quantize_linear_ternary(torch.randn(4, 32))
    unique = torch.unique(q.weight_int8)
    assert set(unique.tolist()).issubset({-1, 0, 1})


def test_binary_weights_only_two_values():
    torch.manual_seed(0)
    q = quantize_linear_binary(torch.randn(4, 32))
    unique = torch.unique(q.weight_int8)
    assert set(unique.tolist()).issubset({-1, 1})


def _load_reference(out_dir: Path):
    spec = importlib.util.spec_from_file_location(
        "asicify_test_ref_multi", out_dir / "reference.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _OneLayer(nn.Module):
    def __init__(self, in_f: int, out_f: int, bias: bool = True):
        super().__init__()
        self.fc = nn.Linear(in_f, out_f, bias=bias)

    def forward(self, x):
        return self.fc(x)


@pytest.mark.parametrize("quantization", ["int8", "int4", "ternary", "binary"])
def test_reference_matches_kernel_for_each_precision(quantization, tmp_path):
    """For each precision, the generated reference.py must match the in-process kernel."""
    torch.manual_seed(11 + hash(quantization) % 1000)
    in_f, out_f = 16, 8
    model = _OneLayer(in_f, out_f, bias=True)

    graph = parse_module(model, name=f"one_{quantization}", task="classification")
    config = _config(quantization)
    graph = quantize_graph(graph, config)
    out_dir = tmp_path / f"rtl_{quantization}"
    render_to_directory(graph, config, out_dir)

    reference = _load_reference(out_dir)
    quant = graph.metadata["_quantized"]["fc"]

    rng = torch.Generator().manual_seed(42)
    for trial in range(8):
        x = torch.randint(-50, 50, (in_f,), generator=rng, dtype=torch.int8)
        expected = linear_int8_forward(x, quant).numpy()
        actual = np.asarray(reference.reference_forward(x.tolist()), dtype=np.int32)
        assert np.array_equal(actual, expected), (
            f"{quantization} trial {trial}: actual {actual.tolist()} "
            f"!= expected {expected.tolist()}"
        )


@pytest.mark.parametrize(
    "quantization, expected_marker",
    [
        ("int8", "8'sd"),
        ("int4", "8'h"),
        ("ternary", "8'h"),
        ("binary", "8'h"),
    ],
)
def test_weights_vh_format_matches_precision(quantization, expected_marker, tmp_path):
    torch.manual_seed(0)
    model = _OneLayer(16, 8, bias=True)
    graph = parse_module(model, name=f"fmt_{quantization}", task="classification")
    config = _config(quantization)
    graph = quantize_graph(graph, config)
    out_dir = tmp_path / f"rtl_{quantization}"
    render_to_directory(graph, config, out_dir)
    weights_vh = (out_dir / "weights.vh").read_text()
    assert expected_marker in weights_vh, (
        f"{quantization}: expected '{expected_marker}' in weights.vh"
    )
