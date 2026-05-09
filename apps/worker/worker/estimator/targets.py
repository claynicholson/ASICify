"""Per-target cell library data. Mirrors apps/api/app/data/targets.py.

Bootstrap with published academic numbers; refine over time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeParams:
    rom_bit_um2: float
    sram_bit_um2: float
    mul_int8_um2: float
    fmax_mhz: float
    energy_int8_pj: float
    wafer_cost_usd: float
    wafer_diameter_mm: float
    nre_usd: float
    defect_density_cm2: float


# Numbers from public papers, foundry data sheets, and academic estimates.
# All have ±20–40% uncertainty; the estimator surfaces this as confidence bands.
ASIC_NODES: dict[str, NodeParams] = {
    "sky130": NodeParams(1.2, 4.0, 2400, 250, 0.9, 1500, 200, 50_000, 0.5),
    "gf22fdx": NodeParams(0.18, 0.55, 380, 1200, 0.18, 5500, 300, 1_500_000, 0.15),
    "tsmc28": NodeParams(0.22, 0.7, 480, 1000, 0.24, 4500, 300, 1_200_000, 0.12),
    "tsmc16": NodeParams(0.08, 0.28, 180, 1500, 0.10, 7500, 300, 5_000_000, 0.10),
    "tsmc7": NodeParams(0.025, 0.09, 60, 2200, 0.04, 14_000, 300, 25_000_000, 0.08),
}


@dataclass(frozen=True)
class FpgaParams:
    name: str
    luts: int
    dsp_blocks: int
    bram_kbit: int
    fmax_mhz: float
    unit_cost_usd: float


FPGAS: dict[str, FpgaParams] = {
    "ecp5": FpgaParams("LFE5UM5G-85", 84_000, 156, 3_744, 200, 35),
    "crosslinknx": FpgaParams("LIFCL-40", 39_000, 156, 2_400, 250, 25),
    "artix7": FpgaParams("XC7A100T", 134_600, 740, 13_140, 300, 75),
    "kria": FpgaParams("K26 SoM", 256_200, 1_248, 25_104, 400, 250),
}


def is_asic(target: str) -> bool:
    return target in ASIC_NODES or target in ("tinytapeout", "chipignite")


def is_fpga(target: str) -> bool:
    return target in FPGAS
