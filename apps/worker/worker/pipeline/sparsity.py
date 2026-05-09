"""Stage 3: Sparsity.

  Magnitude pruning  — Wanda or SparseGPT (one-shot, no retrain)
  Structured 2:4/4:8 — keep layout regular for hardware efficiency
  Block-sparse 16×16 — good for hardware tile size
"""

from __future__ import annotations

from dataclasses import replace

from worker.types import CompressionConfig, ModelGraph


def apply_sparsity(graph: ModelGraph, config: CompressionConfig) -> ModelGraph:
    """Generate sparsity masks per layer (R2 keys would be filled by the kernel).

    For 2:4 structured sparsity, every group of 4 contiguous weights keeps the
    2 with highest magnitude. The mask is stored separately; the RTL generator
    uses it to omit zero-multipliers.
    """
    if config.sparsity.type == "none" or config.sparsity.ratio == 0:
        return graph

    masks: dict[str, str] = {}
    for layer in graph.layers:
        if layer.kind not in ("linear", "ffn", "attention"):
            # Don't prune layernorms or embeddings
            continue
        masks[layer.name] = f"sparsity/{graph.name}/{layer.name}.mask"

    return replace(graph, sparsity_masks=masks)
