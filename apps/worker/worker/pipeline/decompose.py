"""Stage 4: Structural decomposition.

Today: low-rank SVD truncation is real. The decomposed Linear gets split
into two synthetic Linear layers (B then A) that the rest of the pipeline
treats as ordinary Linear modules — quantize, pack, render all work
unchanged.

Monarch and butterfly factorizations are tracked but not yet implemented.
The dispatcher records the requested type so the metric report carries it,
and falls through to no-op for those.
"""

from __future__ import annotations

from dataclasses import replace

from worker.kernels.decompose import low_rank_decompose
from worker.types import CompressionConfig, LayerInfo, ModelGraph


def apply_decomposition(graph: ModelGraph, config: CompressionConfig) -> ModelGraph:
    if config.decomposition.type == "none":
        return graph

    decomp_kind = config.decomposition.type
    rank = config.decomposition.rank or 64

    if decomp_kind == "low_rank":
        return _apply_low_rank(graph, rank)

    if decomp_kind in ("monarch", "butterfly"):
        # Not yet implemented at the kernel level; record intent in metadata
        # so the validator can report it but don't modify weights.
        decomp_meta: dict[str, dict] = {
            layer.name: {
                "type": decomp_kind,
                "n_blocks": _blocks_for(layer.in_features, layer.out_features),
            }
            for layer in graph.layers
            if layer.kind == "linear"
        }
        new_graph = replace(graph)
        new_graph.metadata = dict(graph.metadata)
        new_graph.metadata["_decomp_pending"] = decomp_meta
        return new_graph

    return graph


def _apply_low_rank(graph: ModelGraph, rank: int) -> ModelGraph:
    """Replace each Linear `W (out, in)` with B (rank, in) then A (out, rank).

    The original layer in `graph.layers` is replaced by two new entries with
    suffixes `.b` and `.a`. The metadata maps `_weights` and `_biases` to
    match. Bias goes on the second factor (A) so a single bias add still
    happens once per output.
    """
    weights = dict(graph.metadata.get("_weights", {}))
    biases = dict(graph.metadata.get("_biases", {}))
    decomp_info: dict[str, dict] = {}

    new_layers: list[LayerInfo] = []
    for layer in graph.layers:
        if layer.kind != "linear" or layer.name not in weights:
            new_layers.append(layer)
            continue

        original_w = weights[layer.name]
        original_b = biases.get(layer.name)
        factors = low_rank_decompose(original_w, original_b, rank)

        # Don't decompose if rank wouldn't actually save parameters.
        original_params = layer.in_features * layer.out_features
        decomp_params = factors.rank * (layer.in_features + layer.out_features)
        if decomp_params >= original_params:
            new_layers.append(layer)
            continue

        b_name = f"{layer.name}.b"
        a_name = f"{layer.name}.a"

        # Replace the original tensors with the two factors.
        weights.pop(layer.name)
        biases.pop(layer.name, None)
        weights[b_name] = factors.b
        biases[b_name] = None
        weights[a_name] = factors.a
        biases[a_name] = factors.bias

        new_layers.append(
            LayerInfo(
                name=b_name,
                kind="linear",
                in_features=layer.in_features,
                out_features=factors.rank,
                param_count=factors.rank * layer.in_features,
                metadata={"has_bias": False, "decomposed_from": layer.name, "factor": "b"},
            )
        )
        new_layers.append(
            LayerInfo(
                name=a_name,
                kind="linear",
                in_features=factors.rank,
                out_features=layer.out_features,
                param_count=factors.rank * layer.out_features
                + (layer.out_features if original_b is not None else 0),
                metadata={
                    "has_bias": original_b is not None,
                    "decomposed_from": layer.name,
                    "factor": "a",
                },
            )
        )

        decomp_info[layer.name] = {
            "type": "low_rank",
            "rank": factors.rank,
            "savings": 1.0 - decomp_params / original_params,
            "reconstruction_error": factors.reconstruction_error(original_w),
        }

    new_graph = replace(graph, layers=new_layers)
    new_graph.metadata = dict(graph.metadata)
    new_graph.metadata["_weights"] = weights
    new_graph.metadata["_biases"] = biases
    new_graph.metadata["_decomp_info"] = decomp_info
    return new_graph


def _blocks_for(m: int, n: int) -> int:
    """Heuristic Monarch block count: cube root of dim product."""
    return max(2, round((m * n) ** (1 / 3)))
