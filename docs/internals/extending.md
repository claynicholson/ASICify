# Extending ASICify

How to add the things people will want to add. Each recipe is concrete:
file paths, the sequence of edits, the test that proves it works.

## Recipe index

- [Add a quantization precision](#add-a-quantization-precision)
- [Add a sparsity pattern](#add-a-sparsity-pattern)
- [Add a hardware target](#add-a-hardware-target)
- [Add a layer kind (Conv2d, Mamba, MoE, etc.)](#add-a-layer-kind)
- [Extend HF attention detection](#extend-hf-attention-detection)
- [Add a CLI subcommand](#add-a-cli-subcommand)
- [Add a database table](#add-a-database-table)
- [Add a model to the catalog](#add-a-model-to-the-catalog)

## Add a quantization precision

Worked example: FP4 with shared exponent.

### 1. Quantization kernel: `apps/worker/worker/kernels/quantize.py`

```python
def quantize_linear_fp4(weight, bias=None):
    # FP4 E2M1: 1 sign + 2 exp + 1 mantissa, range ~[-6, 6]
    w = weight.detach().to(torch.float32)
    out_features, in_features = w.shape
    max_abs = w.abs().amax(dim=1).clamp_min(1e-12)
    scale = max_abs / 6.0
    # Round to FP4-representable values (15 grid points + zero).
    grid = torch.tensor([-6, -4, -3, -2, -1.5, -1, -0.5, 0,
                          0.5, 1, 1.5, 2, 3, 4, 6])
    normalized = w / scale.unsqueeze(1)
    # Snap each weight to nearest grid point, store the index.
    diffs = (normalized.unsqueeze(-1) - grid).abs()
    indices = diffs.argmin(dim=-1).to(torch.int8)  # 0..14
    # Map indices to the canonical "as-int8" form for storage.
    quantized = (indices - 7).to(torch.int8)  # signed in [-7, 7]
    return QuantizedLinear(
        quantization="fp4",
        weight_int8=quantized,
        scale=scale.to(torch.float32),
        bias=...,
        ...
    )
```

Then add to the dispatcher:

```python
def quantize_linear(weight, bias, quantization):
    ...
    if quantization == "fp4":
        return quantize_linear_fp4(weight, bias)
    ...
```

### 2. Pack: `apps/worker/worker/kernels/pack.py`

```python
def fp4_array_to_sv(name, tensor):
    """Pack 15-value FP4 indices two-per-byte."""
    # ... same shape as int4_array_to_sv but encoding indices 0..14.
```

Wire into `pack_layer`:

```python
elif q.quantization == "fp4":
    weights_sv = fp4_array_to_sv(f"W_{symbol}", q.weight_int8)
```

### 3. Multiplier strategy: `apps/worker/worker/rtl/generator.py`

```python
def _multiplier_strategy(quantization):
    return {
        ...
        "fp4": "fp4_lut",
    }[quantization]
```

### 4. Verilog template: `apps/worker/worker/rtl/templates/linear_layer.v.j2`

Add an `unpack_w` arm:

```jinja
{% elif multiplier == 'fp4_lut' %}
    byte_val = W_<sym>[o][i >> 1];
    nibble = (i[0] == 0) ? byte_val[3:0] : byte_val[7:4];
    // 16-entry LUT mapping FP4 index -> int8 representation.
    case (nibble)
        4'd0: unpack_w = -8'sd6;
        4'd1: unpack_w = -8'sd4;
        ...
        4'd15: unpack_w = 8'sd6;
    endcase
{% endif %}
```

The kernel forward already works because we store FP4 weights in
canonical signed form (the stored int8 *is* the dequantized value
times some scale; the linear math is the same). The pack/unpack is
the only thing that changes per precision.

### 5. Test: `apps/worker/tests/test_quantize_multi.py`

Add `"fp4"` to the parametrize lists:

```python
@pytest.mark.parametrize("quantization", ["int8", "int4", "ternary", "binary", "fp4"])
def test_reference_matches_kernel_for_each_precision(...)
```

Run `python -m uv run pytest tests/test_quantize_multi.py -v`; the new
precision should pass alongside the others.

### 6. UI: `apps/web/components/playground/config-panel.tsx`

Add `{ value: "fp4", label: "FP4", bits: "4 bit (E2M1)" }` to
`QUANT_OPTIONS`.

Update `apps/web/lib/estimator.ts`:

```ts
const BITS_PER_WEIGHT = { ..., fp4: 4 };
const MUL_AREA_SCALE  = { ..., fp4: 0.25 };
const QUALITY_PENALTY = { ..., fp4: 1.06 };
```

And the matching server-side estimator at
`apps/worker/worker/estimator/area.py:MUL_SCALE`.

## Add a sparsity pattern

Worked example: 1:2 (half-density structured).

### 1. Kernel: `apps/worker/worker/kernels/sparsity.py`

```python
def apply_1_to_2(weight):
    """Each consecutive pair keeps the larger by |w|."""
    out_f, in_f = weight.shape
    pad = (2 - in_f % 2) % 2
    w = torch.nn.functional.pad(weight, (0, pad))
    grouped = w.reshape(out_f, -1, 2)
    abs_w = grouped.abs()
    _, idx = abs_w.topk(1, dim=-1)
    mask = torch.zeros_like(grouped, dtype=torch.bool)
    mask.scatter_(-1, idx, True)
    out = (grouped * mask.to(grouped.dtype)).reshape(out_f, -1)
    return out[:, :in_f]
```

### 2. Dispatcher

```python
def apply_sparsity(weight, sparsity_type, ratio):
    ...
    if sparsity_type == "structured_1_2":
        return apply_1_to_2(weight)
```

### 3. Type: `packages/shared/src/types.ts`

Add `"structured_1_2"` to the `SparsityType` union (mirror in the API
schema and worker dataclass).

### 4. UI: `apps/web/components/playground/config-panel.tsx`

Add `{ value: "structured_1_2", label: "1:2 structured" }` to
`SPARSITY_OPTIONS`.

### 5. Test: `apps/worker/tests/test_sparsity.py`

Mirror the existing 2:4 tests for the new pattern.

## Add a hardware target

Worked example: TSMC 5nm.

### 1. TypeScript types: `packages/shared/src/types.ts`

Add `"tsmc5"` to `TargetId`. Add a `TargetSpec` to
`packages/shared/src/targets.ts:TARGETS`.

### 2. Client estimator: `apps/web/lib/estimator.ts`

Add a row to `NODE_PARAMS`:

```ts
tsmc5: {
  rom_bit_um2: 0.018,
  sram_bit_um2: 0.06,
  mul_int8_um2: 35,
  fmax_mhz: 2800,
  energy_int8_pj: 0.025,
  wafer_cost: 17000,
  wafer_diameter: 300,
  nre: 50_000_000,
  defect_density: 0.07,
},
```

### 3. Server estimator: `apps/worker/worker/estimator/targets.py`

Add a `NodeParams(...)` row to `ASIC_NODES` with the *same numbers*. The
two estimators must stay in sync; refining one without the other gives
a misleading playground.

### 4. API target catalog: `apps/api/app/data/targets.py`

Add a `TargetSpec(...)` entry to the `TARGETS` list.

### 5. Pydantic schema: `apps/api/app/schemas.py`

Extend the `TargetId` `Literal` union.

### 6. Sanity check

```bash
pnpm --filter @asicify/web typecheck
pnpm --filter @asicify/web dev
# /playground dropdown should show "TSMC 5nm"
curl http://localhost:8000/api/targets | jq '.[] | select(.id == "tsmc5")'
cd apps/worker
python -m uv run asicify estimate --target tsmc5
```

## Add a layer kind

Worked example: `nn.Conv2d`.

### 1. Parser: `apps/worker/worker/pipeline/parse.py`

Add to `_classify_module`:

```python
if isinstance(module, nn.Conv2d):
    info = LayerInfo(
        name=name,
        kind="conv2d",
        in_features=module.in_channels * module.kernel_size[0] * module.kernel_size[1],
        out_features=module.out_channels,
        param_count=module.weight.numel() + (module.bias.numel() if module.bias is not None else 0),
        metadata={
            "kernel_size": module.kernel_size,
            "stride": module.stride,
            "padding": module.padding,
            "has_bias": module.bias is not None,
        },
    )
    return "conv2d", info
```

### 2. Quantizer: `apps/worker/worker/kernels/conv.py` (new)

```python
def quantize_conv2d(module):
    # Reshape to (out_ch, in_ch * kh * kw) for per-output-channel quant.
    w = module.weight.detach().reshape(module.out_channels, -1)
    return quantize_linear_int8(w, module.bias)
```

### 3. Pipeline: `apps/worker/worker/pipeline/quantize.py`

Add a branch:

```python
elif layer.kind == "conv2d" and layer.name in modules:
    quantized[layer.name] = quantize_conv2d(modules[layer.name])
```

### 4. Template: `apps/worker/worker/rtl/templates/conv2d.v.j2`

The pattern is similar to `linear_layer.v.j2` but with a sliding-window
state machine that addresses the input row by row. Reuse the same
unpack_w + MAC + rescale arithmetic.

### 5. Generator: `apps/worker/worker/rtl/generator.py`

```python
conv_views = []
...
elif layer.kind == "conv2d" and isinstance(q, QuantizedConv):
    conv_views.append({...})
...
for view in conv_views:
    files[f"modules/{view['module_name']}.v"] = env.get_template("conv2d.v.j2").render(...)
```

Update `weights.vh.j2` to include `conv_views`.

### 6. Reference + test

Extend `reference.py.j2` to handle conv2d stages. Add
`tests/test_conv.py` mirroring `test_quantize_multi.py` for
bit-exactness.

The pattern for any new layer kind: **parser → quantizer → pack →
template → reference → test**.

## Extend HF attention detection

The parser already groups HF attention blocks: a parent module whose
immediate children are `q_proj/k_proj/v_proj/o_proj` (LLaMA, Mistral,
Gemma) or `query/key/value/output.dense` (BERT-style) collapses into a
single `LayerInfo(kind="attention", ...)`, quantized as a
`QuantizedAttention` and rendered as one `attention_<sym>.v` module
(from `attention_block.v.j2`) wiring the four projections plus the
shared softmax and KV cache.

To support another naming scheme:

1. Add the child-name pattern to the detection walk in
   `apps/worker/worker/pipeline/parse.py`.
2. Add a test to `tests/test_attention_autodetect.py` with a small
   module using that naming, asserting its projections collapse into a
   single `attention_*.v` file instead of four separate `layer_*.v`
   files.

## Add a CLI subcommand

```python
# apps/worker/worker/cli.py
def cmd_compile(args):
    """asicify compile <model_id> --quantization int8 --target sky130 --output ./build"""
    from worker.pipeline.parse import parse_model
    graph = parse_model({"type": "huggingface", "id": args.model_id})
    config = CompressionConfig(
        quantization=args.quantization,
        sparsity=SparsityConfig(type=args.sparsity, ratio=args.sparsity_ratio),
        decomposition=DecompositionConfig(type="none"),
    )
    graph = apply_sparsity(graph, config)
    graph = quantize_graph(graph, config)
    render_to_directory(graph, config, Path(args.output))
    return 0


def main():
    parser = argparse.ArgumentParser(prog="asicify")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ...
    compile_p = sub.add_parser("compile", help="...")
    compile_p.add_argument("model_id")
    compile_p.add_argument("--quantization", default="int8")
    compile_p.add_argument("--sparsity", default="none")
    compile_p.add_argument("--sparsity-ratio", type=float, default=0.0)
    compile_p.add_argument("--target", default="sky130")
    compile_p.add_argument("--output", default="./build")
    compile_p.set_defaults(func=cmd_compile)
```

## Add a database table

```python
# apps/api/app/models.py
class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

```bash
cd apps/api
uv run alembic revision --autogenerate -m "add comments table"
# Review the file in alembic/versions/, then:
uv run alembic upgrade head
```

Add the matching Pydantic schemas in `app/schemas.py`, the router in
`app/routers/comments.py`, and mount it in `app/main.py`.

## Add a model to the catalog

Two files, both manual today (a future codegen step would derive one
from the other):

1. **`apps/api/app/data/catalog.py`**: append a `CatalogModel(...)`.
2. **`apps/web/lib/catalog.ts`**: append a matching object to
   `MODEL_CATALOG`.

Both must have the same `id`, `hf_id`, `display_name`, `family`,
`task`, `parameters`, and `recommended_compression`. If they drift, the
playground shows one model and the API serves another. We don't have
codegen here yet because the catalog is small (under 30 models).

## Anti-patterns to avoid

These break things; don't do them.

### Cross-package Python imports

```python
# In apps/worker/...
from app.models import Project   # NO: that's apps/api
```

The worker is supposed to run standalone. If it depends on `apps/api`,
the CLI and the open-source story break.

### Diverging the kernel forward and the reference template

The bit-exactness contract holds *only* if `linear_int8_forward` and
`reference.py.j2` implement the same arithmetic. If you change one,
change the other in the same commit and run
`tests/test_quantize_multi.py`.

### Bypassing the orchestrator's `_stage` helper

```python
# Worker pipeline code
await emit({"event": "log", "message": "doing stuff"})  # NO
```

Use `_stage(emit, name, fn, *args)`. The helper owns the event shapes
that the WebSocket consumers depend on; ad-hoc emits will break the UI.

### Hardcoding the model catalog or target list in two places without syncing

The web `catalog.ts` and api `catalog.py` (and similarly the targets
list across web/api/worker) must stay aligned. Use the existing
"change all three in the same PR" discipline until codegen is wired.

### Touching `weights.vh` without updating the reference

If you change how a precision packs its weights, the kernel forward
keeps working (it reads the canonical signed form), but the generated
`reference.py` reads from the same JSON the pack module emits. Make
sure the `weights_json` in `generator.py:_build_weights_json` matches
what the templates actually produce.
