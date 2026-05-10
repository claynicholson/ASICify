"""Tests for the activation-MSE validator."""

from __future__ import annotations

import torch
from torch import nn

from worker.cli import _default_config
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.pipeline.validate import validate_quality, validate_with_data
from worker.types import CompressionConfig, DecompositionConfig, SparsityConfig


class _MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(8, 16)
        self.fc2 = nn.Linear(16, 4)

    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))


def _config(quantization: str = "int8") -> CompressionConfig:
    return CompressionConfig(
        quantization=quantization,
        sparsity=SparsityConfig(type="none", ratio=0.0),
        decomposition=DecompositionConfig(type="none"),
    )


def test_validation_returns_real_metrics_for_int8():
    torch.manual_seed(0)
    model = _MLP()
    graph = parse_module(model, name="m", task="classification")
    graph = quantize_graph(graph, _config("int8"))
    metrics = validate_quality(graph, _config("int8"), baseline=1.0)
    assert "activation_mse" in metrics
    assert "max_layer_mse" in metrics
    assert "cosine_similarity" in metrics
    # INT8 should be very close to the original.
    assert metrics["activation_mse"] < 0.01
    assert metrics["cosine_similarity"] > 0.99


def test_validation_metrics_degrade_with_lower_precision():
    """INT8 should be tighter than int4 should be tighter than ternary should be tighter than binary."""
    torch.manual_seed(0)
    model = _MLP()
    graph = parse_module(model, name="m", task="classification")

    results: dict[str, float] = {}
    for q in ("int8", "int4", "ternary", "binary"):
        g = quantize_graph(graph, _config(q))
        m = validate_quality(g, _config(q), baseline=1.0)
        results[q] = m["activation_mse"]

    assert results["int8"] < results["int4"]
    assert results["int4"] < results["ternary"]
    assert results["ternary"] < results["binary"]


def test_validate_with_data_top1():
    """Top-1 metric works for a classifier with explicit targets."""
    torch.manual_seed(0)
    model = _MLP()
    graph = parse_module(model, name="m", task="classification")
    graph = quantize_graph(graph, _config("int8"))

    x = torch.randn(64, 8)
    y = model(x).argmax(dim=-1)
    res = validate_with_data(graph, x, y, metric="top1")
    assert "baseline_top1" in res
    assert "compressed_top1" in res
    # INT8 should preserve most of the top-1.
    assert res["compressed_top1"] > 0.9 * res["baseline_top1"]


def test_validate_falls_back_when_no_root_module():
    """If the graph lacks _root_module, fall back to the analytical penalty."""
    torch.manual_seed(0)
    model = _MLP()
    graph = parse_module(model, name="m", task="classification")
    graph = quantize_graph(graph, _config("int8"))
    # Simulate a graph that came from a serialized job (no live module).
    graph.metadata.pop("_root_module", None)
    metrics = validate_quality(graph, _config("int8"), baseline=10.0)
    assert "activation_mse" not in metrics  # fallback path
    assert metrics["baseline"] == 10.0
    # int8 penalty is ~1.005x.
    assert 9.95 < metrics["compressed"] < 10.1
