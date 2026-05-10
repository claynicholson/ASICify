# RTL Template Reference

Every Verilog file ASICify emits is rendered from a Jinja2 template under
`apps/worker/worker/rtl/templates/`. This doc is the reference for each
template: what it generates, what variables it expects, what the output
contract is, and how to extend it.

The renderer is `apps/worker/worker/rtl/generator.py:render_package`. It
builds a context dictionary, then loops through each layer kind and
renders the appropriate template.

## Output package layout

A rendered package looks like:

```
build/<name>/
├── README.md             auto-generated user-facing readme
├── top.v                 top-level pipeline wrapper
├── weights.vh            ALL hardwired constants (W, scales, biases, gamma, beta, embeddings, softmax LUT)
├── modules/
│   ├── layer_<sym>.v     one file per linear / layernorm / embedding layer
│   └── ...
├── softmax.v             shared softmax submodule (used by attention blocks)
├── kv_cache.v            shared KV cache submodule (used by attention blocks)
├── reference.py          bit-exact NumPy reference
├── tb_top.py             cocotb testbench
├── Makefile              targets: sim | lint | synth-yosys | synth-vivado | clean
└── synthesis/
    ├── yosys.tcl
    ├── nextpnr.sh
    └── vivado.tcl
```

## Generator context (the dict passed to every template)

Defined in `render_package`:

| Key | Type | Purpose |
|-----|------|---------|
| `graph` | `ModelGraph` | The post-quantization graph |
| `config` | `CompressionConfig` | User intent (quantization, sparsity, decomp) |
| `multiplier` | `str` | Default multiplier strategy from `config.quantization` |
| `linear_views` | `list[dict]` | One entry per linear layer with all template vars |
| `layernorm_views` | `list[dict]` | One entry per LayerNorm layer |
| `embedding_views` | `list[dict]` | One entry per Embedding layer |
| `pipeline` | `list[dict]` | Linear views in declaration order (used by `top.v`) |
| `weights_json` | `str` | JSON-serialized weight dict for `reference.py` |
| `softmax_lut_decl` | `str` | A `localparam` declaration for the global softmax LUT |
| `random_input_example` | `str` | A small JSON literal for the README quickstart |

Each `*_view` dict has at minimum `name`, `symbol`, `module_name`,
`weights_decl`. Linear views also have `quantization`, `in_features`,
`out_features`, `has_bias`. LayerNorm views have `dim`. Embedding views
have `vocab_size`, `embedding_dim`.

### `_safe_symbol(name)` — Verilog identifier hygiene

Module paths from PyTorch can have dots (`block.0.fc1`). Verilog needs
identifiers without dots. The helper replaces every non-alphanumeric
char with `_` and prepends `_` if the result starts with a digit. So
`block.0.fc1` → `block_0_fc1`. The symbol gets used in module names,
weight constant names, and reference.py keys, so it must be the same
everywhere.

## Template-by-template reference

### `linear_layer.v.j2` — the heart of the compiler

**Generates**: `modules/layer_<symbol>.v`. One per linear layer.

**Inputs**: `layer_view`, plus the standard context. The renderer
overrides `multiplier` per-layer based on `layer_view.quantization`,
because LayerNorm/Embedding stay at INT8 even when the user requests
binary/ternary.

**What it does**: streams int8 inputs in one cycle at a time, MACs
into a per-output-channel int32 accumulator, then streams the
rescaled int32 outputs.

**The polymorphism point**: the `unpack_w(o, i)` SystemVerilog
function is rendered with one of four bodies based on the multiplier
strategy:

```
{% if multiplier == 'booth' %}
    unpack_w = W_<sym>[o][i];                    // INT8: direct
{% elif multiplier == 'csd_shift_add' %}
    byte_val = W_<sym>[o][i >> 1];                // INT4: nibble unpack
    nibble = (i[0] == 0) ? byte_val[3:0] : byte_val[7:4];
    unpack_w = {{4{nibble[3]}}, nibble };         // sign-extend 4 -> 8
{% elif multiplier == 'sign_flip_mux' %}
    byte_val = W_<sym>[o][i >> 2];                // ternary: 2-bit code
    code = byte_val >> (2 * i[1:0]);
    unpack_w = (code == 00) ? 0 : (code == 01) ? +1 : -1;
{% elif multiplier == 'xnor_popcount' %}
    byte_val = W_<sym>[o][i >> 3];                // binary: 1 bit
    bit_val = byte_val[i[2:0]];
    unpack_w = bit_val ? +1 : -1;
{% endif %}
```

Then the rest of the always block is identical for all precisions:
`acc[o] += in_data * unpack_w(o, in_idx)` while accumulating, then
`product = acc[out_idx] * SCALE_Q31[out_idx]; out = product >>> 31`
while streaming.

**Adding a new precision** = adding a new `{% elif %}` arm to
`unpack_w` plus a new pack format and a new `_multiplier_strategy`
mapping.

### `weights.vh.j2` — the constant database

**Generates**: `weights.vh` (top-level, not under `modules/`).

**What it contains**: every numeric constant in the design,
concatenated:

1. Per-linear-layer: `W_<sym>`, `SCALE_Q31_<sym>`, `BIAS_Q_<sym>`
   (formatted by `pack_layer`).
2. Per-layernorm: `GAMMA_Q15_<sym>`, `BETA_Q15_<sym>`, `EPS_Q15_<sym>`
   (formatted by `pack_layernorm`).
3. Per-embedding: `EMBED_<sym>` (formatted by `pack_embedding`).
4. Global: `SOFTMAX_LUT[0:255]`.

**Why one big file**: Verilog `\`include` is a textual substitution.
Putting all constants in one place keeps the include directive in each
module file simple (`\`include "weights.vh"`).

**Why at top level (not `weights/weights.vh`)**: simulators look in the
include search path; the simplest path is a sibling to `top.v`.

### `top.v.j2` — pipeline wrapper

**Generates**: `top.v`.

**What it does**: declares the top-level module, instantiates one
`layer_<sym>` per linear stage in pipeline order, and wires them
together. Inter-stage signal width changes from int32 (output of
layer N) to int8 (input of layer N+1) via an inline saturating clip:

```verilog
assign s1_in_data =
    (s0_out_data >  32'sd127) ?  8'sd127 :
    (s0_out_data < -32'sd128) ? -8'sd128 :
    s0_out_data[7:0];
```

The first stage's input and the last stage's output are exposed as
the top-level ports (int8 in, int32 out).

**Limitation today**: only chains linear layers. LayerNorm and
Embedding are emitted as standalone modules but not auto-wired into
the top-level pipeline. The user wires them by hand for now (or
modifies this template). Adding auto-wiring needs a clearer
`graph.layers` ordering with non-linear stages tagged.

### `layernorm.v.j2` — LayerNorm with int sqrt

**Generates**: `modules/layer_<symbol>.v` for each LayerNorm.

**Three-state machine**:
1. **Collecting**: stream `DIM` int8 values into a buffer.
2. **Normalizing**: compute mean, variance, `inv_std_q15`, then apply
   `(x - mean) * inv_std * gamma + beta` in place.
3. **Streaming**: stream out the `DIM` int8 results.

**`inv_sqrt_q15` function**: uses `$itor`, `$sqrt`, `$rtoi` for
simulation. Verilator supports these. For real synthesis, replace with
a small Newton-Raphson LUT (a 256-entry sqrt table is sufficient at
int8 input scale). This is a tracked future item.

### `embedding.v.j2` — token lookup

**Generates**: `modules/layer_<symbol>.v` for each Embedding.

**What it does**: takes a token id, addresses into `EMBED_<sym>`,
streams out the `DIM` int8 components of that row over `DIM` cycles.

**Hardware mapping**: synthesis tools turn the 2D constant array into
a real ROM. On FPGA this becomes BRAM. On ASIC it becomes mask ROM.
This is the single largest area consumer for token-input models — the
storage scales as `vocab × dim × 8 bits`.

### `softmax.v.j2` — LUT-based softmax

**Generates**: `softmax.v` (always emitted, used by attention).

**Four-state machine**:
1. **Collect**: stream `SEQ_LEN` int32 logits into a buffer.
2. **Max-and-exp**: find max, compute `d = logit - max`, look up
   `SOFTMAX_LUT[d + 255]`.
3. **Normalize**: divide each `exp_q15` by `sum_exp` to get Q15
   weights.
4. **Stream**: emit `SEQ_LEN` int32 weights.

The LUT covers `d ∈ [-255, 0]` because `exp(-256) ≈ 10⁻¹¹¹`, well
below Q15 resolution.

**For ASIC**: the divide step (`(exp_q15 << 15) / sum`) needs special
handling. Yosys synthesizes it as a generic divider, which is large.
The conventional alternative: replace with `1 / sum * exp_q15` using
a reciprocal LUT plus one multiply. Tracked future item.

### `kv_cache.v.j2` — addressable BRAM

**Generates**: `kv_cache.v` (always emitted).

**What it does**: simple synchronous-write, registered-read BRAM with
`DEPTH` entries of `HIDDEN * DATA_WIDTH` bits. One read port, one
write port. Dual-ported BRAM is a future optimization for parallel
attention heads.

Synthesis tools recognize this pattern and infer real BRAM blocks
(both Yosys/nextpnr for ECP5 and Vivado for Xilinx).

### `reference.py.j2` — bit-exact NumPy reference

**Generates**: `reference.py` (top-level).

**What it does**: defines a `WEIGHTS` dict (filled by
`weights_json` from the generator) and a `PIPELINE` list. The
`reference_forward(x_int8)` function:

```python
for stage in PIPELINE:
    sym = stage["symbol"]
    w_int8    = WEIGHTS[f"W_{sym}"]
    scale_q31 = WEIGHTS[f"SCALE_Q31_{sym}"]
    bias_q    = WEIGHTS[f"BIAS_Q_{sym}"]
    y_int32 = ((w_int8 @ x_int64 + bias_q) * scale_q31) >> 31
    if not last: x = clip(y_int32, -128, 127).astype(int8)
return y_int32
```

**Critical**: this *exactly* mirrors the SystemVerilog. The
bit-exactness test in `tests/test_end_to_end.py` runs 32 random
inputs through this and the in-process kernel and asserts equality.

### `tb_top.py.j2` — cocotb testbench

**Generates**: `tb_top.py` (top-level, picked up by `make sim`).

**What it does**: drives 8 random int8 vectors through the RTL using
cocotb's clock + valid/ready handshake, collects the int32 outputs,
asserts they equal `reference.reference_forward(inputs)`.

**Requires** verilator + cocotb on the host. The Makefile checks for
both and prints a helpful install hint if missing.

**Twos-complement helper**: cocotb returns 32-bit signal values as
unsigned ints. The `_twos_complement(v, 32)` helper converts back to
signed int32 for the comparison.

### `Makefile.j2` — build targets

**Generates**: `Makefile` (top-level).

Targets:

| Target | What it does | Requires |
|--------|--------------|----------|
| `sim` | cocotb + Verilator simulation | verilator, cocotb, numpy |
| `lint` | Verilator lint-only (fast CI) | verilator |
| `synth-yosys` | ECP5 synthesis + place-and-route | yosys, nextpnr-ecp5 |
| `synth-vivado` | Xilinx synthesis | vivado |
| `clean` | Remove build artifacts | — |

Each tool-requiring target checks for the binary first and exits with
a friendly install hint if missing.

### `synthesis/yosys.tcl.j2`, `nextpnr.sh.j2`, `vivado.tcl.j2`

Standard scripts for the open-source ECP5 flow and the Xilinx flow.
The Yosys script reads all Verilog sources, hierarchies on `top`, then
calls `synth_ecp5 -json`. nextpnr places and routes. Vivado does the
equivalent for Xilinx parts.

### `README.md.j2` — user-facing package README

**Generates**: `README.md` in the package root. Documents the package
contents, the numerical conventions, and the build commands.

## Render order

```
render_package(graph, config):
    multiplier = strategy_for(config.quantization)
    quantized  = graph.metadata["_quantized"]

    # Build per-kind views
    for layer in graph.layers:
        if linear:    linear_views.append({...})
        elif layernorm: layernorm_views.append({...})
        elif embedding: embedding_views.append({...})

    # Universal context
    ctx = {graph, config, multiplier, ..., weights_json, softmax_lut_decl}

    # Top-level files
    files["top.v"]      = top.v.j2.render(**ctx)
    files["weights.vh"] = weights.vh.j2.render(**ctx)
    files["README.md"]  = README.md.j2.render(**ctx)

    # Per-layer files (linear with per-layer multiplier override)
    for v in linear_views:
        per_layer_ctx = {**ctx, "multiplier": strategy_for(v.quantization)}
        files["modules/layer_{sym}.v"] = linear_layer.v.j2.render(layer_view=v, **per_layer_ctx)

    for v in layernorm_views:  files[...] = layernorm.v.j2.render(layer_view=v, **ctx)
    for v in embedding_views:  files[...] = embedding.v.j2.render(layer_view=v, **ctx)

    # Always-emitted shared modules
    files["softmax.v"]   = softmax.v.j2.render(**ctx)
    files["kv_cache.v"]  = kv_cache.v.j2.render(**ctx)

    # Verification + build
    files["reference.py"] = reference.py.j2.render(**ctx)
    files["tb_top.py"]    = tb_top.py.j2.render(**ctx)
    files["Makefile"]     = Makefile.j2.render(**ctx)
    files["synthesis/*"]  = ...

    return zip(files)
```

## Conventions across all templates

- `\`default_nettype none` at the top of every Verilog file,
  `\`default_nettype wire` at the bottom. Catches accidentally-
  unconnected signals at synthesis time.
- Active-low reset everywhere: `rst_n`, synchronous deassertion.
- Standard handshake on every module's input and output:
  `valid` / `ready` pair plus `data`. The producer asserts `valid`,
  the consumer asserts `ready`, the transfer happens when both are
  high on a clock edge.
- Module names match file names. `module foo (...)` lives in
  `modules/foo.v`. Generator helper `_safe_symbol` turns dotted
  PyTorch paths into legal Verilog identifiers.
- Constants come from `weights.vh` via `\`include "weights.vh"`.

## Adding a new layer kind end-to-end

Suppose you want to add `Conv2d` support. The recipe:

1. **Parser** (`worker/pipeline/parse.py`): add a `_classify_module`
   branch for `nn.Conv2d`. Stash the module ref under
   `_modules[name]`.
2. **Quantizer** (`worker/kernels/layers.py` or new
   `kernels/conv.py`): write `quantize_conv2d(module) -> QuantizedConv`.
   Pick a representation: probably per-output-channel INT8 with a 4D
   weight tensor reshaped to (out_ch, in_ch * kh * kw).
3. **Pack** (`worker/kernels/pack.py`): `pack_conv2d(symbol, qc) -> str`.
4. **Pipeline** (`worker/pipeline/quantize.py`): dispatch on
   `layer.kind == "conv2d"`.
5. **Template**: write `worker/rtl/templates/conv2d.v.j2`. Probably a
   sliding-window state machine that reuses the same MAC pattern as
   `linear_layer.v.j2`.
6. **Generator**: add a `conv2d_views` list, append the right view
   dict, render the template. Update `weights.vh.j2` to include
   `conv2d_views`.
7. **Reference**: extend `reference.py.j2` to handle `conv2d`
   stages. Same fixed-point math.
8. **Tests**: add `tests/test_conv.py` with the same shape as
   `test_quantize_multi.py` for bit-exactness.

This pattern (classify → quantize → pack → template → reference → test)
is the recipe for any new layer kind.
