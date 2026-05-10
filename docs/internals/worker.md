# Worker Internals — `apps/worker`

Where the real work happens. Python 3.11+ process that takes a model and
produces synthesizable Verilog plus a bit-exact reference plus a hardware
estimate. The same code runs as a CLI for local use without the hosted
service.

This page is a high-level orientation. The deep dives:

- [kernels.md](kernels.md) — every kernel module in detail
- [rtl-templates.md](rtl-templates.md) — every Verilog template
- [testing.md](testing.md) — how the 62 tests are organized

## Directory map

```
apps/worker/
├── worker/
│   ├── __init__.py
│   ├── main.py            Redis poller + dispatcher (hosted job mode)
│   ├── cli.py             asicify demo / asicify estimate (CLI mode)
│   ├── modal_app.py       Modal deployment definition
│   ├── config.py          pydantic-settings
│   ├── types.py           ModelGraph, LayerInfo, CompressionConfig dataclasses
│   ├── kernels/           Tensor work — pure functions, no I/O
│   │   ├── __init__.py
│   │   ├── quantize.py    INT8 / INT4 / ternary / binary + bit-exact forward
│   │   ├── pack.py        Tensor -> SystemVerilog literal strings
│   │   ├── sparsity.py    2:4, 4:8, block-16, unstructured pruning
│   │   ├── layers.py      LayerNorm, Embedding, QuantizedAttention dataclasses
│   │   └── attention.py   Integer softmax + reference attention
│   ├── pipeline/          Orchestration — calls kernels in order
│   │   ├── parse.py       torch.fx-style module walk
│   │   ├── sparsity.py    Wraps kernels.sparsity, runs before quantize
│   │   ├── decompose.py   Records config; structural decomp is roadmap
│   │   ├── quantize.py    Dispatches to kernels.quantize per layer kind
│   │   ├── validate.py    Real activation-MSE vs original float model
│   │   └── orchestrator.py Stage pipeline + emit hooks
│   ├── loaders/           Model loaders
│   │   ├── __init__.py
│   │   └── huggingface.py transformers loader (in `hosted` extra)
│   ├── rtl/               Verilog generation
│   │   ├── generator.py   Jinja2 -> zip
│   │   └── templates/     14 .j2 files (see rtl-templates.md)
│   └── estimator/         Hardware estimation
│       ├── area.py
│       ├── throughput.py
│       ├── cost.py
│       ├── targets.py     Per-node cell library data
│       └── runner.py      Top-level estimate()
├── tests/                 62 pytest tests
├── pyproject.toml
└── package.json
```

## The two execution modes

### CLI

```bash
cd apps/worker
python -m uv run asicify demo --output ./build/demo
```

`worker/cli.py` defines `TinyMLP` and runs the full pipeline against it.
End-to-end demo that's also the canonical sanity check.

### Hosted job worker

`worker/main.py` runs an asyncio loop that BLPOPs Redis and dispatches
to `run_compression_job`, `run_rtl_job`, or `run_estimate_job`. Each
runner emits progress events to a Redis pub/sub channel. The API
forwards those events to the browser over WebSocket.

```
BLPOP asicify:jobs (30s timeout)
   → parse JSON job
   → dispatch by job["job_type"]
   → emit start/progress/complete events to asicify:progress:<project_id>
```

## The `ModelGraph` IR

Defined in `worker/types.py`. Every pipeline stage takes and returns a
`ModelGraph`. Stages produce new graphs via `dataclasses.replace`;
in-place mutation is forbidden.

Key fields:
- `layers: list[LayerInfo]` — the structural model description
- `quantization: dict[str, str]` — per-layer precision choices (post-quantize)
- `metadata: dict[str, Any]` — internal state used by later stages

Internal metadata keys (all start with `_` to mark as non-serializable):
- `_weights[name] -> float Tensor` — populated by parse.py
- `_biases[name] -> float Tensor | None`
- `_modules[name] -> nn.Module` — for layernorm/embedding (need the module
  for eps, normalized_shape, etc.)
- `_root_module -> nn.Module` — the entire original model, used by
  validate.py to run forward passes
- `_quantized[name] -> QuantizedLinear | QuantizedLayerNorm | QuantizedEmbedding`
- `_sparsity_ratios[name] -> float` — fraction of pruned weights

## The pipeline

```
parse_model(model_source)
   ↓ ModelGraph with _weights, _biases, _modules, _root_module
apply_sparsity(graph, config)
   ↓ ModelGraph with _weights replaced by pruned versions
apply_decomposition(graph, config)
   ↓ ModelGraph (currently a no-op marker; structural decomp is roadmap)
quantize_graph(graph, config)
   ↓ ModelGraph with _quantized populated
validate_quality(graph, config, baseline)
   ↓ dict with activation_mse, max_layer_mse, cosine_similarity, delta_pct
```

Order matters: sparsity runs *before* quantization so zeros propagate
through; decomposition would also run before quantization (when wired).

## Hardware estimator

`worker/estimator/` produces area, throughput, cost, and energy estimates
for the configured hardware target. The numbers come from per-node cell
library data in `targets.py` (sky130, GF22FDX, TSMC 28/16/7, Lattice
ECP5/CrossLink-NX, Xilinx Artix-7/Kria, TinyTapeout, chipIgnite).

The same numbers are mirrored in `apps/web/lib/estimator.ts` for the
client-side preview. **Keep these in sync**. When you refine a cell
library entry, change both files.

## Loaders

`worker/loaders/huggingface.py` defines `load_huggingface_model(id)`
which returns `(nn.Module, metadata)`. Wired into
`pipeline/parse.py:parse_model` via the `{"type": "huggingface", "id": ...}`
dispatch.

The transformers dependency is in the `hosted` extra (heavy install).
The dispatcher raises a clear error if the extra is missing.

To enable:
```bash
cd apps/worker
uv sync --extra hosted
```

## Modal deployment

`worker/modal_app.py` defines a Modal app with two entry points:

- `run_job(job)` — single-call function. The API spawns one container
  per job. Per-call billing.
- `queue_pump()` — long-running function that BLPOPs Redis. Always
  running.

Use one or the other, not both. See [deployment.md](deployment.md) for
secret setup and `modal deploy` instructions.

## When a kernel changes

The bit-exactness contract is the most important invariant in the
worker. The relevant tests:

- `tests/test_quantize_multi.py` — 4 precisions × generated reference =
  bit-exact
- `tests/test_end_to_end.py` — 32-trial random check on full pipeline

Change `kernels/quantize.py` or `kernels/pack.py` or
`rtl/templates/linear_layer.v.j2` or `rtl/templates/reference.py.j2` —
run those tests in the same commit. They take 5 seconds.

## Hot spots

If you're going to spend time anywhere, it'll be one of these:

1. `worker/kernels/quantize.py` — adding new precisions (FP4, FP8 E4M3,
   MXFP4, etc.)
2. `worker/rtl/templates/linear_layer.v.j2` — new multiplier strategies
3. `worker/pipeline/parse.py` — adding HF attention auto-detection
4. `worker/estimator/targets.py` (+ `apps/web/lib/estimator.ts`) —
   refining cell library numbers
5. `worker/kernels/layers.py` — new layer kinds (Mamba, MoE, conv)

If you're touching anything else, double-check that you're not solving
a problem that should be solved in one of those four places instead.
