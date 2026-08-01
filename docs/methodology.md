# Methodology

> Why our cost models work, where they're wrong, and how we report uncertainty.

## Compression quality

We measure quality on a held-out benchmark suite per task type:

- **Language modeling**: WikiText perplexity (default), HellaSwag, ARC-Easy
- **Classification**: ImageNet top-1, or task-specific dataset
- **Speech**: LibriSpeech WER (Whisper family)

Quality numbers are reported as deltas from the user's baseline checkpoint, not
from absolute leaderboards. This matters because users care whether their
*specific* model survived compression, not whether the family is competitive.

## Hardware estimation

Our area model sums:

```
Total = storage + compute + SRAM + I/O + routing_overhead
```

- **Storage**: `effective_params × bits_per_weight × rom_bit_um2`
- **Compute**: `multiplier_count × multiplier_area × precision_scale`
- **SRAM**: KV cache + activation buffers, sized from compute graph
- **I/O**: fixed for typical pad count
- **Routing**: 1.5× of (storage + compute + SRAM)

### Per-target cell library data

Numbers are bootstrapped from published academic data and refined over time.
See `apps/worker/worker/estimator/targets.py`.

| Node       | Source                               |
| ---------- | ------------------------------------ |
| sky130     | SkyWater open PDK + OpenLane reports |
| GF22FDX    | Public foundry data sheets           |
| TSMC 28nm  | Academic survey papers               |
| TSMC 16nm  | Academic survey papers               |
| TSMC 7nm   | Estimated from 16/10 scaling laws    |

### Confidence intervals

Always shown as ±20–40% bands. Sources of uncertainty:

- Yield variance across foundries and lots
- Layout efficiency (ours assumes ~85% array utilization)
- Foundry pricing varies by customer relationship
- 7nm numbers are extrapolated and should not drive tape-out decisions

## Multiplier strategies by precision

| Precision | Strategy             | Approx LUTs/MAC | Notes                                  |
| --------- | -------------------- | --------------- | -------------------------------------- |
| binary    | XNOR + bit-count     | 1               | Sign-only weights                      |
| ternary   | sign-flip + zero-out | 3               | {-α, 0, +α} per layer                  |
| INT4      | CSD shift-add        | ≤ 1 add         | Each weight as ±2^a ± 2^b              |
| INT8      | Booth                | ~10             | Standard                               |
| FP16      | LUT-based            | small ROM       | E5M10 with shared exponent fallback    |

## Cost per chip

For each volume tier we compute:

```
unit_cost = (bare_die_cost + package + test) × margin
total     = unit_cost + NRE / volume
```

Where `bare_die_cost = wafer_cost / good_dies_per_wafer`, and yield uses
Murphy's model:

```
yield = ((1 - exp(-A·D)) / (A·D))²    where A=area_cm², D=defect_density
```

## Reproducibility

Every estimate is pinned to a config hash. The same hash from the same git
revision produces the same numbers, deterministically. Cite the hash in
methodology sections.

## What we *don't* model (yet)

- Process variation across corners (TT/SS/FF)
- Aging / NBTI effects on Fmax
- Thermal effects under sustained inference
- Multi-die / chiplet partitioning
- Mixed-signal blocks (only digital paths)

These are roadmap items. For tape-out-grade signoff, use commercial EDA
tools; ASICify is for feasibility analysis and design space exploration.
