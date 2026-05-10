"""Tests for LayerNorm and Embedding kernels and rendering."""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn

from worker.cli import _default_config
from worker.kernels.layers import (
    embedding_int_forward,
    layernorm_int_forward,
    quantize_embedding,
    quantize_layernorm,
)
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory


def test_quantize_layernorm_q15_round_trip():
    ln = nn.LayerNorm(16)
    nn.init.normal_(ln.weight, mean=1.0, std=0.05)
    nn.init.normal_(ln.bias, mean=0.0, std=0.05)
    qln = quantize_layernorm(ln)
    assert qln.dim == 16
    assert qln.gamma_q15.dtype == torch.int32
    assert qln.beta_q15.dtype == torch.int32
    # Recovered gamma should be very close to the original.
    recovered_gamma = qln.gamma_q15.to(torch.float32) / (1 << 15)
    assert torch.allclose(recovered_gamma, ln.weight, atol=2e-4)


def test_layernorm_int_forward_finite_and_int8():
    ln = nn.LayerNorm(32)
    nn.init.normal_(ln.weight, mean=1.0, std=0.05)
    qln = quantize_layernorm(ln)
    x = torch.randint(-50, 50, (32,), dtype=torch.int8)
    y = layernorm_int_forward(x, qln)
    assert y.dtype == torch.int8
    assert y.shape == (32,)
    # The output should be roughly mean-zero unit-variance after normalize.
    # Just sanity check that we don't get all zeros or all-saturated.
    assert (y == 0).sum() < y.numel()


def test_quantize_embedding_per_column_scale():
    emb = nn.Embedding(50, 16)
    qe = quantize_embedding(emb)
    assert qe.vocab_size == 50
    assert qe.embedding_dim == 16
    assert qe.table_int8.shape == (50, 16)
    assert qe.scale.shape == (16,)
    # Recover roughly the original.
    recovered = qe.table_int8.to(torch.float32) * qe.scale.unsqueeze(0)
    err = (recovered - emb.weight).abs().mean() / emb.weight.abs().mean()
    assert err < 0.02


def test_embedding_int_forward_returns_rows():
    emb = nn.Embedding(100, 8)
    qe = quantize_embedding(emb)
    ids = torch.tensor([0, 5, 99])
    out = embedding_int_forward(ids, qe)
    assert out.shape == (3, 8)
    assert out.dtype == torch.int8


class _Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Embedding(64, 16)
        self.ln = nn.LayerNorm(16)
        self.fc = nn.Linear(16, 8)

    def forward(self, ids):
        h = self.embed(ids)
        h = self.ln(h)
        return self.fc(h)


def test_pipeline_renders_embedding_and_layernorm(tmp_path: Path):
    """The generator should emit module files and weights for LN and Embedding."""
    torch.manual_seed(0)
    model = _Model()
    graph = parse_module(model, name="m", task="language_modeling")
    graph = quantize_graph(graph, _default_config())

    out_dir = tmp_path / "rtl"
    render_to_directory(graph, _default_config(), out_dir)

    expected = [
        "modules/layer_embed.v",
        "modules/layer_ln.v",
        "modules/layer_fc.v",
    ]
    for rel in expected:
        assert (out_dir / rel).is_file(), f"missing {rel}"

    weights_vh = (out_dir / "weights.vh").read_text()
    assert "EMBED_embed" in weights_vh
    assert "GAMMA_Q15_ln" in weights_vh
    assert "BETA_Q15_ln" in weights_vh
    assert "EPS_Q15_ln" in weights_vh
    assert "W_fc" in weights_vh
