# Roadmap

Honest "what's shipped vs what's next" — updated as work lands. If something
on this page contradicts something elsewhere in the repo, this page is the
source of truth.

## Shipped and verified

The compiler core works end-to-end across four quantization precisions. The
bit-exactness contract (`kernel forward == generated reference.py`) is
locked in by 62 pytest tests in
[`apps/worker/tests/`](../apps/worker/tests/), running in ~5 seconds on CPU.

### Compiler

- [x] Real `torch.fx`-style module walk in `worker/pipeline/parse.py` for
      arbitrary stacks of `nn.Linear`, `nn.LayerNorm`, `nn.Embedding`,
      `nn.MultiheadAttention`, plus standard activations
- [x] Real INT8 symmetric per-output-channel quantization
- [x] Real INT4 in [-7, 7] with per-row scale (CSD shift-add multiplier)
- [x] Real ternary {-1, 0, +1} (TWN-style threshold + per-row scale)
- [x] Real binary {-1, +1} with per-row alpha
- [x] Multi-precision multiplier strategies all wired through real kernels:
      `xnor_popcount`, `sign_flip_mux`, `csd_shift_add`, `booth`
- [x] Real magnitude pruning: 2:4, 4:8, block-sparse 16x16, unstructured
      (operates on float weights before quantization; zeros propagate)
- [x] Binary-precision sparsity skip (binary can't represent zero)
- [x] Real LayerNorm quantization (Q15 gamma/beta as int32)
- [x] Real Embedding quantization (per-column INT8 ROM table)
- [x] Integer softmax kernel with LUT-based exp + reference attention
- [x] HuggingFace model loader (in `hosted` extra) — module / checkpoint /
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

## Partial — wired but not exhaustive

- [~] **HF attention block auto-detection in the parser**. Q/K/V/O
      projections render as separate Linear layers today, which is
      correct but loses the structural relationship. A pass that
      recognizes `XxxAttention` modules and groups their projections
      into a `QuantizedAttention` is the next-largest piece of work.
- [~] **FP16 quantization**. The dispatcher accepts `fp16` and the
      `linear_layer.v.j2` template has an arm marked `fp16_lut`, but
      the kernel currently falls back to int8 quantization for fp16.
      A real FP16 kernel needs per-multiplier ROM-LUTs.
- [~] **Decomposition**. The pipeline records the decomposition config
      but doesn't yet factor matrices. Monarch and butterfly
      factorization need both a kernel (factor float weights into
      block-diagonal A and B) and template work (replace one Linear
      with a chain of three smaller Linears).

## Not yet started

- [ ] **Public deployment of the API and worker.** The Dockerfiles and
      Modal app are committed; no live URLs exist yet. Needs hosting
      account credentials.
- [ ] **End-to-end synthesis verification on real ECP5 hardware**. CI
      runs `verilator --lint-only` and a Yosys synth-check, but no
      bitstream is flashed to a board. The first time we wire this is
      worth a blog post.
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

1. **Wire Verilator into the test loop.** The cocotb testbench is
   generated; running it from CI takes one extra job step. This
   upgrades the bit-exactness chain from `kernel ↔ reference.py` to
   `kernel ↔ reference.py ↔ RTL`.
2. **HF attention auto-detection.** Today HF transformers compile
   correctly but render as a flat list of projections. Recognizing the
   attention block as a unit unlocks the structural template and the
   KV cache wiring.
3. **First real ECP5 bitstream.** Pick a small model (DistilBERT
   tiny), compile to int8, run yosys + nextpnr-ecp5 + ecppack, flash
   to a $35 board, post a tweet with the build log. This is the
   credibility moment.
4. **Public API deployment.** Once the worker pipeline above is
   demonstrably real, deploying the hosted version becomes a story
   worth telling.

## Long-tail

Real but lower priority until the above lands:

- WebGPU inference for *any* HF model (currently fixed to DistilGPT-2)
- Diffusion / Mamba primitive support
- Speculative decoding hardware partitioning
- Self-hosted enterprise option with custom PDKs
- Multi-model deployment with shared backbone
