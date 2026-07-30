"""Shared dataclasses for worker pipeline. Mirrors packages/shared/src/types.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Quantization = Literal["fp16", "int8", "int4", "ternary", "binary"]
SparsityType = Literal[
    "none", "structured_2_4", "structured_4_8", "block_sparse_16", "unstructured"
]
DecompositionType = Literal["none", "monarch", "butterfly", "low_rank"]
LayerKind = Literal[
    "linear", "conv2d", "attention", "ffn", "layernorm", "embedding", "other"
]


@dataclass
class LayerInfo:
    name: str
    kind: LayerKind
    in_features: int
    out_features: int
    param_count: int
    activation_shape: tuple[int, ...] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelGraph:
    """Intermediate representation of a parsed model.

    Used as the value type passed between pipeline stages.
    """

    name: str
    task: Literal["language_modeling", "classification", "speech"]
    layers: list[LayerInfo]
    total_params: int
    metadata: dict[str, Any] = field(default_factory=dict)
    # Per-layer compression state (populated as stages run)
    quantization: dict[str, Quantization] = field(default_factory=dict)
    sparsity_masks: dict[str, str] = field(default_factory=dict)  # layer -> R2 key
    decompositions: dict[str, dict] = field(default_factory=dict)


@dataclass
class SparsityConfig:
    type: SparsityType = "none"
    ratio: float = 0.0


@dataclass
class DecompositionConfig:
    type: DecompositionType = "none"
    rank: int | None = None
    num_blocks: int | None = None  # monarch/butterfly; None = auto (~sqrt of min dim)


@dataclass
class CompressionConfig:
    quantization: Quantization = "int8"
    sparsity: SparsityConfig = field(default_factory=SparsityConfig)
    decomposition: DecompositionConfig = field(default_factory=DecompositionConfig)
    fine_tune: bool = False
    fine_tune_steps: int = 1000


@dataclass
class StageResult:
    stage: str
    duration_ms: int
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)  # R2 keys
