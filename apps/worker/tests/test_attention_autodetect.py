"""Tests for the HF-style attention block auto-detection in the parser."""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn

from worker.cli import _default_config
from worker.kernels.layers import QuantizedAttention
from worker.pipeline.parse import _detect_attention_parents, parse_module
from worker.pipeline.quantize import quantize_graph
from worker.rtl.generator import render_to_directory


class _LlamaStyleAttention(nn.Module):
    """Mimics llama/mistral naming: q_proj, k_proj, v_proj, o_proj."""

    def __init__(self, embed_dim: int = 16, num_heads: int = 4):
        super().__init__()
        self.num_heads = num_heads
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


class _BertStyleAttention(nn.Module):
    """Mimics BERT-ish naming: query, key, value, output.dense."""

    def __init__(self, embed_dim: int = 16):
        super().__init__()

        class Output(nn.Module):
            def __init__(self):
                super().__init__()
                self.dense = nn.Linear(embed_dim, embed_dim)

        self.query = nn.Linear(embed_dim, embed_dim)
        self.key = nn.Linear(embed_dim, embed_dim)
        self.value = nn.Linear(embed_dim, embed_dim)
        self.output = Output()

    def forward(self, x):
        q, k, v = self.query(x), self.key(x), self.value(x)
        return self.output.dense(torch.softmax(q @ k.t(), dim=-1) @ v)


class _Transformer(nn.Module):
    """A model with a self-attention sandwiched between two normal Linears."""

    def __init__(self):
        super().__init__()
        self.in_proj = nn.Linear(16, 16)
        self.attn = _LlamaStyleAttention(embed_dim=16, num_heads=4)
        self.out_proj = nn.Linear(16, 8)

    def forward(self, x):
        return self.out_proj(self.attn(self.in_proj(x)))


def test_detect_llama_style_naming():
    model = _Transformer()
    parents = _detect_attention_parents(model)
    assert "attn" in parents
    assert parents["attn"]["embed_dim"] == 16
    assert parents["attn"]["naming"] == ("q_proj", "k_proj", "v_proj", "o_proj")


def test_detect_bert_style_naming():
    model = _BertStyleAttention(embed_dim=16)
    parents = _detect_attention_parents(model)
    # The root itself looks like an attention block under bert naming.
    assert "" not in parents  # we skip the root
    # No attention parent should fire because the root is the parent of
    # query/key/value/output and we don't classify the root.
    # If any sub-parent matched, that'd be a bug.
    # The detector finds the *parent* containing all 4 children.
    # In this fixture, that parent IS the root, which we skip.
    # To exercise BERT naming, wrap one level deeper:
    class Wrapper(nn.Module):
        def __init__(self):
            super().__init__()
            self.attention = _BertStyleAttention(embed_dim=16)
        def forward(self, x):
            return self.attention(x)
    wrapped = Wrapper()
    parents = _detect_attention_parents(wrapped)
    assert "attention" in parents
    assert parents["attention"]["embed_dim"] == 16


def test_parse_module_collapses_attention_into_one_layer():
    """The parser should report ONE attention layer plus the surrounding Linears,
    not the four Q/K/V/O projections individually.
    """
    torch.manual_seed(0)
    model = _Transformer()
    graph = parse_module(model, name="t", task="language_modeling")

    layer_kinds = [layer.kind for layer in graph.layers]
    layer_names = [layer.name for layer in graph.layers]

    assert "attention" in layer_kinds
    # Q/K/V/O should NOT appear as separate Linear layers.
    for inner in ("attn.q_proj", "attn.k_proj", "attn.v_proj", "attn.o_proj"):
        assert inner not in layer_names, (
            f"{inner} should be hidden inside the attention block, "
            f"not appear as its own Linear"
        )
    # The surrounding Linears should still be visible.
    assert "in_proj" in layer_names
    assert "out_proj" in layer_names


def test_quantize_creates_quantized_attention():
    torch.manual_seed(0)
    model = _Transformer()
    graph = parse_module(model, name="t", task="language_modeling")
    graph = quantize_graph(graph, _default_config())

    quant = graph.metadata["_quantized"]
    assert "attn" in quant
    assert isinstance(quant["attn"], QuantizedAttention)
    assert quant["attn"].embed_dim == 16
    assert quant["attn"].num_heads == 4


def test_renders_attention_block_module(tmp_path: Path):
    """The generator should emit one attention_<sym>.v plus four projection
    layer_<sym>_{q,k,v,o}.v files, instead of four flat layer_*.v.
    """
    torch.manual_seed(0)
    model = _Transformer()
    graph = parse_module(model, name="t", task="language_modeling")
    graph = quantize_graph(graph, _default_config())

    out_dir = tmp_path / "rtl"
    render_to_directory(graph, _default_config(), out_dir)

    assert (out_dir / "modules/attention_attn.v").is_file()
    for proj in ("q", "k", "v", "o"):
        assert (out_dir / f"modules/layer_attn_{proj}.v").is_file()
    # In/out should be normal Linears.
    assert (out_dir / "modules/layer_in_proj.v").is_file()
    assert (out_dir / "modules/layer_out_proj.v").is_file()
