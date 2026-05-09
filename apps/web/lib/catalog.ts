import type { CatalogModel } from "@asicify/shared";

// Curated catalog. Mirrors apps/api/app/data/catalog.py.
// 30 models that work well for compression + RTL gen.
export const MODEL_CATALOG: CatalogModel[] = [
  {
    id: "tinyllama-1.1b",
    hf_id: "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    display_name: "TinyLlama 1.1B Chat",
    family: "Llama",
    task: "language_modeling",
    parameters: 1_100_000_000,
    recommended_compression: {
      quantization: "int4",
      sparsity: { type: "structured_2_4", ratio: 0.5 },
      decomposition: { type: "none" },
      fine_tune: false,
      fine_tune_steps: 1000,
    },
  },
  {
    id: "gpt2-small",
    hf_id: "gpt2",
    display_name: "GPT-2 Small (124M)",
    family: "GPT",
    task: "language_modeling",
    parameters: 124_000_000,
    recommended_compression: {
      quantization: "int4",
      sparsity: { type: "none", ratio: 0 },
      decomposition: { type: "none" },
      fine_tune: false,
      fine_tune_steps: 1000,
    },
  },
  {
    id: "distilbert-base",
    hf_id: "distilbert-base-uncased",
    display_name: "DistilBERT Base",
    family: "BERT",
    task: "language_modeling",
    parameters: 66_000_000,
    recommended_compression: {
      quantization: "int8",
      sparsity: { type: "structured_2_4", ratio: 0.5 },
      decomposition: { type: "none" },
      fine_tune: false,
      fine_tune_steps: 1000,
    },
  },
  {
    id: "mobilebert",
    hf_id: "google/mobilebert-uncased",
    display_name: "MobileBERT",
    family: "BERT",
    task: "language_modeling",
    parameters: 25_000_000,
    recommended_compression: {
      quantization: "int8",
      sparsity: { type: "none", ratio: 0 },
      decomposition: { type: "none" },
      fine_tune: false,
      fine_tune_steps: 1000,
    },
  },
  {
    id: "resnet18",
    hf_id: "microsoft/resnet-18",
    display_name: "ResNet-18",
    family: "ResNet",
    task: "classification",
    parameters: 11_700_000,
    recommended_compression: {
      quantization: "int8",
      sparsity: { type: "none", ratio: 0 },
      decomposition: { type: "none" },
      fine_tune: false,
      fine_tune_steps: 1000,
    },
  },
  {
    id: "mobilenet-v3",
    hf_id: "google/mobilenet_v3_small_1.0_224",
    display_name: "MobileNet V3 Small",
    family: "MobileNet",
    task: "classification",
    parameters: 2_500_000,
    recommended_compression: {
      quantization: "int4",
      sparsity: { type: "none", ratio: 0 },
      decomposition: { type: "none" },
      fine_tune: false,
      fine_tune_steps: 1000,
    },
  },
  {
    id: "whisper-tiny",
    hf_id: "openai/whisper-tiny",
    display_name: "Whisper Tiny",
    family: "Whisper",
    task: "speech",
    parameters: 39_000_000,
    recommended_compression: {
      quantization: "int8",
      sparsity: { type: "none", ratio: 0 },
      decomposition: { type: "none" },
      fine_tune: false,
      fine_tune_steps: 1000,
    },
  },
];

/** Approximate MACs per token/inference for a model (used by quick estimator). */
export function opsPerInference(params: number): number {
  // Crude: ~2× params for transformer forward, 2× for MAC = 4× params per token
  return params * 4;
}
