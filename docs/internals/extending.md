# Extending ASICify

How to add the things people will want to add. Each section is a recipe with
file-by-file instructions and a sanity check.

## Add a hardware target

Goal: surface `My Target` in the playground dropdown, get area / cost
estimates for it on both client and server, and have it appear in API
responses.

### 1. TypeScript types — `packages/shared/src/types.ts`

Add the new id to the `TargetId` union:

```ts
export type TargetId =
  | "sky130"
  | …
  | "my_target";
```

### 2. Shared target catalog — `packages/shared/src/targets.ts`

Add a `TargetSpec`:

```ts
my_target: {
  id: "my_target",
  display_name: "My Target",
  kind: "asic",            // or "fpga" or "shuttle"
  process_node_nm: 65,
  vendor: "Acme",
  description: "One-line summary for the dropdown tooltip.",
},
```

### 3. Client-side estimator — `apps/web/lib/estimator.ts`

Add a row to `NODE_PARAMS`. For ASIC nodes:

```ts
my_target: {
  rom_bit_um2: 0.40,
  sram_bit_um2: 1.20,
  mul_int8_um2: 720,
  fmax_mhz: 800,
  energy_int8_pj: 0.45,
  wafer_cost: 3500,
  wafer_diameter: 300,
  nre: 800_000,
  defect_density: 0.18,
},
```

For FPGAs, add to `fpgaUnitCost(target)` and ensure
`is_fpga`-style branch in `quickEstimate` treats it correctly. (FPGAs have
a flat unit cost and no NRE in this model.)

### 4. API target catalog — `apps/api/app/data/targets.py`

Add a matching `TargetSpec(...)` entry to the `TARGETS` list, and a
`COST_MODELS` entry with the same fields as the worker.

### 5. Pydantic types — `apps/api/app/schemas.py`

Extend the `TargetId` `Literal` union with `"my_target"`.

### 6. Worker estimator — `apps/worker/worker/estimator/targets.py`

Add a `NodeParams(...)` row to `ASIC_NODES` (or `FpgaParams` to `FPGAS`).
**These numbers must match the client estimator** — see the sync rule in
[codebase.md](../codebase.md#the-estimator-lives-in-two-places--on-purpose).

### 7. Worker cost model — `apps/worker/worker/estimator/cost.py`

If the target is a shuttle (TinyTapeout-style fixed-fee), add a branch to
`estimate_cost`. ASIC nodes flow through `_asic_cost` automatically once
they're in `ASIC_NODES`. FPGAs flow through `FPGAS` lookup.

### 8. Sanity check

```bash
# Frontend type-check picks up the new TargetId
pnpm --filter @asicify/web typecheck

# Playground dropdown should show "My Target"
pnpm --filter @asicify/web dev

# API returns it
curl http://localhost:8000/api/targets | jq '.[] | select(.id == "my_target")'

# Worker can estimate against it
cd apps/worker
uv run asicify estimate gpt2 --target my_target
```

Sources for cell-library numbers: foundry data sheets, ASPLOS / ISSCC
papers, RDL synthesis runs you've personally done. Cite the source in the
commit message — future maintainers will need to evaluate whether to update.

## Add a quantization mode

Goal: support a new precision (e.g. FP4 E2M1) end-to-end.

### 1. Shared types

In `packages/shared/src/types.ts` and `apps/api/app/schemas.py`, extend
the `Quantization` union with `"fp4"`.

In `apps/worker/worker/types.py`, do the same on the worker dataclass
typedef.

### 2. UI option

In `apps/web/components/playground/config-panel.tsx`, add to
`QUANT_OPTIONS`:

```ts
{ value: "fp4", label: "FP4", bits: "4 bit (E2M1)" }
```

The grid will accommodate; widen the parent if you exceed 5.

### 3. Estimator constants — both copies

Client (`apps/web/lib/estimator.ts`):

```ts
const BITS_PER_WEIGHT = { …, fp4: 4 };
const MUL_AREA_SCALE = { …, fp4: 0.25 };  // small ROM-LUT per multiply
const QUALITY_PENALTY = { …, fp4: 1.06 };  // empirical
```

Worker (`apps/worker/worker/estimator/area.py`):

```python
MUL_SCALE: dict[str, float] = {…, "fp4": 0.25}
BITS_PER_WEIGHT: dict[str, float] = {…, "fp4": 4}
```

And in `apps/worker/worker/pipeline/quantize.py`:

```python
PENALTY = {…, "fp4": 1.06}
```

### 4. Multiplier strategy — `apps/worker/worker/rtl/generator.py`

Add to `_multiplier_strategy`:

```python
return {…, "fp4": "fp4_lut"}[quantization]
```

### 5. Verilog template — `linear_layer.v.j2`

Add an `{% elif multiplier == 'fp4_lut' %}` branch in the inner-loop body
of `linear_layer.v.j2`. The body should reference a per-weight LUT (small
ROM emitted by the synthesizer from the constant table in `weights.vh`).

### 6. Test

```bash
cd apps/worker
uv run asicify compile gpt2 --quantization fp4 --target tsmc28
unzip -p ./build/gpt2.zip top.v | head -20
```

Verify the generated Verilog references `fp4_lut`-flavored constants and
that estimator output looks plausible.

## Add an RTL primitive

Goal: support a new layer kind, e.g. `mamba_block`.

### 1. Layer kind type — `apps/worker/worker/types.py`

Extend `LayerKind`:

```python
LayerKind = Literal[
    "linear", "conv2d", "attention", "ffn", "layernorm",
    "embedding", "mamba_block", "other"
]
```

### 2. Parser — `apps/worker/worker/pipeline/parse.py`

When real `torch.fx` parsing is wired, add a classifier branch that
recognizes Mamba's `selective_scan` operation as `mamba_block`. For now,
extend `synthesize_transformer` if you want a synthesized graph to include
Mamba blocks for testing.

### 3. Template — `apps/worker/worker/rtl/templates/mamba_block.v.j2`

Create the Verilog. Follow the conventions of existing templates:
- `\`default_nettype none` at top, `wire` at bottom.
- Standard handshake: `in_valid`, `in_ready`, `in_data`, `out_*`.
- `\`include "weights/weights.vh"` for hardwired constants.
- `clk` and `rst_n` always; active-low reset.

### 4. Generator — `apps/worker/worker/rtl/generator.py`

In `render_package`, extend the layer dispatch:

```python
elif layer.kind == "mamba_block":
    content = env.get_template("mamba_block.v.j2").render(layer=layer, **ctx)
```

### 5. Top-level wiring — `apps/worker/worker/rtl/templates/top.v.j2`

The `{% for layer in graph.layers %}` block already handles any layer kind
that emitted a module; verify the generated `u_<i>` instance compiles. If
Mamba needs additional ports (e.g. state passed across timesteps), extend
the top template's layer-instance block.

### 6. Estimator weight

Add Mamba-specific area math if needed. The current estimator treats all
linear-ish layers identically; if Mamba's selective scan is materially
different, branch on `layer.kind` in
`apps/worker/worker/estimator/area.py:_effective_param_count`.

### 7. Test the package

```bash
uv run asicify compile some-mamba-model --target ecp5
unzip -d /tmp/m ./build/some-mamba-model.zip
cd /tmp/m
make sim                       # cocotb + Verilator should still pass
verilator --lint-only top.v modules/*.v
```

## Add a new pipeline stage

Goal: insert a new stage between, say, sparsity and decomposition (perhaps a
weight-clustering step).

### 1. Stage module — `apps/worker/worker/pipeline/cluster.py`

```python
from dataclasses import replace
from worker.types import CompressionConfig, ModelGraph

def apply_clustering(graph: ModelGraph, config: CompressionConfig) -> ModelGraph:
    # Pure function: input graph, output new graph.
    # No I/O, no global state, no Redis. Don't import 'app.*'.
    ...
    return replace(graph, metadata={**graph.metadata, "clustered": True})
```

### 2. Wire into orchestrator — `apps/worker/worker/pipeline/orchestrator.py`

Add the call in `run_compression_job` between sparsity and decomposition:

```python
graph = await _stage(emit, "clustering", apply_clustering, graph, config)
```

The `_stage` helper handles the start/complete events automatically.

### 3. Optional: extend `CompressionConfig`

If clustering needs config knobs (number of clusters, etc.), add a new
field:

- `packages/shared/src/types.ts` — TypeScript `CompressionConfig`
- `apps/api/app/schemas.py` — Pydantic `CompressionConfig`
- `apps/worker/worker/types.py` — dataclass `CompressionConfig`

Plus a UI control in `apps/web/components/playground/config-panel.tsx`.

### 4. Test

Stage purity makes this easy:

```python
def test_apply_clustering_reduces_unique_weights():
    g = synthesize_transformer("test", 1_000_000)
    cfg = CompressionConfig(...)
    out = apply_clustering(g, cfg)
    assert out.metadata["clustered"]
```

## Add a CLI subcommand

Goal: e.g. `asicify report <project>` to download the PDF report.

### 1. Subparser — `apps/worker/worker/cli.py`

```python
report_parser = sub.add_parser("report", help="…")
report_parser.add_argument("project_id")
```

### 2. Handler

```python
elif args.cmd == "report":
    # Hits the API like a regular client
    ...
```

The CLI is allowed to call the hosted API; that's different from worker
pipeline code, which must remain self-contained.

### 3. Wire into the script entry

Already handled via `pyproject.toml`'s `[project.scripts]` block:

```toml
asicify = "worker.cli:main"
```

The new subcommand auto-registers via the `argparse` subparser pattern.

## Add a database table

Goal: e.g. add `comments` for inline notes on projects.

### 1. ORM — `apps/api/app/models.py`

```python
class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", …))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", …))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

### 2. Migration

```bash
cd apps/api
uv run alembic revision --autogenerate -m "add comments table"
# Review the generated file in alembic/versions/, then:
uv run alembic upgrade head
```

### 3. Pydantic schemas — `apps/api/app/schemas.py`

```python
class CommentCreate(BaseModel):
    body: str

class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    user_id: UUID
    body: str
    created_at: datetime
```

### 4. Router — `apps/api/app/routers/comments.py`

Mirror the pattern in `routers/projects.py`. Add to `app/main.py`:

```python
app.include_router(comments.router, prefix="/api/projects", tags=["comments"])
```

### 5. Optional: shared TS types

If the frontend will display comments, add to `packages/shared/src/types.ts`
and update `apps/web/lib/api.ts` with new methods.

## Add a model to the catalog

Goal: support a new HuggingFace model id in the dropdown.

You must update **both** copies:

1. `apps/api/app/data/catalog.py` — `CATALOG` list
2. `apps/web/lib/catalog.ts` — `MODEL_CATALOG` array

Required fields: `id`, `hf_id`, `display_name`, `family`, `task`,
`parameters`, `recommended_compression`. The recommended compression
should be a config that's known to validate well — start with INT8 +
no sparsity if you haven't tested aggressive settings.

If the model has unusual structure (Mamba, MoE, encoder-decoder), add a
note in `metadata` and consider whether the parser needs a new branch.

## Anti-patterns to avoid

These are mistakes I've watched people make. Don't do them.

### Cross-package Python imports

```python
# In apps/worker/...
from app.models import Project   # NO — that's apps/api
```

The worker is supposed to run standalone via the CLI. If it depends on
`apps/api`, that breaks.

### Bypassing the orchestrator

```python
# Worker pipeline code calling the emit function directly
await emit({"event": "log", "message": "doing stuff"})  # NO
```

Use `_stage(emit, name, fn, *args)`. The orchestrator owns the event
shapes; ad-hoc emits will break consumers.

### Global mutable state in stages

```python
# In pipeline/quantize.py
QUANT_CACHE = {}  # NO

def quantize_graph(graph, config):
    if (graph.name, config) in QUANT_CACHE: ...  # NO
```

Caching belongs in the orchestrator, keyed by content hash. Stage purity
is what makes the system testable.

### Hardcoding the API base URL

```ts
fetch("https://api.asicify.com/api/projects")  // NO
```

Use `lib/api.ts` which respects `NEXT_PUBLIC_API_BASE_URL`. Hardcoded URLs
break local dev.

### Shipping the worker estimator constants to the client

Don't generate `apps/web/lib/estimator.ts`'s constants from
`apps/worker/...` at runtime. The client must remain a static bundle.

### Touching `weights.vh` without updating the multiplier branch

If you add a precision, you also add a Verilog branch. If you only change
the data layout in `weights.vh`, the existing multiplier branches break
silently. Always test with `verilator --lint-only` after changes.
