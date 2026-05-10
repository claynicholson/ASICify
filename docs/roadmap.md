# Roadmap

What's actually shipped, what's stubbed, what's planned. Updated as work
lands. Prefer the truth on this page over claims elsewhere in the repo.

## Shipped and verified

The compiler core works end-to-end for the INT8 + Linear-only slice. The
bit-exactness test in `apps/worker/tests/test_end_to_end.py` runs 32 random
inputs through the in-process kernel and the generated `reference.py` and
asserts identical int32 output, every commit.

- [x] Monorepo with Turborepo (web, api, worker, shared)
- [x] Next.js 15 web app with live in-browser hardware estimator
- [x] Markdown docs site rendered from `/docs/*.md`
- [x] Production Docker image for the web app
- [x] **Real `torch.fx` module walk** in `worker/pipeline/parse.py` for
      arbitrary `nn.Linear` / `nn.LayerNorm` / `nn.Embedding` stacks
- [x] **Real INT8 symmetric per-output-channel quantization** in
      `worker/kernels/quantize.py`, with `<1%` reconstruction error on
      Gaussian weights
- [x] **Real weight packing** to SystemVerilog `localparam` literals in
      `worker/kernels/pack.py` (signed 8-bit weights, Q0.31 scales,
      pre-rescale int32 biases)
- [x] **Real synthesizable Verilog** with hardwired weight constants
      and a working int32 MAC + Q0.31 rescale pipeline
- [x] **Bit-exact NumPy reference** generated alongside the RTL
- [x] **`asicify demo` CLI** that goes model → quantize → render → verify
      in one command
- [x] **Pytest suite** with 16 tests covering the kernel, the pack module,
      and the end-to-end pipeline
- [x] Hardware estimator with cell-library data for sky130, GF22FDX,
      TSMC 28/16/7, ECP5, CrossLink-NX, Artix-7, Kria, TinyTapeout,
      chipIgnite

## Partial

These are wired but only for the INT8 + Linear path. Other branches still
exist as templates / typing only.

- [~] Multi-precision multiplier strategies. Templates branch on
      `multiplier` ∈ {`xnor_popcount`, `sign_flip_mux`, `csd_shift_add`,
      `booth`, `fp16_lut`}, but only `booth` (INT8) is wired through real
      kernels. INT4 / ternary / binary fall back to int8 quants today.
- [~] Pipeline stages for sparsity and decomposition record their config
      but do not yet pack masks or factor matrices into the RTL.
- [~] Attention, LayerNorm, Embedding, and KV cache templates exist but
      the generator only renders Linear modules into the package.

## Not yet started

- [ ] Real perplexity validation against held-out data (we use
      reconstruction error today)
- [ ] HuggingFace model loader (the `hosted` extra in `apps/worker/pyproject.toml`
      includes `transformers` but the loader code isn't written)
- [ ] Modal deployment for GPU jobs
- [ ] Cocotb testbench actually exercising RTL via Verilator (the file is
      generated; running it requires Verilator on the host)
- [ ] End-to-end synthesis verification: compile a small model, run yosys
      + nextpnr, get an ECP5 bitstream, flash to an actual board
- [ ] WebGPU inference comparison (`transformers.js`) in the playground
- [ ] PDF report generation
- [ ] FastAPI backend deployed publicly (it's implemented locally; no
      hosted instance yet)

## Where to focus next

Highest leverage in priority order:

1. **HuggingFace model loader.** Wire `AutoModel.from_pretrained` →
   `parse_module`. Unlocks real models without leaving the toolchain.
2. **Verilator hookup.** The cocotb testbench template already exists.
   Add a `make sim` that actually runs and asserts on RTL output. This
   makes every commit verify the RTL matches the reference, not just
   that the reference matches the kernel.
3. **INT4 kernel.** The CSD shift-add multiplier is implemented in the
   template; we need the quantization side: GPTQ-style per-channel INT4
   plus a pack module that emits 4-bit constants. This is the precision
   most users will actually want.
4. **Attention block end-to-end.** Add Q/K/V projection parsing, the
   softmax LUT, and the output projection; wire it into a small
   transformer (DistilBERT or GPT-2 small) for a real demo.
5. **Synthesis CI.** Run yosys + nextpnr on every push, fail the build
   if any generated package fails synthesis.

## Long-tail

Real but lower priority until the above lands:

- Monarch and butterfly decompositions
- Hardware-aware fine-tuning loop
- TinyTapeout submission helpers
- Diffusion and Mamba primitives
- Speculative decoding hardware partitioning
