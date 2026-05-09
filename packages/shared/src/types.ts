// Shared types used across web, api, and (mirrored in) the Python worker.
// Keep aligned with apps/api/app/schemas.py and apps/worker/worker/types.py.

export type Quantization = "fp16" | "int8" | "int4" | "ternary" | "binary";

export type SparsityType =
  | "none"
  | "structured_2_4"
  | "structured_4_8"
  | "block_sparse_16"
  | "unstructured";

export type DecompositionType = "none" | "monarch" | "butterfly" | "low_rank";

export type ProjectStatus =
  | "draft"
  | "queued"
  | "running"
  | "complete"
  | "failed";

export type TargetId =
  | "sky130"
  | "gf22fdx"
  | "tsmc28"
  | "tsmc16"
  | "tsmc7"
  | "ecp5"
  | "crosslinknx"
  | "artix7"
  | "kria"
  | "tinytapeout"
  | "chipignite";

export interface ModelSource {
  type: "huggingface" | "upload" | "onnx";
  id?: string; // hf id or uploaded artifact id
  url?: string;
}

export interface SparsityConfig {
  type: SparsityType;
  ratio: number; // 0..1
}

export interface DecompositionConfig {
  type: DecompositionType;
  rank?: number;
}

export interface CompressionConfig {
  quantization: Quantization;
  sparsity: SparsityConfig;
  decomposition: DecompositionConfig;
  fine_tune: boolean;
  fine_tune_steps: number;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  model_source: ModelSource;
  compression_config: CompressionConfig;
  target_hardware: TargetId[];
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  artifact_ids: string[];
  metrics?: ProjectMetrics;
}

export interface ProjectMetrics {
  baseline_perplexity?: number;
  compressed_perplexity?: number;
  baseline_accuracy?: number;
  compressed_accuracy?: number;
  baseline_param_count: number;
  compressed_param_count: number;
  size_reduction: number; // 0..1
  effective_bits_per_weight: number;
}

export interface Artifact {
  id: string;
  project_id: string;
  type:
    | "rtl_package"
    | "report_pdf"
    | "compressed_model"
    | "hardware_estimate"
    | "compute_graph";
  r2_key: string;
  size_bytes: number;
  created_at: string;
}

export interface CostByVolume {
  "1000": number;
  "100000": number;
  "1000000": number;
}

export interface AreaBreakdown {
  storage_mm2: number;
  compute_mm2: number;
  sram_mm2: number;
  io_mm2: number;
  routing_overhead_mm2: number;
}

export interface HardwareEstimate {
  target: TargetId;
  area_mm2: number;
  area_breakdown: AreaBreakdown;
  max_clock_mhz: number;
  throughput_per_sec: number;
  energy_per_op_pj: number;
  cost_per_chip: CostByVolume;
  confidence: number; // 0..1
  notes?: string;
}

export interface CatalogModel {
  id: string;
  hf_id: string;
  display_name: string;
  family: string;
  task: "language_modeling" | "classification" | "speech";
  parameters: number;
  recommended_compression: CompressionConfig;
}

export type ProgressEvent =
  | { event: "stage_start"; project_id: string; stage: string }
  | {
      event: "stage_complete";
      project_id: string;
      stage: string;
      duration_ms: number;
      metrics?: Record<string, number>;
    }
  | { event: "log"; project_id: string; level: "info" | "warn" | "error"; message: string }
  | { event: "error"; project_id: string; message: string }
  | { event: "complete"; project_id: string };
