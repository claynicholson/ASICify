"""Stage 2: Quantization.

Modes:
  INT8 symmetric  — per-channel scale, no zero-point
  INT4 GPTQ-style — block-wise, group size 128, with calibration data
  Ternary         — weights ∈ {-α, 0, +α} per layer
  Binary          — weights ∈ {-α, +α}
  Mixed precision — per-layer precision selection by sensitivity

This module owns the quantization logic; it operates on a ModelGraph and
returns a new graph with `quantization` populated. The actual weight-tensor
work is implemented in worker.kernels.* (not included in this scaffold —
this is the orchestration layer).
"""

from __future__ import annotations

from dataclasses import replace

from worker.types import CompressionConfig, ModelGraph, Quantization

# Sensitivity heuristic: layernorms and embeddings keep higher precision.
# Linear and attention layers take the requested precision.

def quantize_graph(graph: ModelGraph, config: CompressionConfig) -> ModelGraph:
    target: Quantization = config.quantization
    new_quant: dict[str, Quantization] = {}
    for layer in graph.layers:
        if layer.kind in ("layernorm", "embedding"):
            # These are notoriously sensitive — keep at fp16 for binary/ternary
            if target in ("binary", "ternary"):
                new_quant[layer.name] = "int8"
            else:
                new_quant[layer.name] = target
        else:
            new_quant[layer.name] = target
    return replace(graph, quantization=new_quant)


def estimate_quality_delta(
    graph: ModelGraph, baseline_metric: float, config: CompressionConfig
) -> float:
    """Rough projection used for early progress events. Worker validates with real data."""
    PENALTY: dict[Quantization, float] = {
        "fp16": 1.0,
        "int8": 1.005,
        "int4": 1.04,
        "ternary": 1.18,
        "binary": 1.45,
    }
    return baseline_metric * PENALTY[config.quantization]
