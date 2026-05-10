"""Stage 3: Sparsity.

Real magnitude pruning that runs before quantization. Pruned weights become
exact zeros in the float tensor, which then quantize to zero and stay zero
in the packed Verilog constants. Synthesis removes the dead multipliers.

Binary precision can't represent zero, so binary skips sparsity.
"""

from __future__ import annotations

from dataclasses import replace

from worker.kernels.sparsity import apply_sparsity as _apply_kernel
from worker.kernels.sparsity import sparsity_ratio
from worker.types import CompressionConfig, ModelGraph


def apply_sparsity(graph: ModelGraph, config: CompressionConfig) -> ModelGraph:
    """Walk linear layers, prune in place on the float tensors, then return a new graph."""
    if config.sparsity.type == "none" or config.sparsity.ratio == 0.0:
        return graph
    if config.quantization == "binary":
        # Binary {-1, +1} has no zero, sparsity is meaningless.
        return graph

    weights = dict(graph.metadata.get("_weights", {}))
    masks_ratios: dict[str, float] = {}

    for layer in graph.layers:
        if layer.kind != "linear":
            continue
        if layer.name not in weights:
            continue
        pruned = _apply_kernel(weights[layer.name], config.sparsity.type, config.sparsity.ratio)
        weights[layer.name] = pruned
        masks_ratios[layer.name] = sparsity_ratio(pruned)

    new_graph = replace(graph)
    new_graph.metadata = dict(graph.metadata)
    new_graph.metadata["_weights"] = weights
    new_graph.metadata["_sparsity_ratios"] = masks_ratios
    return new_graph
