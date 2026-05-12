# Testing

Everything verifiable runs in pytest. As of writing, **80 tests in 4.6
seconds** on CPU. The test suite is the canonical source of truth for
"does the compiler still work" — CI runs it on every push.

## Running

From `apps/worker`:

```bash
python -m uv run pytest tests/ -v        # full suite, verbose
python -m uv run pytest tests/test_end_to_end.py -v   # one file
python -m uv run pytest -k bit_exact    # one test name pattern
```

The web app's typecheck runs separately:

```bash
pnpm --filter @asicify/web typecheck
pnpm --filter @asicify/web build
```

(no Vitest yet for the web client; the live estimator is pure math
that the bit-exactness test in the worker indirectly covers).

## File map

```
apps/worker/tests/
├── __init__.py
├── test_quantize.py             INT8 quantizer + bit-exact forward (6 tests)
├── test_pack.py                 All five packing formats (5 tests)
├── test_quantize_multi.py       Bit-exactness across INT8/INT4/ternary/binary × generated reference.py (15 tests)
├── test_fp16.py                 FP16 kernel + dispatch + reference bit-exactness (5 tests)
├── test_sparsity.py             All four sparsity patterns + pipeline integration + binary skip (9 tests)
├── test_decompose.py            Low-rank SVD + Monarch placeholder + pipeline integration (8 tests)
├── test_layers.py               LayerNorm, Embedding kernels + render to package (5 tests)
├── test_attention.py            Softmax LUT, softmax_int, attention_int_forward, Q/K/V/O renders (7 tests)
├── test_attention_autodetect.py HF-style attention parser + structural attention rendering (5 tests)
├── test_validate.py             Activation-MSE, ordering across precisions, top1, fallback (4 tests)
├── test_loader.py               parse_model dispatch (module/checkpoint/HF stub), error messages (6 tests)
└── test_end_to_end.py           Full TinyMLP → RTL → reference 32-trial bit-exactness (5 tests)
```

## What each test guarantees

### `test_quantize.py`

- `quantize_linear_int8` shapes, dtypes, and per-row max-abs scaling.
- Per-channel INT8 reconstruction error stays under 1% on Gaussian
  weights.
- Zero rows are handled without divide-by-zero.
- The bit-exact forward `linear_int8_forward` matches a hand-computed
  version of the same fixed-point arithmetic (proves the kernel
  formula is what we say it is).

### `test_pack.py`

- INT8 weight literals contain the exact integer values from the
  source tensor, formatted as signed decimals.
- `int8_array_to_sv` rejects non-int8 dtypes (catches accidental
  fp32 inputs).
- `scale_q31` values fit in unsigned 31 bits, with a known fixed point
  for `scale=0.5`.
- `bias_q_array_to_sv` handles `bias=None` gracefully.
- `pack_layer` emits all three required arrays (W, SCALE, BIAS) plus
  a header comment with shape info.

### `test_quantize_multi.py` (the central guarantee)

Parametrized across `["int8", "int4", "ternary", "binary"]`:

- The kernel's `weight_int8` is in the right value range for each
  precision.
- The generated `reference.py` produces *identical* output to
  `linear_int8_forward` across 8 random int8 input vectors per
  precision.
- The `weights.vh` file contains the right format marker for each
  precision (`8'sd...` for INT8, `8'h...` for the bit-packed forms).

If you're touching anything in `kernels/quantize.py`, `kernels/pack.py`,
`rtl/templates/linear_layer.v.j2`, or `rtl/templates/reference.py.j2`,
this is the test that catches drift.

### `test_sparsity.py`

- `apply_2_to_4` keeps exactly 2 of every 4 weights, and they're the
  largest by magnitude.
- `apply_4_to_8` keeps exactly 4 of every 8.
- `apply_unstructured` drops the bottom-N% per row.
- `apply_block_sparse` drops entire 16x16 tiles by mean magnitude.
- The dispatcher passes `sparsity="none"` through unchanged.
- Pipeline integration: after `apply_sparsity` then `quantize_graph`,
  the int8 weights have zeros wherever the float was zero.
- Binary precision skips sparsity (binary can't represent zero).

### `test_layers.py`

- `quantize_layernorm` produces int32 gamma/beta in Q15 with
  reconstruction error < 2×10⁻⁴ for normal-init weights.
- `layernorm_int_forward` returns int8 of the right shape with finite
  values.
- `quantize_embedding` produces per-column scales with < 2% recovery
  error.
- `embedding_int_forward` returns rows of the right shape and dtype.
- The full pipeline emits `modules/layer_<sym>.v` files for embed,
  ln, and fc; `weights.vh` contains all the matching constants.

### `test_attention.py`

- The softmax LUT has the right shape and contains exp(0)=1.0 at the
  last index.
- `softmax_int` on uniform logits yields uniform Q15 weights.
- Normalized weights sum to ~2^15 (Q15 representation of 1.0).
- A dominant logit concentrates almost all the mass.
- `attention_int_forward` returns the right shape and dtype.
- When one key matches the query, the corresponding value dominates
  the output.
- Q/K/V/O linear projections render as separate `layer_*.v` files in
  the package.

### `test_validate.py`

- INT8 validation reports activation_mse < 0.01 and cosine_similarity
  > 0.99 (preserves the model).
- Activation MSE strictly increases as precision drops:
  INT8 < INT4 < ternary < binary.
- `validate_with_data` with `metric="top1"` works for classifiers.
- When `_root_module` isn't set on the graph, validation falls back to
  the analytical penalty.

### `test_loader.py`

- `parse_model` dispatches `{"type": "module"}` correctly.
- Back-compat `{"module": ...}` without `"type"` still works.
- Unknown types raise a clear ValueError.
- `{"type": "checkpoint", "path": ...}` loads a saved nn.Module.
- The HF loader reports availability correctly and raises a helpful
  RuntimeError when the `hosted` extra isn't installed.

### `test_end_to_end.py`

The full integration:

- The package contains all 11 expected files (top.v, weights.vh,
  modules/, reference.py, tb_top.py, Makefile, synthesis/*).
- `weights.vh` contains real int8 numeric literals (catches the
  regression where templates were emitting all zeros).
- 32 random input vectors all produce identical int32 output between
  the in-process kernel and the generated `reference.py`.
- `reference_forward` rejects inputs of the wrong length.
- Per-layer reconstruction error stays under 2%.

## Adding a new test

Match the existing patterns:

```python
import torch
from torch import nn
from worker.kernels.<your_module> import <function>

def test_function_name_describes_what_it_proves():
    torch.manual_seed(0)  # always seed for reproducibility
    # arrange
    w = torch.randn(8, 4)
    # act
    result = function(w)
    # assert: be specific about what equality means
    assert result.shape == (8, 4)
    assert result.dtype == torch.int8
    assert (result.abs().max() <= 127).all()
```

Conventions:

- Always `torch.manual_seed(0)` (or any fixed seed).
- Test names start with `test_` and read like English: `test_2_to_4_keeps_largest_magnitudes`.
- Use `pytest.parametrize` to run the same logic across all
  precisions (see `test_quantize_multi.py`).
- For end-to-end tests, use `tmp_path` fixture for the rendered
  package — pytest cleans it up.
- Don't test internals of internals; test contracts. If you find
  yourself patching private functions, the test is too tight.

### Bit-exactness tests

When you add a new precision or a new layer kind, the central
guarantee is this loop:

```python
@pytest.mark.parametrize("quantization", [..., "<new>"])
def test_reference_matches_kernel(quantization, tmp_path):
    torch.manual_seed(<unique>)
    model = _OneLayer(in_f=16, out_f=8, bias=True)
    graph = parse_module(model, name="t", task="classification")
    config = _config(quantization)
    graph = quantize_graph(graph, config)
    out_dir = tmp_path / "rtl"
    render_to_directory(graph, config, out_dir)

    reference = _load_reference(out_dir)
    quant = graph.metadata["_quantized"]["fc"]

    for trial in range(8):
        x = torch.randint(-50, 50, (16,), dtype=torch.int8)
        expected = linear_int8_forward(x, quant).numpy()
        actual = np.asarray(reference.reference_forward(x.tolist()), dtype=np.int32)
        assert np.array_equal(actual, expected)
```

Replace the parametrize value, add the matching `_<precision>_array_to_sv`
in `pack.py`, add the `{% elif %}` arm in `linear_layer.v.j2`, and the
test passes.

## Manual end-to-end verification

The `asicify demo` CLI doubles as an integration smoke test:

```bash
cd apps/worker
python -m uv run asicify demo --output ./build/demo
```

It renders a TinyMLP, runs the cross-check between the in-process
kernel and the generated `reference.py`, and prints a hardware estimate.
Useful for spot-checking after a refactor.

## CI integration

`.github/workflows/ci.yml` runs three jobs in parallel on every push:

| Job | Runs | What |
|-----|------|------|
| `worker-tests` | ubuntu-latest | `uv sync --extra dev && uv run pytest -q` |
| `rtl-lint-and-synth` | ubuntu-latest | Generate the demo package + verilator lint + yosys synth-check |
| `web-build` | ubuntu-latest | pnpm install + typecheck + build + Docker build |

The `rtl-lint-and-synth` job catches regressions where the templates
emit syntactically-valid Python but no-longer-synthesizable Verilog.
Verilator's lint is fast; yosys's `read_verilog -sv ... ; hierarchy ;
proc ; flatten ; stat` exercises the full elaboration without writing
a netlist.

## Coverage gaps (known)

Tests we don't have yet that we should:

- **Verilator simulation in pytest**. Right now the bit-exact test is
  Python kernel ↔ Python reference. Adding `pytest-cocotb` or
  shelling out to `make sim` from a test would cover Verilog-level
  correctness too.
- **HF loader against a real small model**. The smoke test in
  `test_loader.py` only covers dispatch, not actual model loading.
  When the `hosted` extra is installed in CI, we should add a test
  that loads `prajjwal1/bert-tiny` (4M params, downloads in seconds)
  and runs it through `parse_module`.
- **Web client tests**. The live estimator math in
  `apps/web/lib/estimator.ts` should have Vitest unit tests.
- **PDF report rendering**. The `/api/report` route should have a
  smoke test that requests a PDF and asserts the response starts
  with `%PDF`.

These are tracked but not blocking — the core compiler invariants are
covered.
