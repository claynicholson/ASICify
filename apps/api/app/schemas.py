"""Pydantic schemas for API request/response. Aligned with packages/shared/src/types.ts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Quantization = Literal["fp16", "int8", "int4", "ternary", "binary"]
SparsityType = Literal[
    "none", "structured_2_4", "structured_4_8", "block_sparse_16", "unstructured"
]
DecompositionType = Literal["none", "monarch", "butterfly", "low_rank"]
ProjectStatus = Literal["draft", "queued", "running", "complete", "failed"]
TargetId = Literal[
    "sky130",
    "gf22fdx",
    "tsmc28",
    "tsmc16",
    "tsmc7",
    "ecp5",
    "crosslinknx",
    "artix7",
    "kria",
    "tinytapeout",
    "chipignite",
]


class ModelSource(BaseModel):
    type: Literal["huggingface", "upload", "onnx"]
    id: str | None = None
    url: str | None = None


class SparsityConfig(BaseModel):
    type: SparsityType = "none"
    ratio: float = Field(0, ge=0, le=1)


class DecompositionConfig(BaseModel):
    type: DecompositionType = "none"
    rank: int | None = None


class CompressionConfig(BaseModel):
    quantization: Quantization = "int8"
    sparsity: SparsityConfig = SparsityConfig()
    decomposition: DecompositionConfig = DecompositionConfig()
    fine_tune: bool = False
    fine_tune_steps: int = 1000


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    model_source: ModelSource
    compression: CompressionConfig
    targets: list[TargetId]


class ProjectMetrics(BaseModel):
    baseline_perplexity: float | None = None
    compressed_perplexity: float | None = None
    baseline_accuracy: float | None = None
    compressed_accuracy: float | None = None
    baseline_param_count: int = 0
    compressed_param_count: int = 0
    size_reduction: float = 0.0
    effective_bits_per_weight: float = 0.0


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    model_source: dict
    compression_config: dict
    target_hardware: list[str]
    status: ProjectStatus
    metrics: dict | None
    created_at: datetime
    updated_at: datetime


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    type: str
    size_bytes: int
    created_at: datetime
    download_url: str | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    job_type: str
    status: str
    progress: float
    error_message: str | None
    created_at: datetime


class CatalogModel(BaseModel):
    id: str
    hf_id: str
    display_name: str
    family: str
    task: Literal["language_modeling", "classification", "speech"]
    parameters: int
    recommended_compression: CompressionConfig


class TargetSpec(BaseModel):
    id: TargetId
    display_name: str
    kind: Literal["asic", "fpga", "shuttle"]
    process_node_nm: int | None = None
    vendor: str
    description: str
