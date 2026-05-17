"""Full hardware estimate runner. Aggregates area + throughput + cost per target."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from worker.estimator.area import estimate_area
from worker.estimator.cost import estimate_cost
from worker.estimator.targets import ASIC_NODES, FPGAS
from worker.estimator.throughput import estimate_throughput
from worker.pipeline.orchestrator import _cfg_from_dict
from worker.pipeline.parse import parse_model
from worker.types import CompressionConfig, ModelGraph

EmitFn = Callable[[dict[str, Any]], Awaitable[None]]


def estimate(graph: ModelGraph, config: CompressionConfig, target: str) -> dict[str, Any]:
    area_breakdown = estimate_area(graph, config, target)
    total_area_mm2 = sum(area_breakdown.values()) if area_breakdown else 0.0
    throughput = estimate_throughput(graph, target)
    cost = estimate_cost(total_area_mm2, target)

    confidence = 0.85 if target in FPGAS else 0.65 if target in ASIC_NODES else 0.55

    return {
        "target": target,
        "area_mm2": total_area_mm2,
        "area_breakdown": area_breakdown,
        "max_clock_mhz": throughput["max_clock_mhz"],
        "throughput_per_sec": throughput["throughput_per_sec"],
        "latency_ms": throughput["latency_ms"],
        "energy_per_op_pj": _energy(target, config),
        "cost_per_chip": {str(k): v for k, v in cost.items()},
        "confidence": confidence,
    }


async def run_estimate_job(job: dict[str, Any], emit: EmitFn) -> None:
    graph = parse_model(job["model_source"])
    config = _cfg_from_dict(job["compression_config"])
    targets: list[str] = job.get("target_hardware") or ["tsmc28"]

    estimates: list[dict[str, Any]] = []
    for t in targets:
        await emit({"event": "stage_start", "stage": f"estimate:{t}"})
        e = estimate(graph, config, t)
        estimates.append(e)
        await emit(
            {
                "event": "stage_complete",
                "stage": f"estimate:{t}",
                "duration_ms": 0,
                "metrics": {
                    "area_mm2": e["area_mm2"],
                    "throughput_per_sec": e["throughput_per_sec"],
                    "cost_at_100k": e["cost_per_chip"]["100000"],
                },
            }
        )

    # Final summary event
    await emit(
        {
            "event": "stage_complete",
            "stage": "summary",
            "duration_ms": 0,
            "metrics": {"n_targets": float(len(estimates))},
        }
    )


def _energy(target: str, config: CompressionConfig) -> float:
    base = ASIC_NODES.get(target)
    if base is None:
        # FPGAs: rough constant
        return 1.5
    scale = {
        "fp16": 4.0,
        "int8": 1.0,
        "int4": 0.18,
        "ternary": 0.04,
        "binary": 0.015,
    }
    return base.energy_int8_pj * scale[config.quantization]
