import type { TargetId } from "./types";

export interface TargetSpec {
  id: TargetId;
  display_name: string;
  kind: "asic" | "fpga" | "shuttle";
  process_node_nm?: number;
  vendor: string;
  description: string;
}

export const TARGETS: Record<TargetId, TargetSpec> = {
  sky130: {
    id: "sky130",
    display_name: "SkyWater 130nm",
    kind: "asic",
    process_node_nm: 130,
    vendor: "SkyWater",
    description: "Open-source PDK. Good for first tape-outs and academic work.",
  },
  gf22fdx: {
    id: "gf22fdx",
    display_name: "GlobalFoundries 22FDX",
    kind: "asic",
    process_node_nm: 22,
    vendor: "GlobalFoundries",
    description: "FD-SOI process, low-power, good for edge AI.",
  },
  tsmc28: {
    id: "tsmc28",
    display_name: "TSMC 28nm",
    kind: "asic",
    process_node_nm: 28,
    vendor: "TSMC",
    description: "Mature commercial node. Great cost/performance for inference.",
  },
  tsmc16: {
    id: "tsmc16",
    display_name: "TSMC 16nm",
    kind: "asic",
    process_node_nm: 16,
    vendor: "TSMC",
    description: "FinFET. Higher density, higher NRE.",
  },
  tsmc7: {
    id: "tsmc7",
    display_name: "TSMC 7nm",
    kind: "asic",
    process_node_nm: 7,
    vendor: "TSMC",
    description: "Leading-edge. Estimates only; requires production tape-out partner.",
  },
  ecp5: {
    id: "ecp5",
    display_name: "Lattice ECP5",
    kind: "fpga",
    vendor: "Lattice",
    description: "Open-source toolchain (yosys + nextpnr). Cheap prototyping.",
  },
  crosslinknx: {
    id: "crosslinknx",
    display_name: "Lattice CrossLink-NX",
    kind: "fpga",
    vendor: "Lattice",
    description: "Low-power edge FPGA, on-chip flash.",
  },
  artix7: {
    id: "artix7",
    display_name: "Xilinx Artix-7",
    kind: "fpga",
    vendor: "AMD/Xilinx",
    description: "Vivado toolchain. Good mid-range FPGA target.",
  },
  kria: {
    id: "kria",
    display_name: "Xilinx Kria K26",
    kind: "fpga",
    vendor: "AMD/Xilinx",
    description: "SoM with onboard ARM. Good for production edge deployments.",
  },
  tinytapeout: {
    id: "tinytapeout",
    display_name: "TinyTapeout (sky130 shuttle)",
    kind: "shuttle",
    process_node_nm: 130,
    vendor: "TinyTapeout",
    description: "$300/tile mini-shuttle. Tiny designs only.",
  },
  chipignite: {
    id: "chipignite",
    display_name: "Efabless chipIgnite (sky130)",
    kind: "shuttle",
    process_node_nm: 130,
    vendor: "Efabless",
    description: "MPW shuttle, ~$10K. Larger designs than TinyTapeout.",
  },
};

export const TARGET_LIST: TargetSpec[] = Object.values(TARGETS);
