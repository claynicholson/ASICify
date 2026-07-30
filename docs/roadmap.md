# Roadmap

What's shipped vs what's next, updated as work lands. If something on this
page contradicts something elsewhere in the repo, this page is the source
of truth.

## Shipped and verified

The compiler core works end-to-end across four quantization precisions. The
bit-exactness contract (`kernel forward == generated reference.py == RTL`)
is locked in by 90 pytest tests in
[`apps/worker/tests/`](../apps/worker/tests/): the fast ones run in ~7
seconds on CPU; the cocotb/Verilator simulation test runs in CI on every
push.

### Compiler

- [x] Real `torch.fx`-style module walk in `worker/pipeline/parse.py` for
      arbitrary stacks of `nn.Linear`, `nn.LayerNorm`, `nn.Embedding`,
      `nn.MultiheadAttention`, plus standard activations
- [x] Real INT8 symmetric per-output-channel quantization
- [x] Real INT4 in [-7, 7] with per-row scale (CSD shift-add multiplier)
- [x] Real ternary {-1, 0, +1} (TWN-style threshold + per-row scale)
- [x] Real binary {-1, +1} with per-row alpha
- [x] Real FP16 (separate float-math path; weights stored as fp16, RTL uses
      behavioral float multiplier with $bitstoshortreal)
- [x] Multi-precision multiplier strategies all wired through real kernels:
      `xnor_popcount`, `sign_flip_mux`, `csd_shift_add`, `booth`, `fp16_lut`
- [x] Real magnitude pruning: 2:4, 4:8, block-sparse 16x16, unstructured
      (operates on float weights before quantization; zeros propagate)
- [x] Binary-precision sparsity skip (binary can't represent zero)
- [x] Real LayerNorm quantization (Q15 gamma/beta as int32)
- [x] Real Embedding quantization (per-column INT8 ROM table)
- [x] Integer softmax kernel with LUT-based exp + reference attention
- [x] **HF attention block auto-detection** in the parser. Models with
      `q_proj/k_proj/v_proj/o_proj` (llama, mistral, gemma) or
      `query/key/value/output.dense` (BERT-style) naming get collapsed
      into a single `QuantizedAttention` and rendered as one
      `attention_<sym>.v` module that wires the four projections + the
      shared softmax + KV cache.
- [x] **Low-rank SVD decomposition** that actually factors weight
      tensors and inserts two synthetic Linear layers (B then A) into
      the graph. Pipeline metadata records reconstruction error per
      decomposed layer.
- [x] **Monarch and butterfly decomposition.** Real blockwise rank-1
      SVD projection onto the Monarch class (Dao et al. 2022), factors
      materialized as two dense Linears with structured zeros and the
      permutation folded into row ordering. Butterfly is the
      power-of-two-blocks flavor
      (two factors, one intermediate requantization, instead of log n
      butterfly stages), so quantize, pack, and RTL render are untouched.
      `--num-blocks` on the CLI; auto ≈ √min-dim
      snapped to a divisor of gcd(in, out). Estimators use real nonzero
      counts instead of the old hardcoded 0.35x guess.
- [x] HuggingFace model loader (in `hosted` extra): module / checkpoint /
      huggingface dispatch
- [x] Real activation-MSE validation: dequantize, run, compare per-layer
      activations + end-to-end cosine similarity, ordering across precisions
      verified by tests

### RTL generation

- [x] Synthesizable Verilog `linear_layer.v` with one `unpack_w` arm per
      multiplier strategy
- [x] `top.v` with multi-stage pipeline + inter-stage int8 saturating clip
- [x] `weights.vh` with all hardwired constants (W, scale, bias, gamma,
      beta, embeddings, softmax LUT)
- [x] `layernorm.v` with Verilator-friendly int sqrt approximation
- [x] `embedding.v` with ROM lookup
- [x] `softmax.v` with LUT-based exp + max-subtract + normalize
- [x] `kv_cache.v` as a real BRAM
- [x] Bit-exact NumPy reference (`reference.py`) generated alongside the RTL
- [x] Cocotb testbench (`tb_top.py`) with 8-trial random vector check
- [x] `Makefile` with `sim` / `lint` / `synth-yosys` / `synth-vivado` targets
      that detect missing tools and print install hints
- [x] **Cocotb simulation in the test loop.** `tests/test_simulation.py`
      generates a package and runs its `make sim` (Verilator + cocotb)
      as a real pytest: skipped locally without the tools, required in
      CI via `ASICIFY_REQUIRE_SIM=1` so a broken tool install can't go
      green. The bit-exactness chain is now
      `kernel ↔ reference.py ↔ RTL`, machine-checked on every push.

### Tooling

- [x] `asicify demo` and `asicify estimate` CLI subcommands
- [x] Hardware estimator with cell-library data for sky130, GF22FDX, TSMC
      28/16/7, ECP5, CrossLink-NX, Artix-7, Kria, TinyTapeout, chipIgnite
- [x] Production Docker image for the web app
- [x] FastAPI Dockerfile + Fly.io config (ready to deploy)
- [x] Modal worker app definition (ready to deploy)
- [x] GitHub Actions CI: pytest + Verilator lint + Yosys synth-check + web
      build, all on every push

### Web

- [x] Next.js landing, playground, markdown docs site, blog stub, about
- [x] Live in-browser hardware estimator (sub-millisecond per slider move)
- [x] PDF report generation via `@react-pdf/renderer` at `/api/report`
- [x] WebGPU in-browser inference preview using `@huggingface/transformers`
      with WASM fallback (DistilGPT-2 by default, ~80MB cached after first
      load)

## Partial: wired but not exhaustive

- [~] **Attention KV cache wiring**. The `kv_cache.v` and `softmax.v`
      modules are emitted in every package, and the
      `attention_block.v.j2` wires them in for single-token attention.
      Multi-token attention with a real KV-cache rotation is the next
      template iteration.

## Not yet started

- [ ] **Public deployment of the API and worker.** The Dockerfiles and
      Modal app are committed; no live URLs exist yet. Needs hosting
      account credentials.
- [ ] **End-to-end synthesis verification on real ECP5 hardware**. CI
      runs `verilator --lint-only` and a Yosys synth-check, but no
      bitstream is flashed to a board.
- [ ] **Real perplexity validation against language data**. The
      validator works against random Gaussian inputs; for token-input
      models, you need a dataset. The hook is `validate_with_data`.
- [ ] **Hardware-aware fine-tuning loop**. Short retraining run with
      quantization simulated in the loop, straight-through estimator
      for non-differentiable ops. Modal-backed.
- [ ] **TinyTapeout submission integration**. We can target sky130, but
      packaging for an actual TinyTapeout tile (with their pinout and
      area limits) needs a separate template variant.
- [ ] **Stripe billing**. Pricing page was deliberately removed when we
      reframed as an open-source project.

## Where to focus next

In priority order:

1. **Multi-token attention with real KV-cache rotation.** The last
   `[~]` item above. `kv_cache.v` is a real BRAM and single-token
   attention works; the template iteration that rotates the cache
   across a token sequence unlocks honest autoregressive decode.
2. **First real ECP5 bitstream.** Pick a small model (DistilBERT
   tiny), compile to int8, run yosys + nextpnr-ecp5 + ecppack, flash
   it to a $35 board, and publish the build log.
3. **Real perplexity validation.** The validator runs against random
   Gaussian inputs today; wire `validate_with_data` to a real token
   dataset (wikitext-2 is the obvious start) so compression reports
   carry perplexity deltas, not just cosine similarity.
4. **Public API deployment.** The Dockerfiles and Modal app are
   committed and the pipeline is verified end-to-end; deploying the
   hosted version is now unblocked.

## Long-tail

Real but lower priority until the above lands:

### Compression quality
- **Static activation calibration**: feed a small calibration set
  through the float model and derive per-layer activation ranges,
  replacing the weight-only assumptions in quantization + validation
- **Per-group quantization (GPTQ-style)**: group-wise scales within a
  row, plus error-compensating rounding order; better int4 accuracy on
  transformer weights
- **Mixed-precision assignment**: search precision per layer against
  an area budget (the estimator is already fast enough to be the inner
  loop of that search)
- **Hardware-aware fine-tuning**: the existing "Not yet started" item;
  a short straight-through-estimator retraining run, Modal-backed

### Hardware pipeline
- **CI area regression tracking**: record Yosys `stat` cell counts for
  the demo package on every push; fail on unexplained growth the same
  way perf suites fail on latency regressions
- **TinyTapeout tile template variant**: sky130 already works; add
  their pinout and area-limit packaging
- **Toggle-rate power estimation**: Verilator can dump per-net
  activity from the cocotb runs in CI; fold real toggle rates into the
  power model instead of the static estimate

### Reach
- WebGPU inference for *any* HF model (currently fixed to DistilGPT-2)
- Diffusion / Mamba primitive support
- Speculative decoding hardware partitioning
- Self-hosted enterprise option with custom PDKs
- Multi-model deployment with shared backbone
