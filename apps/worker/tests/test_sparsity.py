"""Tests for the sparsity kernel and pipeline integration."""

from __future__ import annotations

import torch
from torch import nn

from worker.kernels.sparsity import (
    apply_2_to_4,
    apply_4_to_8,
    apply_block_sparse,
    apply_sparsity,
    apply_unstructured,
    sparsity_ratio,
)
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.pipeline.sparsity import apply_sparsity as pipeline_apply_sparsity
from worker.types import CompressionConfig, DecompositionConfig, SparsityConfig


def test_2_to_4_keeps_exactly_half():
    torch.manual_seed(0)
    w = torch.randn(8, 16)
    out = apply_2_to_4(w)
    assert out.shape == w.shape
    # Every group of 4 must contain exactly 2 zeros.
    g = out.reshape(8, -1, 4)
    nonzero_per_group = (g != 0).sum(dim=-1)
    assert (nonzero_per_group == 2).all()


def test_2_to_4_keeps_largest_magnitudes():
    """Within each group of 4, the kept weights should be the two with largest |w|."""
    w = torch.tensor([[0.1, 0.5, -2.0, 1.5]])
    out = apply_2_to_4(w)
    # Largest by |w|: -2.0 and 1.5; the others should be zeroed.
    assert out[0, 0].item() == 0.0
    assert out[0, 1].item() == 0.0
    assert out[0, 2].item() == -2.0
    assert out[0, 3].item() == 1.5


def test_4_to_8_keeps_half():
    torch.manual_seed(0)
    w = torch.randn(8, 24)
    out = apply_4_to_8(w)
    assert out.shape == w.shape
    g = out.reshape(8, -1, 8)
    assert ((g != 0).sum(dim=-1) == 4).all()


def test_unstructured_drops_correct_fraction():
    torch.manual_seed(0)
    w = torch.randn(4, 100)
    out = apply_unstructured(w, ratio=0.5)
    # Should keep 50% per row.
    nonzero_per_row = (out != 0).sum(dim=-1)
    assert (nonzero_per_row == 50).all()


def test_unstructured_zero_ratio_is_identity():
    w = torch.randn(4, 8)
    out = apply_unstructured(w, ratio=0.0)
    assert torch.equal(out, w)


def test_block_sparse_drops_lowest_tiles():
    torch.manual_seed(0)
    w = torch.randn(32, 32)
    out = apply_block_sparse(w, ratio=0.5, block=16)
    # Output should have approximately half the tiles fully zeroed.
    tiled = out.reshape(2, 16, 2, 16)
    # Reduce: a tile is "kept" if any element is nonzero.
    tile_kept = (tiled != 0).any(dim=(1, 3))
    n_kept = int(tile_kept.sum())
    n_total = tile_kept.numel()
    # At least half dropped, allowing for ties.
    assert n_kept <= n_total * 0.5 + 1


def test_dispatcher_handles_none():
    w = torch.randn(4, 8)
    out = apply_sparsity(w, "none", 0.5)
    assert torch.equal(out, w)


def test_pipeline_zeros_propagate_to_quantization():
    """After sparsity + quantization, the int8 weights should have zeros where the float was zero."""
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(16, 8)

        def forward(self, x):
            return self.fc(x)

    graph = parse_module(M(), name="m", task="classification")
    config = CompressionConfig(
        quantization="int8",
        sparsity=SparsityConfig(type="structured_2_4", ratio=0.5),
        decomposition=DecompositionConfig(type="none"),
    )
    graph = pipeline_apply_sparsity(graph, config)
    pruned = graph.metadata["_weights"]["fc"]
    # The pruned float should have 50% zeros from 2:4.
    ratio = sparsity_ratio(pruned)
    assert 0.45 < ratio < 0.55, f"sparsity ratio {ratio} not near 0.5"

    graph = quantize_graph(graph, config)
    quant = graph.metadata["_quantized"]["fc"]
    # The int8 weights should have zeros wherever the float was zero.
    pruned_zero_mask = pruned == 0
    int8_zero_mask = quant.weight_int8 == 0
    # Every pruned position should remain zero after quantization.
    assert (pruned_zero_mask <= int8_zero_mask).all()


def test_binary_skips_sparsity():
    """Binary precision can't represent zero, so sparsity is skipped silently."""
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(16, 8)

        def forward(self, x):
            return self.fc(x)

    graph = parse_module(M(), name="m", task="classification")
    config = CompressionConfig(
        quantization="binary",
        sparsity=SparsityConfig(type="structured_2_4", ratio=0.5),
        decomposition=DecompositionConfig(type="none"),
    )
    original = graph.metadata["_weights"]["fc"].clone()
    graph = pipeline_apply_sparsity(graph, config)
    # Weight should be unchanged since binary rejects sparsity.
    assert torch.equal(graph.metadata["_weights"]["fc"], original)
