# Worker Internals — `apps/worker`

The worker is where the real work happens. It's a Python 3.11+ process that
pulls jobs off Redis, runs them, and emits progress events. The same code is
also exposed as a CLI for local use without the hosted service.

## Directory map

```
apps/worker/
├── worker/
│   ├── __init__.py
│   ├── main.py            Entry point: Redis poller + dispatcher
│   ├── cli.py             `asicify` CLI for local compile/estimate
│   ├── config.py          Settings via pydantic-settings
│   ├── types.py           ModelGraph IR + CompressionConfig dataclasses
│   ├── pipeline/          Compression stages (parse → quantize → … → validate)
│   │   ├── parse.py
│   │   ├── quantize.py
│   │   ├── sparsity.py
│   │   ├── decompose.py
│   │   ├── validate.py
│   │   └── orchestrator.py
│   ├── rtl/               Verilog generation
│   │   ├── generator.py   Jinja2 → zip
│   │   └── templates/     *.v.j2, tb_top.py.j2, Makefile.j2, …
│   └── estimator/         Hardware estimation
│       ├── area.py
│       ├── throughput.py
│       ├── cost.py
│       ├── targets.py     Per-node cell library data
│       └── runner.py      Top-level estimate() + run_estimate_job()
├── pyproject.toml
└── package.json
```

## The two execution modes

### 1. Hosted job worker

[`worker/main.py`](../../apps/worker/worker/main.py) runs an `asyncio` loop:

```
BLPOP asicify:jobs (30s timeout)
   → parse JSON job
   → dispatch by job["job_type"] →
       compress  → run_compression_job
       rtl       → run_rtl_job
       estimate  → run_estimate_job
   → each emits progress events to asicify:progress:<project_id>
   → final event: {"event": "complete"}
```

The dispatcher passes an `emit` async callable to each job runner. This is
the **only** way the pipeline talks to the outside world. Pipeline code never
imports `redis` directly. This is what lets the same pipeline run via CLI
with `emit = print`.

### 2. CLI

[`worker/cli.py`](../../apps/worker/worker/cli.py) exposes `asicify compile`
and `asicify estimate`. It bypasses Redis and calls
`render_package(graph, config)` and `estimate(graph, config, target)`
directly. Output is a zip on disk plus JSON to stdout.

The CLI is the canonical "open-source core" experience. Everything in
`worker/{pipeline,rtl,estimator}/` must work from the CLI without the API.

## The `ModelGraph` IR

Defined in [`worker/types.py`](../../apps/worker/worker/types.py). Every
pipeline stage is `(ModelGraph, CompressionConfig) → ModelGraph`. Stages
return a new graph via `dataclasses.replace`; in-place mutation is forbidden.

```python
@dataclass
class ModelGraph:
    name: str
    task: Literal["language_modeling", "classification", "speech"]
    layers: list[LayerInfo]
    total_params: int
    metadata: dict[str, Any]
    quantization: dict[str, Quantization]   # populated by quantize.py
    sparsity_masks: dict[str, str]          # layer.name -> R2 key
    decompositions: dict[str, dict]         # layer.name -> decomp metadata
```

`LayerInfo` is the per-layer descriptor: name, kind (linear / attention /
ffn / layernorm / embedding / conv2d / other), feature dimensions, parameter
count.

## The pipeline — six stages

### Stage 1: Parse — `pipeline/parse.py`

`parse_model(model_source) → ModelGraph`. The full implementation uses
`torch.fx.symbolic_trace` to walk the model's forward graph and extract
layer structure. The MVP currently **synthesizes** a transformer-shaped
graph from a known parameter count (see `synthesize_transformer`); this is
a stub clearly marked in the file.

When you wire real parsing:

1. Load the model from HF or a local checkpoint.
2. Run `torch.fx.symbolic_trace`.
3. Walk `gm.graph.nodes`, classify each `call_module` node by its target
   class.
4. Map to `LayerInfo` entries.

The output IR doesn't change; only the function body does.

### Stage 2: Quantize — `pipeline/quantize.py`

`quantize_graph(graph, config) → ModelGraph` with `graph.quantization`
populated per-layer. Sensitivity heuristic: layernorms and embeddings step
up to INT8 even when the user asks for binary/ternary, because those layers
collapse otherwise.

The actual weight tensor work (rounding, scale calculation, bit-packing)
lives in `worker.kernels.*` (not yet implemented). The pipeline orchestrator
records *what* should happen; the kernel module is what executes the math.

This split is important: the orchestrator runs in milliseconds, drives the UI,
and is fully testable. Kernel work is GPU-bound and runs only when artifacts
are needed.

`estimate_quality_delta` is the analytical penalty model used until we wire
real validation. It maps quantization to a multiplicative perplexity penalty.
Source: empirical study, ASICify methodology doc.

### Stage 3: Sparsity — `pipeline/sparsity.py`

`apply_sparsity(graph, config) → ModelGraph` with `graph.sparsity_masks`
populated. Mask R2 keys are placeholders today. When wired:

- 2:4 / 4:8 — Wanda or one-shot SparseGPT, no retraining needed.
- Block-sparse 16×16 — magnitude pruning at block granularity.
- Unstructured — generic magnitude pruning.

LayerNorms and embeddings are skipped (they don't tile well into structured
sparsity patterns).

### Stage 4: Decompose — `pipeline/decompose.py`

`apply_decomposition(graph, config) → ModelGraph` with
`graph.decompositions` populated. Three algorithms:

- **Monarch** — `W ≈ P₁ B P₂ A P₃` with block-diagonal A, B. Parameters
  drop from `mn` to `O((m+n)·sqrt(mn))`.
- **Butterfly** — `O(log n)` factors with sparse structure.
- **Low-rank** — `W ≈ AB` with skinny inner dim (SVD init + fine-tune).

The `_blocks_for(m, n)` heuristic is `cbrt(m·n)` — a reasonable starting
point. Real Monarch implementations let you sweep block count.

### Stage 5: Validate — `pipeline/validate.py`

`validate_quality(graph, config, baseline) → dict[str, float]`. Returns
`{"baseline": …, "compressed": …, "delta_pct": …}`.

The MVP uses the analytical `estimate_quality_delta`. The real version runs
the compressed model against:

- LMs: WikiText perplexity (default), HellaSwag, ARC-Easy
- Classifiers: ImageNet top-1 (or task-specific dataset)
- Speech: LibriSpeech WER (Whisper)

The baseline number comes from a one-time inference pass before compression.

### Stage 6 (optional): Hardware-aware fine-tune

Not yet implemented. When added: short retraining run with quantization
simulation in the loop, straight-through estimator for non-differentiable
ops, 1–10K steps. Modal-backed GPU job, 5–30 min wall time. Toggled via
`config.fine_tune` and the `ENABLE_HARDWARE_AWARE_FT` flag.

### Orchestration — `pipeline/orchestrator.py`

`run_compression_job(job, emit)` runs the stages in sequence. Each stage:

1. `await emit({"event": "stage_start", "stage": name})`
2. Run the stage function.
3. `await emit({"event": "stage_complete", "stage": name, "duration_ms": n, "metrics": {...}})`

The `_stage` helper enforces this pattern. When you add a stage, call it via
`_stage(emit, "your_stage", your_function, *args)` and don't emit by hand.

`_cfg_from_dict(d)` is the converter from JSON job payload (sent via Redis)
to the typed `CompressionConfig` dataclass. The job submitter is the API,
which serializes Pydantic — so this converter is an implicit boundary
between Pydantic land and dataclass land.

## RTL generation

[`worker/rtl/generator.py`](../../apps/worker/worker/rtl/generator.py) is the
zip-emitting top-level. It:

1. Picks a multiplier strategy from the quantization choice.
2. Loads each Jinja2 template from `worker/rtl/templates/`.
3. Renders them with `(graph, config, multiplier)` in scope.
4. Packs everything into a zip in memory.
5. Returns `bytes` (caller uploads to R2).

### Multiplier strategy

The single most important hardware decision flows from quantization choice:

```python
def _multiplier_strategy(quantization):
    return {
        "binary":  "xnor_popcount",
        "ternary": "sign_flip_mux",
        "int4":    "csd_shift_add",
        "int8":    "booth",
        "fp16":    "fp16_lut",
    }[quantization]
```

The selected strategy is exposed to every template as the `multiplier`
variable. `linear_layer.v.j2` switches its inner-loop body on this — see
the `{% if multiplier == 'xnor_popcount' %}` blocks.

### Template inventory

| Template            | Output file               | Purpose                          |
| ------------------- | ------------------------- | -------------------------------- |
| `top.v.j2`          | `top.v`                   | Top-level wrapper, layer pipeline |
| `linear_layer.v.j2` | `modules/<name>.v`        | Linear / FFN MAC                 |
| `attention.v.j2`    | `modules/<name>.v`        | Attention block (shell)          |
| `layernorm.v.j2`    | `modules/<name>.v`        | LayerNorm                        |
| `embedding.v.j2`    | `modules/<name>.v`        | Embedding lookup                 |
| `kv_cache.v.j2`     | `kv_cache.v`              | Addressable BRAM                 |
| `weights.vh.j2`     | `weights/weights.vh`      | Hardwired weight constants       |
| `tb_top.py.j2`      | `tb_top.py`               | Cocotb testbench                 |
| `reference.py.j2`   | `reference.py`            | Bit-exact Python reference       |
| `Makefile.j2`       | `Makefile`                | sim / synth-yosys / synth-vivado |
| `yosys.tcl.j2`      | `synthesis/yosys.tcl`     | Yosys synthesis                  |
| `nextpnr.sh.j2`     | `synthesis/nextpnr.sh`    | nextpnr place-and-route (ECP5)   |
| `vivado.tcl.j2`     | `synthesis/vivado.tcl`    | Vivado synthesis (Xilinx)        |
| `README.md.j2`      | `README.md`               | User-facing package docs         |

### Template conventions

- **Jinja2 `StrictUndefined`** — undefined variables raise an error rather
  than silently rendering empty. This catches typos early.
- **`trim_blocks` and `lstrip_blocks`** — keeps generated Verilog readable.
- **No filter pipelines beyond `replace`** — keep templates dumb. Logic
  belongs in `generator.py`.
- **All Verilog modules use `\`default_nettype none`** at top + `wire` at
  bottom — catches accidentally-unconnected wires during synthesis.

### What the templates *don't* do

The current templates emit shells. The real per-layer body (especially
`attention.v.j2`) needs:

- Q/K/V projection submodule instantiation.
- Scaled dot-product with parallel reduction.
- Softmax via small lookup table (or piecewise polynomial).
- Output projection.
- Connection to KV cache.

Each of these is one PR's worth of work. The shape is decided; it's just
implementation.

## Estimator

[`worker/estimator/runner.py`](../../apps/worker/worker/estimator/runner.py)
provides the top-level `estimate(graph, config, target) → dict` that
combines area + throughput + cost + energy.

### `estimator/area.py`

`estimate_area(graph, config, target) → dict[str, float]` returns the area
breakdown in mm²:

```
storage_mm2          = effective_params × bits_per_weight × rom_bit_um2
compute_mm2          = mul_count × multiplier_area × precision_scale
sram_mm2             = 4MB × 8 × sram_bit_um2 × 0.05  # 5% utilization
io_mm2               = 0.5  # ~80 pads at typical pitch
routing_overhead_mm2 = 0.5 × (storage + compute + sram)
```

The 1.5× routing overhead is empirical for digital-only designs; mixed-signal
or high-IO designs would need a different multiplier.

`_effective_param_count` applies sparsity + decomposition:

- Sparsity: `params *= 1 - ratio`
- Monarch / butterfly: `params *= 0.35` (heuristic for typical models)
- Low-rank: `params *= min(1.0, 2·rank / 512)`

### `estimator/throughput.py`

`estimate_throughput(graph, target) → {max_clock_mhz, cycles_per_token,
throughput_per_sec, latency_ms}`.

The model is "largest layer's MACs / 4096 parallel multipliers, at f_max".
This assumes a fully pipelined design where the throughput bottleneck is the
single biggest layer. For tile-based designs it would be different.

### `estimator/cost.py`

`estimate_cost(area_mm2, target) → {1000, 100000, 1000000}` returning USD
per chip. Three branches: ASIC nodes (Murphy yield + NRE amortization),
FPGAs (flat unit cost lookup), shuttles (TinyTapeout = $300 fixed,
chipIgnite = NRE-only at low volumes).

The Murphy yield model:

```
A = area_cm² × defect_density_per_cm²
yield = ((1 - exp(-A)) / A)²
```

This is the same formula every silicon cost calculator uses; we cap at 0.10
to prevent absurd low-yield results from pushing per-chip cost to infinity.

### `estimator/targets.py`

The cell library data table. Each ASIC node has a `NodeParams` row with:

- `rom_bit_um2` — area for one mask-ROM bit
- `sram_bit_um2` — area for one SRAM bit
- `mul_int8_um2` — area for one INT8 multiplier (reference)
- `fmax_mhz` — typical max clock for pipelined logic
- `energy_int8_pj` — energy per INT8 MAC
- `wafer_cost_usd`, `wafer_diameter_mm`, `nre_usd`, `defect_density_cm2`

These numbers are from published academic surveys and foundry data sheets.
They have ±20–40% uncertainty; the estimator surfaces this as the
`confidence` field in the response. Refining these is a contributor-friendly
PR — add a citation in the commit message.

## Configuration and credentials

[`worker/config.py`](../../apps/worker/worker/config.py) reads the same env
vars as the API. `REDIS_URL` and the R2 credentials are the only ones the
worker actually uses.

The HF cache lives at `./.cache/huggingface` by default; the artifact
staging dir at `./.cache/artifacts`. Both are gitignored.

## Modal deployment (planned)

The worker is designed to run on Modal — one container per job, scales to
zero. The Modal app definition will go in `worker/main.py` as a sibling
entry point:

```python
import modal
app = modal.App("asicify-worker")
image = modal.Image.debian_slim().pip_install_from_pyproject("pyproject.toml")
@app.function(image=image, gpu="A10G", timeout=1800)
def run_job(job: dict): ...
```

The same `dispatch` function in `main.py` will be the body. Adding Modal
shouldn't require pipeline changes.

## Performance considerations

- **Pipeline stage caching** — by `hash(input_graph, config)`. Not yet
  implemented but the orchestrator's purity is what makes it free to add.
- **GPU vs CPU** — quantization and sparsity want GPU; RTL gen and estimator
  are CPU-only. Modal lets us pick per-job.
- **Memory** — for large models (10B+) we'll hit memory ceilings. The
  workaround is layer-by-layer streaming — load one layer's weights, quantize,
  write back, free. The current dataclass-passing design is fine; it's the
  kernel module that needs streaming-aware code.

## Testing strategy (planned)

- **Pure functions first** — area/throughput/cost are arithmetic, easy to
  golden-test against fixtures.
- **Pipeline stages** — `(input_graph, config) → output_graph` round-trips
  with deepequal assertions.
- **RTL generation** — render to a tempdir, then run `verilator --lint-only`
  on the output to catch syntax errors. Add this to CI.
- **End-to-end** — `asicify compile gpt2 --output /tmp/out`, then assert the
  zip contains expected files and the cocotb sim completes.

When you add tests, put them in `apps/worker/tests/` mirroring the package
layout.
