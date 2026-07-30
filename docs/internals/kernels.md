# Kernels

The `worker/kernels/` package is where actual tensor work happens. The
pipeline modules in `worker/pipeline/` are pure orchestration: they walk a
`ModelGraph`, decide what to do, and call into kernels for the math.

This doc is the reference for every kernel: what it does, the data
contracts, the bit-exactness invariants, and the extension points.

## Module map

```
apps/worker/worker/kernels/
├── __init__.py        Empty marker
├── quantize.py        INT8 / INT4 / ternary / binary / FP16 quantization + bit-exact forward
├── pack.py            Tensor -> SystemVerilog `localparam` literal strings (5 formats)
├── sparsity.py        2:4, 4:8, block-16, unstructured magnitude pruning
├── decompose.py       Low-rank SVD truncation + Monarch/butterfly blockwise projection
├── layers.py          LayerNorm, Embedding, QuantizedAttention dataclass
└── attention.py       Integer softmax with LUT-based exp + reference attention
```

Everything in this package is **pure**. No I/O, no global state, no Redis,
no environment variable reads. Every function is a pure tensor → tensor
mapping. This is what lets pytest run all 80 tests in 4.6 seconds.

## The bit-exactness contract

The most important invariant in the compiler: the kernel
forward pass and the generated `reference.py` must produce identical
`int32` output on identical input. The Verilog is verified against the
reference, and the reference is verified against the kernel, so
transitively the kernel pins the silicon.

Every kernel that has a `*_forward` function exists to define exactly
what the RTL is supposed to do, in Python. If you change a kernel
forward, you must regenerate the matching template arm and rerun
`tests/test_quantize_multi.py` and `tests/test_end_to_end.py`. Both
suites run in under 5 seconds.

## `quantize.py`: INT8 / INT4 / ternary / binary / FP16

### `QuantizedLinear` dataclass

The carrier. Stores the int8 weights in **canonical signed form** for
the integer precisions. INT4 weights live in `int8` tensors with
values clipped to `[-7, 7]`. Ternary lives in `int8` tensors with values
in `{-1, 0, 1}`. Binary in `{-1, +1}`.

For FP16 the same field carries `float16` values directly. The dispatcher
checks `q.quantization == "fp16"` and routes to a separate float-math
forward.

```python
@dataclass
class QuantizedLinear:
    quantization: str           # "int8" | "int4" | "ternary" | "binary" | "fp16"
    weight_int8: torch.Tensor   # canonical signed form (dtype int8 for ints, float16 for fp16)
    scale: torch.Tensor         # float32, per-output-channel (sentinel 1.0 for fp16)
    bias: torch.Tensor | None   # float32, per-output-channel
    in_features: int
    out_features: int
```

Why one dataclass for all precisions? Because the *forward arithmetic*
is identical; the only thing that changes is how the int8 tensor gets
**packed** into Verilog literals. The pack module handles that.

### Quantizer functions

| Function | Range | Scale rule | Recon error (Gaussian) |
|----------|-------|-----------|-----------------------|
| `quantize_linear_int8(W, b)`     | [-128, 127] | per-row max-abs / 127 | ~0.3% |
| `quantize_linear_int4(W, b)`     | [-7, 7]     | per-row max-abs / 7   | ~5%   |
| `quantize_linear_ternary(W, b)`  | {-1, 0, 1}  | per-row mean(|kept|) | ~30% |
| `quantize_linear_binary(W, b)`   | {-1, 1}     | per-row mean(|w|)    | ~45% |

Plus a dispatcher: `quantize_linear(W, b, precision)`.

The ternary threshold uses the classic `0.7 * mean(|W|)` heuristic
(Li & Liu 2016). It minimizes L2 reconstruction error for Gaussian
weights. Don't change it without a good reason.

### `linear_int8_forward(x, q)`: the bit-exact reference

```python
def linear_int8_forward(x, q):
    bias_q   = round(bias / scale).clamp(int32)         # pre-rescale int32
    scale_q31 = round(scale * 2^31).clamp(uint32)        # Q0.31

    acc      = W @ x + bias_q                             # int32 MAC
    product  = acc * scale_q31                            # int64
    return (product >> 31).to(int32)                      # arithmetic shift
```

Every multiplication uses the canonical int8 weight regardless of
precision. The Verilog template generates the same arithmetic; only
the `unpack_w(o, i)` function differs per precision.

**Critical detail**: `>> 31` is an arithmetic right shift on signed
int64. PyTorch's default `>>` does this for signed dtypes. The
SystemVerilog `>>>` operator on signed types matches.

### Adding a new precision

1. Add `quantize_linear_<name>(W, b)` → `QuantizedLinear` (set
   `quantization="<name>"`).
2. Extend `quantize_linear()` dispatcher.
3. Add `<name>_array_to_sv(name, t)` to `pack.py`.
4. Extend `pack_layer()` to dispatch.
5. Add a multiplier strategy to
   `worker/rtl/generator.py:_multiplier_strategy`.
6. Add an `{% elif multiplier == '<strategy>' %}` arm to
   `worker/rtl/templates/linear_layer.v.j2:unpack_w` that decodes the
   packed format back to a signed int8 value.
7. The kernel forward and reference both keep working without changes
   because they read from `weight_int8` directly.
8. Add tests in `tests/test_quantize_multi.py` parametrize lists.

The full FP4 pattern is the most likely next addition; it would store
weights as 4-bit floats with shared exponents and need a small LUT in
the multiplier arm.

## `pack.py`: Tensor → SystemVerilog literals

Each precision packs differently to match what the multiplier expects:

| Precision | Bytes per row | Format |
|-----------|---------------|--------|
| INT8      | `in_features` | `'{8'sd-12, ...}'` (signed decimal per byte) |
| INT4      | `(in_features + 1) / 2` | `'{8'h<lo:hi>, ...}'` (two nibbles per byte, low first) |
| Ternary   | `(in_features + 3) / 4` | `'{8'h<...>, ...}'` (4 codes/byte: 00=0, 01=+1, 11=-1) |
| Binary    | `(in_features + 7) / 8` | `'{8'h<...>, ...}'` (1 bit/weight, 1=+1, 0=-1, LSB first) |

Plus three constant tables, all precision-independent:

| Table | Format | Used in RTL as |
|-------|--------|----------------|
| `W_<sym>`         | weight literal (above) | inner-loop operand |
| `SCALE_Q31_<sym>` | `'{32'd<n>, ...}'` (Q0.31 unsigned) | rescale multiplier |
| `BIAS_Q_<sym>`    | `'{32'sd<n>, ...}'` (signed int32) | accumulator initial value |

`bias_q = round(bias_float / scale)`: the bias gets converted *into
accumulator units* so it can be added before the rescale shift. This
saves a separate adder in hardware.

`scale_q31 = round(scale_float * 2^31).clamp(0, 2^31-1)`: Q0.31
unsigned. Range covers typical per-row scales (10⁻⁴ to 10⁻²) with
plenty of resolution.

Functions:

- `pack_layer(symbol, q: QuantizedLinear) -> str`: emits all three
  declarations. **Use this**, not the per-precision functions.
- `int8_array_to_sv`, `int4_array_to_sv`, `ternary_array_to_sv`,
  `binary_array_to_sv`: per-precision weight emitters.
- `pack_layernorm(symbol, qln) -> str`: emits gamma_q15 / beta_q15 /
  eps_q15 for a `QuantizedLayerNorm`.
- `pack_embedding(symbol, qe) -> str`: emits the int8 lookup table.

## `sparsity.py`: magnitude pruning

Runs **before** quantization (in `worker/pipeline/sparsity.py`). The
pruned weights become exact zeros in the float tensor, which then
quantize to zero and stay zero in the packed Verilog constants. The
synthesis tool removes the dead multipliers.

| Function | Pattern | Notes |
|----------|---------|-------|
| `apply_2_to_4(W)`               | every group of 4 keeps the 2 largest by \|w\| | NVIDIA Ampere-style |
| `apply_4_to_8(W)`               | every group of 8 keeps the 4 largest | |
| `apply_block_sparse(W, ratio, block=16)` | drop entire NxN tiles by mean magnitude | Tile-friendly |
| `apply_unstructured(W, ratio)`  | per-row top-k by magnitude | |
| `apply_sparsity(W, type, ratio)` | dispatcher | |

Plus `sparsity_ratio(W) -> float` for inspection.

**Binary precision skips sparsity** because binary weights can't
represent zero. The pipeline-level wrapper in
`worker/pipeline/sparsity.py` checks `config.quantization == "binary"`
and short-circuits. There's a test for this
(`test_sparsity.test_binary_skips_sparsity`).

## `decompose.py`: low-rank SVD truncation

Replaces a `Linear(in, out)` with two smaller Linears: `Linear_B(in, r)`
followed by `Linear_A(r, out)`. The pipeline does this *before*
quantization, so the two factors get quantized like any other Linear.

```python
@dataclass
class LowRankFactors:
    a: torch.Tensor     # (out, rank)
    b: torch.Tensor     # (rank, in)
    bias: torch.Tensor | None
    rank: int
    in_features: int
    out_features: int
```

`low_rank_decompose(W, b, rank)` does an SVD truncation, splitting the
energy as `A = U sqrt(S)` and `B = sqrt(S) V^T`. Even split keeps
downstream quantization well-conditioned.

`parameter_savings(in, out, rank)` returns the fraction of parameters
dropped. The pipeline wrapper in `worker/pipeline/decompose.py` skips
layers where the decomposition would not actually save parameters (e.g.
small layers with high rank).

The pipeline replaces the original layer name with `<name>.b` and
`<name>.a` and stashes per-layer reconstruction error in
`graph.metadata["_decomp_info"]`. The downstream pack and template
machinery treat the two factors as ordinary Linear layers.

### Monarch and butterfly

`monarch_decompose(W, b, n_blocks)` projects W onto the Monarch class
(Dao et al. 2022): view W as a `k x k` grid of blocks and replace each
block with its best rank-1 approximation (independent per-block SVDs,
which is the optimal projection onto that class). The same `sqrt(S)`
energy split keeps both factors quantization-friendly.

The two factors are *materialized as dense matrices with structured
zeros* (density `1/k` each) and the fixed Monarch permutation is folded
into the row ordering of the B factor. That means no permutation module
in RTL: the pipeline inserts plain `<name>.b` / `<name>.a` Linear layers
exactly like low-rank, and zeros quantize exactly to zero downstream.
`param_count` on the synthetic layers counts nonzeros (`k*in` and
`k*out`), so area estimates stay honest.

Butterfly is realized as the Monarch projection with a power-of-two
block count: the product of the two halves of a radix-2 butterfly chain
lands in the Monarch class, and collapsing to two factors costs only a
single intermediate int8 requantization instead of one per butterfly
stage.

`auto_n_blocks(in, out, requested, power_of_two)` picks `k`: target is
the request or `round(sqrt(min dim))`, snapped down to a divisor of
`gcd(in, out)`; returns `None` (skip the layer) when no `k >= 2` fits or
the decomposition would not save parameters.

## `layers.py`: LayerNorm and Embedding

### `QuantizedLayerNorm`

```python
@dataclass
class QuantizedLayerNorm:
    gamma_q15: torch.Tensor  # int32, Q15 (so values up to ~65k)
    beta_q15: torch.Tensor   # int32, Q15
    eps_q15: int             # eps * 2^15
    dim: int
```

Why int32 for gamma when typical values are ~1.0? Because `1.0` in Q15
needs `2^15 = 32768`, which is *just* outside int16 signed range. We
use int32 for headroom. Real synthesis tools fold the upper bits of
near-1.0 constants away.

`quantize_layernorm(nn.LayerNorm) -> QuantizedLayerNorm` is the
quantizer. `layernorm_int_forward(x_int8, qln) -> int8` is the
bit-exact reference (used in `tests/test_layers.py`).

### `QuantizedEmbedding`

```python
@dataclass
class QuantizedEmbedding:
    table_int8: torch.Tensor  # (vocab, dim), int8
    scale: torch.Tensor       # (dim,), float32, per-column scale
    vocab_size: int
    embedding_dim: int
```

Per-column INT8: each embedding dimension gets its own scale, mirroring
the per-output-channel rule for Linear layers. Reconstruction error is
~0.5% on Gaussian-init embeddings.

`quantize_embedding(nn.Embedding) -> QuantizedEmbedding`.
`embedding_int_forward(token_ids, qe) -> int8 (seq_len, dim)`.

### `QuantizedAttention`

```python
@dataclass
class QuantizedAttention:
    q_proj: QuantizedLinear
    k_proj: QuantizedLinear
    v_proj: QuantizedLinear
    o_proj: QuantizedLinear
    embed_dim: int
    num_heads: int
    head_dim: int
    softmax_lut: torch.Tensor  # int16, length 256
```

This is a structural composite. The four projections are independent
QuantizedLinear records that render as four `layer_<sym>.v` files. The
softmax LUT is a global constant emitted once into `weights.vh`.

The current parser (in `worker/pipeline/parse.py`) does **not**
auto-detect HF attention blocks and group them into a
`QuantizedAttention`. That is the next-largest piece of work. For now
the projections render as separate Linear layers, which is correct but
loses the structural relationship.

## `attention.py`: softmax and reference attention

### `build_softmax_lut(input_bits=8, output_q=15) -> int32 tensor`

Pre-computed LUT mapping `d ∈ [-(2^input_bits - 1), 0]` → `exp(d)` in
Q15 unsigned. The Verilog `softmax.v` module reads this same table.
Default size 256.

### `softmax_int(logits_int32) -> int32 (Q15 unsigned)`

The bit-exact integer softmax:

```python
max_val = logits.max()
d = (logits - max_val).clamp(min=-(N-1), max=0)
exp_q15 = LUT[d + (N-1)]
sum = exp_q15.sum()
weights_q15 = (exp_q15 << 15) / sum
```

Returns Q15 unsigned weights summing to ~`2^15` (truncating int divide
leaves a small remainder; tests allow ±16 slack on a 16-element vector).

### `attention_int_forward(q, k, v) -> int32`

Single-head scaled dot-product attention in integer form. The scale is
implemented as a right shift by `ceil(log2(head_dim) / 2)`, which
approximates dividing by `sqrt(head_dim)` and is exactly what the RTL
does (right-shifts are free in hardware; real division isn't).

Used in `tests/test_attention.py` to verify the building blocks before
the full structural attention block is wired in the parser.

## How the pipeline calls the kernels

End-to-end trace for the demo path:

```
worker.cli.cmd_demo
  ├── parse_module(TinyMLP)                           [pipeline/parse.py]
  │     stashes _weights, _biases, _modules, _root_module
  │
  ├── apply_sparsity(graph, config)                   [pipeline/sparsity.py]
  │     calls kernels.sparsity.apply_sparsity per linear layer
  │     replaces _weights with pruned floats
  │
  ├── quantize_graph(graph, config)                   [pipeline/quantize.py]
  │     for linear:    kernels.quantize.quantize_linear  -> QuantizedLinear
  │     for layernorm: kernels.layers.quantize_layernorm -> QuantizedLayerNorm
  │     for embedding: kernels.layers.quantize_embedding -> QuantizedEmbedding
  │     stashes _quantized
  │
  ├── render_to_directory(graph, config, out)         [rtl/generator.py]
  │     calls kernels.pack.pack_layer / pack_layernorm / pack_embedding
  │     calls kernels.attention.build_softmax_lut
  │     renders Jinja2 templates with the packed strings
  │
  ├── reference.reference_forward(x_int8)             [generated reference.py]
  │     loads WEIGHTS dict from the same packed numbers
  │     applies the same int math as kernels.quantize.linear_int8_forward
  │
  └── validate_quality(graph, config, baseline)       [pipeline/validate.py]
        runs original model + dequantized clone on random Gaussian input
        computes per-layer activation MSE and end-to-end cosine sim
```

The `_root_module`, `_quantized`, etc. are stashed under
`graph.metadata` with leading underscores. They're internal to the
pipeline and *not* serialized when the graph crosses a process
boundary (that would be the case if the worker reads jobs from Redis;
in that case the worker re-runs `parse_module` from a model id).

## Testing layout

| Test file | What it covers |
|-----------|----------------|
| `tests/test_quantize.py`        | INT8 quantizer + forward |
| `tests/test_pack.py`            | All four packing formats |
| `tests/test_quantize_multi.py`  | Bit-exactness across all four precisions × generated reference.py |
| `tests/test_sparsity.py`        | All four sparsity patterns + pipeline integration + binary skip |
| `tests/test_layers.py`          | LayerNorm, Embedding kernels + render to package |
| `tests/test_attention.py`       | Softmax LUT, softmax_int, attention_int_forward, Q/K/V/O renders |
| `tests/test_validate.py`        | Activation-MSE, ordering across precisions, top1, fallback |
| `tests/test_loader.py`          | parse_model dispatch (module/checkpoint/HF stub), error messages |
| `tests/test_end_to_end.py`      | Full TinyMLP → RTL → reference 32-trial bit-exactness |

Run the suite:

```
cd apps/worker
python -m uv run pytest tests/ -v
```

80 tests, ~5 seconds on CPU.
