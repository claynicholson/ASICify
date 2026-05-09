"""Pipeline orchestrator. Runs stages in order, emits progress events,
caches intermediates by hash(input_graph, config).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from worker.pipeline.decompose import apply_decomposition
from worker.pipeline.parse import parse_model
from worker.pipeline.quantize import quantize_graph
from worker.pipeline.sparsity import apply_sparsity
from worker.pipeline.validate import validate_quality
from worker.types import (
    CompressionConfig,
    DecompositionConfig,
    SparsityConfig,
)

EmitFn = Callable[[dict[str, Any]], Awaitable[None]]


def _cfg_from_dict(d: dict[str, Any]) -> CompressionConfig:
    return CompressionConfig(
        quantization=d.get("quantization", "int8"),
        sparsity=SparsityConfig(
            type=d.get("sparsity", {}).get("type", "none"),
            ratio=d.get("sparsity", {}).get("ratio", 0.0),
        ),
        decomposition=DecompositionConfig(
            type=d.get("decomposition", {}).get("type", "none"),
            rank=d.get("decomposition", {}).get("rank"),
        ),
        fine_tune=d.get("fine_tune", False),
        fine_tune_steps=d.get("fine_tune_steps", 1000),
    )


async def run_compression_job(job: dict[str, Any], emit: EmitFn) -> None:
    config = _cfg_from_dict(job["compression_config"])

    # Stage 1: parse
    await _stage(emit, "parse", _do_parse, job["model_source"])

    graph = parse_model(job["model_source"])

    # Stage 2: quantize
    graph = await _stage(emit, "quantization", quantize_graph, graph, config)

    # Stage 3: sparsity
    graph = await _stage(emit, "sparsity", apply_sparsity, graph, config)

    # Stage 4: decomposition
    graph = await _stage(emit, "decomposition", apply_decomposition, graph, config)

    # Stage 5: quality validation
    baseline = 9.2 if graph.task == "language_modeling" else 1.0
    quality = await _stage(
        emit, "validation", validate_quality, graph, config, baseline
    )

    await emit(
        {
            "event": "stage_complete",
            "stage": "summary",
            "duration_ms": 0,
            "metrics": {
                "total_params": float(graph.total_params),
                **quality,
            },
        }
    )


def _do_parse(model_source: dict[str, Any]):
    return parse_model(model_source)


async def _stage(emit: EmitFn, name: str, fn, *args, **kwargs):
    await emit({"event": "stage_start", "stage": name})
    started = time.monotonic()
    result = fn(*args, **kwargs)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    payload: dict[str, Any] = {
        "event": "stage_complete",
        "stage": name,
        "duration_ms": elapsed_ms,
    }
    if isinstance(result, dict):
        payload["metrics"] = result
    await emit(payload)
    return result
