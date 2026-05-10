"""Tests for the attention kernel: softmax LUT correctness and end-to-end attention."""

from __future__ import annotations

import math
from pathlib import Path

import torch
from torch import nn

from worker.cli import _default_config
from worker.kernels.attention import (
    attention_int_forward,
    build_softmax_lut,
    softmax_int,
)
from worker.pipeline.parse import parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory


def test_softmax_lut_shape_and_dtype():
    lut = build_softmax_lut(input_bits=8)
    assert lut.shape == (256,)
    assert lut.dtype == torch.int32
    # exp(0) = 1, mapped to Q15 = 32768.
    assert lut[-1].item() == 32768
    # exp(-255) is essentially zero in Q15.
    assert lut[0].item() < 100


def test_softmax_int_uniform_logits_yields_uniform_weights():
    # All logits equal -> all weights equal.
    logits = torch.zeros(8, dtype=torch.int32)
    w = softmax_int(logits)
    expected_w = (1 << 15) // 8  # uniform Q15
    # All weights should be near uniform (small int division remainders ok).
    assert (w - expected_w).abs().max().item() <= 1


def test_softmax_int_normalization_sums_to_q15():
    """Normalized weights should sum to ~2^15 (Q15 representation of 1.0)."""
    torch.manual_seed(0)
    logits = torch.randint(-50, 50, (16,), dtype=torch.int32)
    w = softmax_int(logits)
    total = w.sum().item()
    # Truncating int divide can leave us a few off; allow 16 slack for 16 entries.
    assert abs(total - (1 << 15)) <= 16


def test_softmax_int_concentrates_on_max():
    """If one logit is much larger, weights concentrate on it."""
    logits = torch.tensor([0, 0, 100, 0, 0], dtype=torch.int32)
    w = softmax_int(logits)
    # The third entry should hold almost all the mass.
    assert w[2].item() > 30000  # close to 32768


def test_attention_int_forward_shape_and_finite():
    torch.manual_seed(0)
    head_dim = 8
    seq = 6
    q = torch.randint(-30, 30, (head_dim,), dtype=torch.int32)
    k = torch.randint(-30, 30, (seq, head_dim), dtype=torch.int32)
    v = torch.randint(-50, 50, (seq, head_dim), dtype=torch.int32)
    ctx = attention_int_forward(q, k, v)
    assert ctx.shape == (head_dim,)
    assert ctx.dtype == torch.int32


def test_attention_int_forward_attends_to_matching_key():
    """When one key matches the query well, that value should dominate the output."""
    head_dim = 4
    q = torch.tensor([100, 0, 0, 0], dtype=torch.int32)
    # Three keys; only key 1 matches query direction.
    k = torch.tensor(
        [
            [0, 0, 100, 0],     # mismatch
            [100, 0, 0, 0],     # match
            [0, 0, 0, 100],     # mismatch
        ],
        dtype=torch.int32,
    )
    v = torch.tensor(
        [
            [0, 0, 0, 0],
            [50, 50, 50, 50],   # what we should attend to
            [-100, -100, -100, -100],
        ],
        dtype=torch.int32,
    )
    ctx = attention_int_forward(q, k, v)
    # Output should be dominated by row 1.
    assert (ctx > 30).all(), f"expected ctx near v[1]={v[1].tolist()} but got {ctx.tolist()}"


class _AttnLikeModel(nn.Module):
    """A model with separate Q/K/V/O projections, as transformers usually have."""

    def __init__(self, embed_dim: int = 16):
        super().__init__()
        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.o_proj = nn.Linear(embed_dim, embed_dim)

    def forward(self, x):
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)
        attn = torch.softmax(q @ k.t(), dim=-1)
        return self.o_proj(attn @ v)


def test_attention_projections_render_as_linear_layers(tmp_path: Path):
    """The Q/K/V/O projections each become layer_*.v files in the package."""
    torch.manual_seed(0)
    model = _AttnLikeModel(embed_dim=16)
    graph = parse_module(model, name="attn", task="language_modeling")
    config = _default_config()
    graph = quantize_graph(graph, config)

    out_dir = tmp_path / "rtl"
    render_to_directory(graph, config, out_dir)

    for sym in ("q_proj", "k_proj", "v_proj", "o_proj"):
        assert (out_dir / f"modules/layer_{sym}.v").is_file()
    # The shared softmax + KV cache modules should also be present.
    assert (out_dir / "softmax.v").is_file()
    assert (out_dir / "kv_cache.v").is_file()
    # The softmax LUT should be in weights.vh.
    assert "SOFTMAX_LUT" in (out_dir / "weights.vh").read_text()
