"""Tests for low-rank SVD and Monarch/butterfly decomposition."""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn

from worker.kernels.decompose import (
    LowRankFactors,
    MonarchFactors,
    auto_n_blocks,
    low_rank_decompose,
    monarch_decompose,
    monarch_parameter_savings,
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


# ---------------------------------------------------------------------------
# Monarch / butterfly
# ---------------------------------------------------------------------------


def _block_config(
    kind: str = "monarch", num_blocks: int | None = None
) -> CompressionConfig:
    return CompressionConfig(
        quantization="int8",
        sparsity=SparsityConfig(type="none", ratio=0.0),
        decomposition=DecompositionConfig(type=kind, num_blocks=num_blocks),  # type: ignore[arg-type]
    )


def test_monarch_decompose_shapes_and_zero_pattern():
    torch.manual_seed(0)
    w = torch.randn(64, 128)
    k, p, q = 4, 128 // 4, 64 // 4
    f = monarch_decompose(w, None, n_blocks=k)
    assert isinstance(f, MonarchFactors)
    assert f.b.shape == (k * k, 128)
    assert f.a.shape == (64, k * k)
    assert f.mid_features == k * k
    assert f.nnz_b == k * 128
    assert f.nnz_a == k * 64

    # b: row i*k+j is nonzero only inside input-block j's columns.
    for i in range(k):
        for j in range(k):
            row = f.b[i * k + j]
            mask = torch.zeros(128, dtype=torch.bool)
            mask[j * p:(j + 1) * p] = True
            assert torch.all(row[~mask] == 0)
    # a: column i*k+j is nonzero only inside output-block i's rows.
    for i in range(k):
        for j in range(k):
            col = f.a[:, i * k + j]
            mask = torch.zeros(64, dtype=torch.bool)
            mask[i * q:(i + 1) * q] = True
            assert torch.all(col[~mask] == 0)
    # Nonzero counts match the claimed density of 1/k.
    assert int((f.b != 0).sum()) <= f.nnz_b
    assert int((f.a != 0).sum()) <= f.nnz_a


def test_monarch_reconstruction_improves_with_blocks():
    torch.manual_seed(0)
    w = torch.randn(64, 128)
    err_2 = monarch_decompose(w, None, n_blocks=2).reconstruction_error(w)
    err_8 = monarch_decompose(w, None, n_blocks=8).reconstruction_error(w)
    err_32 = monarch_decompose(w, None, n_blocks=32).reconstruction_error(w)
    assert err_32 < err_8 < err_2


def test_monarch_recovers_monarch_matrix_exactly():
    """A matrix whose k x k blocks are all rank-1 lies in the Monarch class;
    projecting it at the same k should reconstruct nearly perfectly."""
    torch.manual_seed(0)
    k, q, p = 4, 8, 16
    blocks = [
        [torch.outer(torch.randn(q), torch.randn(p)) for _ in range(k)]
        for _ in range(k)
    ]
    w = torch.cat([torch.cat(row, dim=1) for row in blocks], dim=0)  # (32, 64)
    f = monarch_decompose(w, None, n_blocks=k)
    assert f.reconstruction_error(w) < 1e-5


def test_monarch_parameter_savings():
    assert monarch_parameter_savings(4096, 4096, 64) > 0.9
    assert monarch_parameter_savings(64, 128, 4) > 0.0
    # Enough blocks always erases the savings: k(in+out) >= in*out.
    assert monarch_parameter_savings(8, 8, 4) <= 0.0


def test_auto_n_blocks():
    # Auto target is ~sqrt(min dim): sqrt(64) = 8, which divides gcd(64, 128).
    assert auto_n_blocks(64, 128) == 8
    # Requested value snaps down to the nearest divisor of the gcd.
    assert auto_n_blocks(64, 128, requested=12) == 8
    # Butterfly flavor restricts to powers of two.
    assert auto_n_blocks(48, 24, requested=6) == 6
    assert auto_n_blocks(48, 24, requested=6, power_of_two=True) == 4
    # Coprime dims have no valid block count.
    assert auto_n_blocks(7, 5) is None
    # Tiny layers where no k saves parameters.
    assert auto_n_blocks(2, 2) is None
    assert auto_n_blocks(1, 64) is None


def test_pipeline_replaces_linear_with_monarch_factors():
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(64, 32)

        def forward(self, x):
            return self.fc(x)

    graph = parse_module(M(), name="m", task="classification")
    graph = apply_decomposition(graph, _block_config("monarch", num_blocks=4))

    layer_names = [layer.name for layer in graph.layers]
    assert "fc" not in layer_names
    assert "fc.b" in layer_names
    assert "fc.a" in layer_names

    by_name = {layer.name: layer for layer in graph.layers}
    assert by_name["fc.b"].out_features == 16  # k*k
    assert by_name["fc.a"].in_features == 16
    # param_count counts nonzeros, not the dense materialized size.
    assert by_name["fc.b"].param_count == 4 * 64
    assert by_name["fc.a"].param_count == 4 * 32 + 32  # + bias

    info = graph.metadata["_decomp_info"]["fc"]
    assert info["type"] == "monarch"
    assert info["n_blocks"] == 4
    assert info["mid_features"] == 16
    assert info["savings"] > 0
    assert info["reconstruction_error"] >= 0
    assert "_decomp_pending" not in graph.metadata


def test_pipeline_skips_monarch_when_not_applicable():
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.odd = nn.Linear(7, 5)   # coprime dims: no valid k
            self.tiny = nn.Linear(4, 4)  # no k saves parameters

        def forward(self, x):
            return self.tiny(nn.functional.pad(self.odd(x), (0, -1)))

    graph = parse_module(M(), name="m", task="classification")
    graph = apply_decomposition(graph, _block_config("monarch"))
    layer_names = [layer.name for layer in graph.layers]
    assert "odd" in layer_names
    assert "tiny" in layer_names
    assert "odd.a" not in layer_names
    assert "tiny.a" not in layer_names


def test_butterfly_uses_power_of_two_blocks():
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(48, 24)

        def forward(self, x):
            return self.fc(x)

    graph = parse_module(M(), name="m", task="classification")
    graph = apply_decomposition(graph, _block_config("butterfly", num_blocks=6))
    info = graph.metadata["_decomp_info"]["fc"]
    assert info["type"] == "butterfly"
    assert info["n_blocks"] == 4  # 6 snapped down to a power of two


def test_monarch_bias_preserved_on_a_factor():
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(64, 32)

        def forward(self, x):
            return self.fc(x)

    m = M()
    original_bias = m.fc.bias.detach().clone()
    graph = parse_module(m, name="m", task="classification")
    graph = apply_decomposition(graph, _block_config("monarch", num_blocks=4))

    assert graph.metadata["_biases"]["fc.b"] is None
    assert torch.allclose(graph.metadata["_biases"]["fc.a"], original_bias)
    by_name = {layer.name: layer for layer in graph.layers}
    assert by_name["fc.b"].metadata["has_bias"] is False
    assert by_name["fc.a"].metadata["has_bias"] is True


def test_monarch_layers_quantize_and_render(tmp_path: Path):
    """End-to-end: monarch decompose -> quantize -> render, like low_rank."""
    torch.manual_seed(0)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(64, 32)

        def forward(self, x):
            return self.fc(x)

    cfg = _block_config("monarch", num_blocks=4)
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
