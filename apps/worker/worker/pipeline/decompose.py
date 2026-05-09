"""Stage 4: Structured decomposition.

  Monarch matrices — W ≈ P₁ B P₂ A P₃, A,B block-diagonal
                     parameters drop from m·n to O((m+n)·sqrt(mn))
  Butterfly        — log(n) factors with sparse structure
  Low-rank         — W ≈ AB, SVD-initialized then fine-tuned
  Tensor-train     — for very high-dim tensors (stretch)
"""

from __future__ import annotations

from dataclasses import replace

from worker.types import CompressionConfig, ModelGraph


def apply_decomposition(graph: ModelGraph, config: CompressionConfig) -> ModelGraph:
    if config.decomposition.type == "none":
        return graph

    decomp: dict[str, dict] = {}
    for layer in graph.layers:
        if layer.kind not in ("linear", "ffn", "attention"):
            continue
        if config.decomposition.type in ("monarch", "butterfly"):
            decomp[layer.name] = {
                "type": config.decomposition.type,
                "n_blocks": _blocks_for(layer.in_features, layer.out_features),
            }
        elif config.decomposition.type == "low_rank":
            decomp[layer.name] = {
                "type": "low_rank",
                "rank": config.decomposition.rank or 64,
            }
    return replace(graph, decompositions=decomp)


def _blocks_for(m: int, n: int) -> int:
    # Heuristic: cube root of dimensions for Monarch block count.
    return max(2, int(round((m * n) ** (1 / 3))))
