"""Stage 2: Quantization.

Calls into worker.kernels.quantize for the actual tensor work. Real
QuantizedLinear records are stashed in graph.metadata["_quantized"] for the
generator and the validator to read.

Sensitivity rule: LayerNorm and Embedding are pinned to INT8 even when the
user requests an extreme low precision. These layers collapse otherwise.
"""

from __future__ import annotations

from dataclasses import replace

from worker.kernels.layers import quantize_embedding, quantize_layernorm
from worker.kernels.quantize import quantize_linear
from worker.types import CompressionConfig, ModelGraph, Quantization


def quantize_graph(graph: ModelGraph, config: CompressionConfig) -> ModelGraph:
    target: Quantization = config.quantization
    new_quant: dict[str, Quantization] = {}
    quantized: dict[str, object] = {}

    weights = graph.metadata.get("_weights", {})
    biases = graph.metadata.get("_biases", {})
    modules = graph.metadata.get("_modules", {})  # filled by parser for layernorm/embedding

    for layer in graph.layers:
        # Sensitivity: LayerNorm and Embedding stay at int8 even at lower precisions.
        if layer.kind in ("layernorm", "embedding") and target in ("binary", "ternary"):
            chosen: Quantization = "int8"
        else:
            chosen = target
        new_quant[layer.name] = chosen

        if layer.kind == "linear" and layer.name in weights:
            quantized[layer.name] = quantize_linear(
                weights[layer.name], biases.get(layer.name), chosen
            )
        elif layer.kind == "layernorm" and layer.name in modules:
            quantized[layer.name] = quantize_layernorm(modules[layer.name])
        elif layer.kind == "embedding" and layer.name in modules:
            quantized[layer.name] = quantize_embedding(modules[layer.name])

    new_graph = replace(graph, quantization=new_quant)
    new_graph.metadata = dict(graph.metadata)
    new_graph.metadata["_quantized"] = quantized
    return new_graph


def estimate_quality_delta(
    graph: ModelGraph, baseline_metric: float, config: CompressionConfig
) -> float:
    """Coarse first-order metric. The validator now uses real activation MSE."""
    PENALTY: dict[Quantization, float] = {
        "fp16": 1.0,
        "int8": 1.005,
        "int4": 1.04,
        "ternary": 1.18,
        "binary": 1.45,
    }
    return baseline_metric * PENALTY[config.quantization]
