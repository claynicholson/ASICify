"""Stage 4: Structural decomposition.

All three decomposition types are real. The decomposed Linear gets split
into two synthetic Linear layers (B then A) that the rest of the pipeline
treats as ordinary Linear modules — quantize, pack, render all work
unchanged.

    low_rank   - truncated SVD, B (rank, in) then A (out, rank)
    monarch    - blockwise rank-1 SVD projection onto the Monarch class;
                 factors materialized as dense matrices with structured
                 zeros (density 1/k) and the permutation folded into row
                 ordering, so no permutation module is needed in RTL
    butterfly  - the Monarch projection with a power-of-two block count
"""

from __future__ import annotations

from dataclasses import replace

from worker.kernels.decompose import (
    auto_n_blocks,
    low_rank_decompose,
    monarch_decompose,
    monarch_parameter_savings,
)
from worker.types import CompressionConfig, LayerInfo, ModelGraph


def apply_decomposition(graph: ModelGraph, config: CompressionConfig) -> ModelGraph:
    if config.decomposition.type == "none":
        return graph

    decomp_kind = config.decomposition.type
    rank = config.decomposition.rank or 64

    if decomp_kind == "low_rank":
        return _apply_low_rank(graph, rank)

    if decomp_kind in ("monarch", "butterfly"):
        return _apply_block_diagonal(graph, config, decomp_kind)

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


def _apply_block_diagonal(
    graph: ModelGraph, config: CompressionConfig, kind: str
) -> ModelGraph:
    """Replace each Linear with the two materialized Monarch factors.

    Same shape as `_apply_low_rank`: the original layer becomes `{name}.b`
    (in -> k*k, no bias) then `{name}.a` (k*k -> out, bias). `param_count`
    on the new layers counts nonzeros, not the dense materialized size, so
    area estimates stay honest. Layers where no valid block count exists
    (non-divisible dims, too small, or no savings) are kept as-is.
    """
    weights = dict(graph.metadata.get("_weights", {}))
    biases = dict(graph.metadata.get("_biases", {}))
    decomp_info: dict[str, dict] = {}

    new_layers: list[LayerInfo] = []
    for layer in graph.layers:
        if layer.kind != "linear" or layer.name not in weights:
            new_layers.append(layer)
            continue

        k = auto_n_blocks(
            layer.in_features,
            layer.out_features,
            requested=config.decomposition.num_blocks,
            power_of_two=(kind == "butterfly"),
        )
        if k is None:
            new_layers.append(layer)
            continue

        original_w = weights[layer.name]
        original_b = biases.get(layer.name)
        factors = monarch_decompose(original_w, original_b, k)

        b_name = f"{layer.name}.b"
        a_name = f"{layer.name}.a"

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
                out_features=factors.mid_features,
                param_count=factors.nnz_b,
                metadata={
                    "has_bias": False,
                    "decomposed_from": layer.name,
                    "factor": "b",
                    "n_blocks": k,
                    "structure": kind,
                },
            )
        )
        new_layers.append(
            LayerInfo(
                name=a_name,
                kind="linear",
                in_features=factors.mid_features,
                out_features=layer.out_features,
                param_count=factors.nnz_a
                + (layer.out_features if original_b is not None else 0),
                metadata={
                    "has_bias": original_b is not None,
                    "decomposed_from": layer.name,
                    "factor": "a",
                    "n_blocks": k,
                    "structure": kind,
                },
            )
        )

        decomp_info[layer.name] = {
            "type": kind,
            "n_blocks": k,
            "mid_features": factors.mid_features,
            "savings": monarch_parameter_savings(
                layer.in_features, layer.out_features, k
            ),
            "reconstruction_error": factors.reconstruction_error(original_w),
        }

    new_graph = replace(graph, layers=new_layers)
    new_graph.metadata = dict(graph.metadata)
    new_graph.metadata["_weights"] = weights
    new_graph.metadata["_biases"] = biases
    new_graph.metadata["_decomp_info"] = decomp_info
    return new_graph
