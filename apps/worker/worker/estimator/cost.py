"""Cost model. For each volume tier:
  wafer cost / dies-per-wafer (Murphy yield)
  + NRE amortized over volume
  + packaging + test
  × margin
"""

from __future__ import annotations

import math

from worker.estimator.targets import ASIC_NODES, FPGAS, NodeParams


def estimate_cost(area_mm2: float, target: str) -> dict[int, float]:
    if target in FPGAS:
        unit = FPGAS[target].unit_cost_usd
        return {1_000: unit, 100_000: unit, 1_000_000: unit}
    if target == "tinytapeout":
        # $300 per tile, fixed
        return {1_000: 300.0, 100_000: 300.0, 1_000_000: 300.0}
    if target == "chipignite":
        nre = 10_000.0
        return {1_000: nre / 1_000, 100_000: nre / 100_000, 1_000_000: nre / 1_000_000}
    if target not in ASIC_NODES:
        return {1_000: 0.0, 100_000: 0.0, 1_000_000: 0.0}

    p = ASIC_NODES[target]
    return _asic_cost(area_mm2, p)


def _asic_cost(area_mm2: float, p: NodeParams) -> dict[int, float]:
    wafer_area_mm2 = math.pi * (p.wafer_diameter_mm / 2) ** 2
    die_with_scribe = area_mm2 * 1.05
    dies_per_wafer = max(1, int((wafer_area_mm2 * 0.85) // die_with_scribe))

    # Murphy yield model
    a = (area_mm2 * p.defect_density_cm2) / 100
    if a == 0:
        y = 1.0
    else:
        y = ((1 - math.exp(-a)) / a) ** 2
    y = max(0.1, y)

    good_dies = max(1, dies_per_wafer * y)
    bare_die_cost = p.wafer_cost_usd / good_dies
    package_cost = 2.5
    test_cost = 0.5
    margin = 1.4
    unit = (bare_die_cost + package_cost + test_cost) * margin

    return {
        1_000: unit + p.nre_usd / 1_000,
        100_000: unit + p.nre_usd / 100_000,
        1_000_000: unit + p.nre_usd / 1_000_000,
    }
