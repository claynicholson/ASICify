// Client-side hardware estimator. Mirrors apps/worker/worker/estimator/* with
// simplified math, so the playground can update within ~500ms as users move sliders.
//
// All numbers are first-order approximations with ±30% confidence bands. The
// authoritative estimates come from the worker.

import type {
  CompressionConfig,
  HardwareEstimate,
  Quantization,
  TargetId,
} from "@asicify/shared";

interface NodeParams {
  // Effective area for one storage bit (mask ROM), in µm²
  rom_bit_um2: number;
  // SRAM bit area in µm²
  sram_bit_um2: number;
  // INT8 multiplier area in µm²
  mul_int8_um2: number;
  // Max realistic clock for pipelined logic (MHz)
  fmax_mhz: number;
  // Energy per INT8 MAC, pJ
  energy_int8_pj: number;
  // Wafer cost ($)
  wafer_cost: number;
  // Wafer diameter mm
  wafer_diameter: number;
  // NRE cost (mask + setup, $)
  nre: number;
  // Defect density per cm² (Murphy's model)
  defect_density: number;
}

// Bootstrap numbers from published academic data. Refine over time.
const NODE_PARAMS: Record<TargetId, NodeParams> = {
  sky130: { rom_bit_um2: 1.2, sram_bit_um2: 4.0, mul_int8_um2: 2400, fmax_mhz: 250, energy_int8_pj: 0.9, wafer_cost: 1500, wafer_diameter: 200, nre: 50_000, defect_density: 0.5 },
  gf22fdx: { rom_bit_um2: 0.18, sram_bit_um2: 0.55, mul_int8_um2: 380, fmax_mhz: 1200, energy_int8_pj: 0.18, wafer_cost: 5500, wafer_diameter: 300, nre: 1_500_000, defect_density: 0.15 },
  tsmc28: { rom_bit_um2: 0.22, sram_bit_um2: 0.7, mul_int8_um2: 480, fmax_mhz: 1000, energy_int8_pj: 0.24, wafer_cost: 4500, wafer_diameter: 300, nre: 1_200_000, defect_density: 0.12 },
  tsmc16: { rom_bit_um2: 0.08, sram_bit_um2: 0.28, mul_int8_um2: 180, fmax_mhz: 1500, energy_int8_pj: 0.1, wafer_cost: 7500, wafer_diameter: 300, nre: 5_000_000, defect_density: 0.1 },
  tsmc7: { rom_bit_um2: 0.025, sram_bit_um2: 0.09, mul_int8_um2: 60, fmax_mhz: 2200, energy_int8_pj: 0.04, wafer_cost: 14_000, wafer_diameter: 300, nre: 25_000_000, defect_density: 0.08 },
  ecp5: { rom_bit_um2: 0, sram_bit_um2: 0, mul_int8_um2: 0, fmax_mhz: 200, energy_int8_pj: 1.5, wafer_cost: 0, wafer_diameter: 0, nre: 0, defect_density: 0 },
  crosslinknx: { rom_bit_um2: 0, sram_bit_um2: 0, mul_int8_um2: 0, fmax_mhz: 250, energy_int8_pj: 1.2, wafer_cost: 0, wafer_diameter: 0, nre: 0, defect_density: 0 },
  artix7: { rom_bit_um2: 0, sram_bit_um2: 0, mul_int8_um2: 0, fmax_mhz: 300, energy_int8_pj: 1.4, wafer_cost: 0, wafer_diameter: 0, nre: 0, defect_density: 0 },
  kria: { rom_bit_um2: 0, sram_bit_um2: 0, mul_int8_um2: 0, fmax_mhz: 400, energy_int8_pj: 1.0, wafer_cost: 0, wafer_diameter: 0, nre: 0, defect_density: 0 },
  tinytapeout: { rom_bit_um2: 1.2, sram_bit_um2: 4.0, mul_int8_um2: 2400, fmax_mhz: 50, energy_int8_pj: 1.2, wafer_cost: 0, wafer_diameter: 0, nre: 300, defect_density: 0.5 },
  chipignite: { rom_bit_um2: 1.2, sram_bit_um2: 4.0, mul_int8_um2: 2400, fmax_mhz: 250, energy_int8_pj: 0.9, wafer_cost: 0, wafer_diameter: 0, nre: 10_000, defect_density: 0.5 },
};

const BITS_PER_WEIGHT: Record<Quantization, number> = {
  fp16: 16,
  int8: 8,
  int4: 4,
  ternary: 1.6, // log2(3) effective
  binary: 1,
};

// Multiplier area scales relative to INT8. Empirical/heuristic.
const MUL_AREA_SCALE: Record<Quantization, number> = {
  fp16: 4.0,
  int8: 1.0,
  int4: 0.18, // CSD shift-add networks
  ternary: 0.04, // sign-flip mux
  binary: 0.015, // XNOR + popcount
};

// Quality penalty (perplexity multiplier for LMs, accuracy delta for classifiers).
// First-order; the worker validates with real data.
const QUALITY_PENALTY: Record<Quantization, number> = {
  fp16: 1.0,
  int8: 1.005,
  int4: 1.04,
  ternary: 1.18,
  binary: 1.45,
};

export interface QuickEstimateInput {
  param_count: number;
  ops_per_token: number; // total MACs
  config: CompressionConfig;
  target: TargetId;
  baseline_metric?: number; // perplexity or 1-accuracy
}

export interface QuickEstimate extends HardwareEstimate {
  estimated_metric: number;
  bits_per_weight: number;
  effective_param_count: number;
}

/** Apply sparsity + decomposition to get effective parameter count. */
export function effectiveParams(params: number, config: CompressionConfig): number {
  let p = params;
  if (config.sparsity.type !== "none") {
    p *= 1 - config.sparsity.ratio;
  }
  if (config.decomposition.type === "monarch" || config.decomposition.type === "butterfly") {
    // Monarch/butterfly factorization compresses dense layers by O(sqrt(n))
    p *= 0.35;
  } else if (config.decomposition.type === "low_rank") {
    const rank = config.decomposition.rank ?? 64;
    // crude: assume mean dim ~512
    p *= Math.min(1.0, (rank * 2) / 512);
  }
  return p;
}

export function quickEstimate(input: QuickEstimateInput): QuickEstimate {
  const { param_count, ops_per_token, config, target } = input;
  const params = NODE_PARAMS[target];
  const bpw = BITS_PER_WEIGHT[config.quantization];
  const eff = effectiveParams(param_count, config);

  const isFpga = params.wafer_cost === 0 && target.startsWith("ecp5") || ["ecp5", "crosslinknx", "artix7", "kria"].includes(target);

  // Storage area (mask ROM)
  const storage_um2 = eff * bpw * params.rom_bit_um2;
  // Compute area (multipliers; crude — assume 1 multiplier per output channel batched)
  const mul_count = Math.min(eff, 4096);
  const compute_um2 = mul_count * params.mul_int8_um2 * MUL_AREA_SCALE[config.quantization];
  // SRAM (KV cache, activations) — estimate 4MB ceiling
  const sram_um2 = 4 * 1024 * 1024 * 8 * params.sram_bit_um2 * 0.05;
  // I/O ring (fixed-ish)
  const io_um2 = 0.5 * 1_000_000;
  // Routing overhead 1.5×
  const subtotal = storage_um2 + compute_um2 + sram_um2;
  const routing_um2 = subtotal * 0.5;

  const total_um2 = storage_um2 + compute_um2 + sram_um2 + io_um2 + routing_um2;
  const total_mm2 = total_um2 / 1_000_000;

  // Throughput
  const cycles_per_token = Math.max(1, Math.ceil(ops_per_token / Math.max(mul_count, 1)));
  const fmax = params.fmax_mhz * 1e6;
  const throughput = fmax / cycles_per_token;

  // Energy
  const energy_per_op_pj = params.energy_int8_pj * MUL_AREA_SCALE[config.quantization];

  // Cost (ASIC only)
  const cost_per_chip = isFpga
    ? { "1000": fpgaUnitCost(target), "100000": fpgaUnitCost(target), "1000000": fpgaUnitCost(target) }
    : computeAsicCost(total_mm2, params);

  const baseline = input.baseline_metric ?? 10;
  const estimated_metric = baseline * QUALITY_PENALTY[config.quantization];

  return {
    target,
    area_mm2: total_mm2,
    area_breakdown: {
      storage_mm2: storage_um2 / 1e6,
      compute_mm2: compute_um2 / 1e6,
      sram_mm2: sram_um2 / 1e6,
      io_mm2: io_um2 / 1e6,
      routing_overhead_mm2: routing_um2 / 1e6,
    },
    max_clock_mhz: params.fmax_mhz,
    throughput_per_sec: throughput,
    energy_per_op_pj,
    cost_per_chip,
    confidence: isFpga ? 0.85 : 0.65,
    estimated_metric,
    bits_per_weight: bpw,
    effective_param_count: eff,
  };
}

function fpgaUnitCost(target: TargetId): number {
  const COSTS: Partial<Record<TargetId, number>> = {
    ecp5: 35,
    crosslinknx: 25,
    artix7: 75,
    kria: 250,
  };
  return COSTS[target] ?? 50;
}

function computeAsicCost(area_mm2: number, p: NodeParams) {
  if (p.wafer_cost === 0) return { "1000": 0, "100000": 0, "1000000": 0 };
  const wafer_area_mm2 = Math.PI * (p.wafer_diameter / 2) ** 2;
  const die_area_with_scribe = area_mm2 * 1.05;
  const dies_per_wafer = Math.floor((wafer_area_mm2 * 0.85) / die_area_with_scribe);
  // Murphy yield model
  const D0 = p.defect_density;
  const yieldFn = (a: number) => Math.pow((1 - Math.exp(-a * D0 / 100)) / (a * D0 / 100 || 1), 2);
  const y = Math.max(0.1, yieldFn(area_mm2));
  const good_dies = Math.max(1, dies_per_wafer * y);
  const bare_die_cost = p.wafer_cost / good_dies;
  const package_cost = 2.5;
  const test_cost = 0.5;
  const margin = 1.4;
  const unit = (bare_die_cost + package_cost + test_cost) * margin;

  return {
    "1000": unit + p.nre / 1_000,
    "100000": unit + p.nre / 100_000,
    "1000000": unit + p.nre / 1_000_000,
  };
}
