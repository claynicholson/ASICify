"""Tests for low-rank SVD decomposition."""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn

from worker.kernels.decompose import (
    LowRankFactors,
    low_rank_decompose,
    parameter_savings,
)
from worker.pipeline.decompose import apply_decomposition
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory
from worker.types import (
    CompressionConfig,
    DecompositionConfig,
    SparsityConfig,
)


def _config(rank: int) -> CompressionConfig:
    return CompressionConfig(
        quantization="int8",
        sparsity=SparsityConfig(type="none", ratio=0.0),
        decomposition=DecompositionConfig(type="low_rank", rank=rank),
    )


def test_low_rank_decompose_shapes():
    torch.manual_seed(0)
    w = torch.randn(64, 128)
    f = low_rank_decompose(w, None, rank=8)
    assert isinstance(f, LowRankFactors)
    assert f.a.shape == (64, 8)
    assert f.b.shape == (8, 128)
    assert f.rank == 8


def test_low_rank_reconstruction_decreases_with_rank():
    torch.manual_seed(0)
    w = torch.randn(64, 128)
    err_low = low_rank_decompose(w, None, rank=4).reconstruction_error(w)
    err_mid = low_rank_decompose(w, None, rank=16).reconstruction_error(w)
    err_high = low_rank_decompose(w, None, rank=48).reconstruction_error(w)
    assert err_high < err_mid < err_low


def test_low_rank_recovers_low_rank_matrix_exactly():
    """A rank-8 input matrix decomposed to rank 8 should reconstruct nearly perfectly."""
    torch.manual_seed(0)
    a = torch.randn(64, 8)
    b = torch.randn(8, 128)
    w = a @ b
    f = low_rank_decompose(w, None, rank=8)
    err = f.reconstruction_error(w)
    assert err < 1e-5


def test_parameter_savings():
    assert parameter_savings(4096, 4096, 128) > 0.9
    assert parameter_savings(64, 128, 32) > 0.0
    # Equal-size rank gives no savings (in fact a small loss).
    assert parameter_savings(64, 128, 64) <= 0.0


def test_pipeline_replaces_linear_with_two_factors():
    """After apply_decomposition, the original Linear should be replaced by
    layer.b (rank x in) followed by layer.a (out x rank).
    """
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(64, 32)

        def forward(self, x):
            return self.fc(x)

    graph = parse_module(M(), name="m", task="classification")
    graph = apply_decomposition(graph, _config(rank=8))

    layer_names = [layer.name for layer in graph.layers]
    assert "fc" not in layer_names  # original removed
    assert "fc.b" in layer_names    # B factor first
    assert "fc.a" in layer_names    # A factor second

    info = graph.metadata.get("_decomp_info", {})
    assert "fc" in info
    assert info["fc"]["rank"] == 8
    assert info["fc"]["savings"] > 0


def test_pipeline_skips_decomp_when_rank_too_high():
    """If the decomposed parameter count would not be smaller, skip the layer."""
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(8, 4)  # Small layer; rank=64 would cost more.

        def forward(self, x):
            return self.fc(x)

    graph = parse_module(M(), name="m", task="classification")
    graph = apply_decomposition(graph, _config(rank=64))
    layer_names = [layer.name for layer in graph.layers]
    # Original should remain because decomp wouldn't save anything.
    assert "fc" in layer_names
    assert "fc.a" not in layer_names


def test_decomposed_layers_quantize_and_render(tmp_path: Path):
    """End-to-end: decompose → quantize → render. Both factor layers should
    appear as separate Verilog modules.
    """
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(64, 32)

        def forward(self, x):
            return self.fc(x)

    cfg = _config(rank=8)
    graph = parse_module(M(), name="m", task="classification")
    graph = apply_decomposition(graph, cfg)
    graph = quantize_graph(graph, cfg)

    out_dir = tmp_path / "rtl"
    render_to_directory(graph, cfg, out_dir)

    assert (out_dir / "modules/layer_fc_b.v").is_file()
    assert (out_dir / "modules/layer_fc_a.v").is_file()
    weights = (out_dir / "weights.vh").read_text()
    assert "W_fc_b" in weights
    assert "W_fc_a" in weights


def test_monarch_records_intent_without_modifying_weights():
    """Monarch is not yet implemented; pipeline should record intent but not change weights."""
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(64, 32)

        def forward(self, x):
            return self.fc(x)

    cfg = CompressionConfig(
        quantization="int8",
        sparsity=SparsityConfig(type="none", ratio=0.0),
        decomposition=DecompositionConfig(type="monarch", rank=None),
    )
    graph = parse_module(M(), name="m", task="classification")
    original_w = graph.metadata["_weights"]["fc"].clone()
    graph = apply_decomposition(graph, cfg)
    assert torch.equal(graph.metadata["_weights"]["fc"], original_w)
    assert "_decomp_pending" in graph.metadata
