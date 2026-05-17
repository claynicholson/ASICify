"""Throughput model.

  pipeline_depth = number of pipeline stages
  cycles_per_token = max over layers (since pipelined)
  throughput = clock_freq / cycles_per_token
  latency = depth x cycle_time (single-token first-fill)
"""

from __future__ import annotations

from worker.estimator.targets import ASIC_NODES, FPGAS
from worker.types import ModelGraph


def estimate_throughput(graph: ModelGraph, target: str) -> dict[str, float]:
    if target in ASIC_NODES:
        fmax_mhz = ASIC_NODES[target].fmax_mhz
    elif target in FPGAS:
        fmax_mhz = FPGAS[target].fmax_mhz
    else:
        # Shuttles use sky130 timing
        fmax_mhz = ASIC_NODES["sky130"].fmax_mhz

    fmax_hz = fmax_mhz * 1e6

    # Crude: assume largest layer's MACs / available multipliers cycles
    parallel_macs = 4096
    relevant_kinds = ("linear", "ffn", "attention")
    largest_layer_params = max(
        (layer.param_count for layer in graph.layers if layer.kind in relevant_kinds),
        default=1,
    )
    cycles_per_token = max(1, largest_layer_params // parallel_macs)

    throughput = fmax_hz / cycles_per_token
    return {
        "max_clock_mhz": fmax_mhz,
        "cycles_per_token": float(cycles_per_token),
        "throughput_per_sec": throughput,
        "latency_ms": (cycles_per_token * len(graph.layers)) / fmax_hz * 1000,
    }
