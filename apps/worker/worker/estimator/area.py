"""Area model. Sums:
  - multiplier area (precision x multiplier count)
  - storage area (mask ROM x bits)
  - SRAM area (KV cache, activation buffers)
  - routing overhead (~1.5x)
  - I/O ring (fixed for given pad count)
"""

from __future__ import annotations

from worker.estimator.targets import ASIC_NODES, NodeParams
from worker.types import CompressionConfig, ModelGraph

# Multiplier area scaling vs INT8 reference
MUL_SCALE: dict[str, float] = {
    "fp16": 4.0,
    "int8": 1.0,
    "int4": 0.18,    # CSD shift-add
    "ternary": 0.04, # sign-flip mux
    "binary": 0.015, # XNOR + popcount
}

BITS_PER_WEIGHT: dict[str, float] = {
    "fp16": 16,
    "int8": 8,
    "int4": 4,
    "ternary": 1.6,
    "binary": 1,
}


def estimate_area(
    graph: ModelGraph, config: CompressionConfig, target: str
) -> dict[str, float]:
    """Returns area_breakdown in mm². Caller sums for total."""
    if target not in ASIC_NODES:
        return {}
    params: NodeParams = ASIC_NODES[target]
    bpw = BITS_PER_WEIGHT[config.quantization]

    effective_params = _effective_param_count(graph, config)

    storage_um2 = effective_params * bpw * params.rom_bit_um2

    mul_count = min(effective_params, 4096)
    compute_um2 = (
        mul_count * params.mul_int8_um2 * MUL_SCALE[config.quantization]
    )

    # SRAM for KV cache + activation buffers — assume ~4MB ceiling, 5% utilization
    sram_um2 = 4 * 1024 * 1024 * 8 * params.sram_bit_um2 * 0.05

    io_um2 = 0.5 * 1_000_000  # ~80 pads at typical pitch

    subtotal = storage_um2 + compute_um2 + sram_um2
    routing_um2 = subtotal * 0.5

    return {
        "storage_mm2": storage_um2 / 1e6,
        "compute_mm2": compute_um2 / 1e6,
        "sram_mm2": sram_um2 / 1e6,
        "io_mm2": io_um2 / 1e6,
        "routing_overhead_mm2": routing_um2 / 1e6,
    }


def _effective_param_count(graph: ModelGraph, config: CompressionConfig) -> int:
    # If the decomposition stage already ran, layer param_counts are exact
    # (nonzero counts for the synthetic factor layers) — sum those instead
    # of applying a heuristic multiplier on the stale total.
    if config.decomposition.type != "none" and "_decomp_info" in graph.metadata:
        p = float(sum(layer.param_count for layer in graph.layers))
        if config.sparsity.type != "none":
            p *= 1 - config.sparsity.ratio
        return int(p)

    p = float(graph.total_params)
    if config.sparsity.type != "none":
        p *= 1 - config.sparsity.ratio
    if config.decomposition.type in ("monarch", "butterfly"):
        # Nonzero params are k*(in+out) vs in*out dense; with the mean-dim-512
        # convention used by the low_rank branch this is 2k/512.
        k = config.decomposition.num_blocks or 23  # ~sqrt(512)
        p *= min(1.0, (k * 2) / 512)
    elif config.decomposition.type == "low_rank":
        rank = config.decomposition.rank or 64
        p *= min(1.0, (rank * 2) / 512)
    return int(p)
