"""Stage 5: Quality validation.

Run inference on benchmark suite (per task type):
  LMs:         WikiText perplexity, optionally HellaSwag / ARC-Easy
  Classifiers: ImageNet top-1 (or relevant dataset)
"""

from __future__ import annotations

from worker.pipeline.quantize import estimate_quality_delta
from worker.types import CompressionConfig, ModelGraph


def validate_quality(
    graph: ModelGraph, config: CompressionConfig, baseline: float
) -> dict[str, float]:
    """Returns the per-stage quality breakdown.

    For the MVP this calls estimate_quality_delta. The full implementation
    runs real inference on a held-out set with the compressed model.
    """
    compressed = estimate_quality_delta(graph, baseline, config)
    return {
        "baseline": baseline,
        "compressed": compressed,
        "delta_pct": ((compressed / baseline) - 1) * 100,
    }
