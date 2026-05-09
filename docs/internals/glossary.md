# Glossary

ASICify sits at the intersection of three vocabularies: ML, computer
architecture, and EDA / semiconductor manufacturing. Most contributors are
strong in one, weak in two. This glossary is the bridge.

Use it when reading the code; the other internals docs assume these
definitions.

## ML compression

**Quantization** — Replacing high-precision floats (FP32, FP16) with
lower-precision integers (INT8, INT4) or extreme formats (ternary, binary).
Trades model quality for parameter bits, multiplier complexity, and energy.

**Calibration** — A small representative dataset (128–512 samples) used to
choose quantization scales. Not training; just statistics over activations.

**Per-channel scale** — Each output channel of a linear layer gets its own
scale factor. Better quality than per-tensor; small overhead.

**Symmetric quantization** — Range is `[-α, +α]`, no zero-point. Standard
for INT8.

**GPTQ** — One-shot post-training quantization for LLMs that uses second-order
information (Hessian approximation) to minimize per-layer reconstruction
error. The standard for INT4.

**Wanda** — One-shot pruning method that combines weight magnitude with
activation norm. Works without retraining.

**SparseGPT** — One-shot pruning that solves the per-layer reconstruction
problem in closed form using inverse-Hessian approximation.

**Sparsity ratio** — Fraction of weights set to zero. 50% sparsity = half the
weights are zero.

**Structured sparsity (2:4 / 4:8)** — Every group of 4 (or 8) contiguous
weights keeps exactly 2 (or 4). NVIDIA Ampere supports this in hardware;
CPUs and ASICs benefit too because the layout is regular.

**Block-sparse** — Zero-out entire 16×16 (or N×N) blocks. Tile-friendly for
hardware accelerators.

**Magnitude pruning** — Drop the weights with smallest absolute value.
Crude but works surprisingly well at moderate sparsity.

**Knowledge distillation** — Train a smaller (or quantized) student to
mimic a larger teacher. Used as a rescue when straight quantization is too
lossy.

**Monarch matrices** — Structured matrix decomposition `W ≈ P₁ B P₂ A P₃`
with block-diagonal A and B. Reduces parameter count from `mn` to
`O((m+n)·sqrt(mn))` while staying expressive enough for many ML tasks.
Original paper: Tri Dao et al., HazyResearch.

**Butterfly factorization** — `O(log n)` factor matrices with sparse
structure. Used in fast Fourier transforms historically; rediscovered for
neural nets.

**Low-rank decomposition** — `W ≈ AB` with skinny inner dim. SVD-init,
fine-tune. Cheap and well-understood; loses expressivity at very low rank.

**Hardware-aware fine-tuning** — Short retraining run with quantization
simulated in the loop. Recovers 1–3% accuracy at the same compression
ratio. Uses straight-through estimators for gradient flow through
non-differentiable ops.

**Straight-through estimator (STE)** — Gradient-flow trick: in the forward
pass, round; in the backward pass, pretend round was identity. Lets
gradients flow through quantization.

**Perplexity (PPL)** — Standard quality metric for language models. Lower
is better. `exp(loss)` for cross-entropy. ASICify reports PPL deltas, not
absolutes.

**HellaSwag, ARC-Easy** — Common-sense reasoning benchmarks for LMs.
Sanity checks beyond raw perplexity.

## Transformer architecture

**Attention block** — Q (query), K (key), V (value) projections, scaled
dot-product, softmax, output projection. The `attention.v.j2` template
emits this.

**FFN (feed-forward network)** — Two linear layers with an activation
between. Usually `up_proj` is 4× the hidden size, `down_proj` brings it
back. Bigger param count than attention.

**Hidden size** — The model's main vector width. GPT-2 small is 768.
LLaMA-7B is 4096.

**Head / head dim** — Attention is split into `n_heads` parallel computations
of `head_dim = hidden / n_heads`. Each head looks at a different subspace.

**LayerNorm** — Normalize-then-scale-and-shift. Per-token (not per-batch).
Sensitive to quantization; we keep it at INT8 even when other layers go
ternary.

**Embedding** — Vocab→hidden lookup table. Reads one row per token.
Massive parameter count, very simple compute. Mask ROM in hardware.

**KV cache** — During autoregressive generation, K and V tensors from
previous tokens are stored in a buffer and reused. Lives in BRAM in
hardware.

**Decode step** — One token of generation. Each step reads the KV cache and
appends one row. The throughput-per-second number ASICify reports is decode
steps per second.

## Silicon / hardware

**ASIC** — Application-Specific Integrated Circuit. A custom chip designed
for one purpose. ASICify generates the design files for these.

**FPGA** — Field-Programmable Gate Array. A reconfigurable chip you flash
with a bitstream. Slower and more power-hungry than an ASIC but no NRE
cost.

**SoM (System-on-Module)** — A small board with FPGA + memory + power.
Xilinx Kria is one. Easier to deploy than a bare FPGA.

**Tape-out** — The point where you submit your final design files to the
foundry to be fabricated. The "Hello World" of ASIC engineering, and the
moment after which mistakes cost millions.

**MPW (Multi-Project Wafer)** — A shared wafer split among many small
designs to amortize cost. Your design gets a corner of someone else's
wafer. Slow turn (months), cheap (~$10K).

**Shuttle** — Industry term for an MPW program. TinyTapeout and Efabless's
chipIgnite are two.

**TinyTapeout** — Matt Venn's $300/tile shuttle on SkyWater 130. Designed
for hobbyists and education. Tiny designs only.

**chipIgnite** — Efabless's shuttle on SkyWater 130, ~$10K. Larger designs
than TinyTapeout, still on the open PDK.

**PDK (Process Design Kit)** — The library of cells, models, and rules a
foundry gives designers. SkyWater's is open-source; TSMC's are NDA-locked.

**NRE (Non-Recurring Engineering)** — One-time cost: mask set, design tools,
tape-out fees. Amortizes over volume. Why high-volume parts get cheap.

**Reticle** — The largest contiguous area you can pattern in one
photolithography step. Limits the maximum die size (~858 mm² at modern
nodes).

**Standard cell** — A pre-designed Boolean gate (NAND2, NOR2, flip-flop,
etc.) used as a building block. Cell library = the foundry's catalog.

**Mask ROM** — Read-only memory whose contents are fixed by the photomasks.
Smaller than SRAM. ASICify uses mask ROM for hardwired weights.

**SRAM** — Static random-access memory. 6 transistors per bit; fast,
volatile, expensive in area. Used for KV cache and activation buffers.

**BRAM** — Block RAM. The SRAM blocks built into FPGAs.

**Foundry node** — The process technology generation. "28nm" historically
referred to a feature size; today it's a marketing label that correlates
with density. We model: SkyWater 130, GF22FDX, TSMC 28/16/7.

**FinFET** — Transistor structure used at 16nm and below. Higher density,
better leakage than planar.

**FD-SOI** — Fully-Depleted Silicon-On-Insulator. Alternative to FinFET,
good for low-power. GF22FDX uses this.

**Yield** — Fraction of dies on a wafer that work. Murphy's model relates
yield to area × defect density.

**Defect density** — Number of fatal defects per cm² of wafer. Lower at
mature nodes. Foundry-specific.

**Murphy's yield model** — `yield = ((1 - exp(-A·D)) / (A·D))²` where A is
die area in cm² and D is defects per cm². The standard cost-model yield
curve.

**Dies-per-wafer** — How many copies of your chip fit on one wafer. Wafer
area / die area, with edge waste accounted.

**Bare die** — The unpackaged chip. Adding package + test = $2-3.

**Reticle limit** — Max die size for a single exposure (~858 mm² modern).
Stitch designs cross this with multiple reticles.

## Multipliers and arithmetic

**MAC (Multiply-Accumulate)** — One multiply + one add. The unit of work
in any neural network. Throughput is measured in MACs per second.

**Booth multiplier** — Standard signed multiplication algorithm. ~10 LUTs
per INT8 MAC.

**XNOR + popcount** — Binary multiplication. XNOR = `==` for bits. Sum the
agreements. ~1 LUT per binary MAC. The reason binary networks are so
hardware-friendly.

**Sign-flip mux** — Ternary multiplication. Output = +x, 0, or -x based on
weight. ~3 LUTs per ternary MAC.

**CSD (Canonical Signed Digit)** — Number representation that allows
negative digits. Lets you express any small integer with very few non-zero
digits (often 1 or 2). For INT4 weights, multiplication becomes ≤ 2
shift-add operations.

**LUT (Look-Up Table)** — Both an FPGA primitive (small truth table) and a
generic hardware idiom (a ROM that maps input to output). Multiplier
strategies sometimes use LUTs to materialize precomputed products.

**Pipeline depth** — Number of register stages between input and output.
More depth = higher clock rate but more latency.

**Throughput** — Outputs per second. For pipelined designs, this is
clock rate / cycles-per-output.

**f_max** — The highest clock frequency at which the design meets timing.
Process and design dependent.

## EDA tools

**RTL (Register-Transfer Level)** — Hardware description abstraction at the
level of "registers and combinational logic between them". Verilog and
SystemVerilog are RTL languages.

**Verilog / SystemVerilog** — Hardware description languages. SystemVerilog
adds typed bit-vectors, packed structs, and verification features. ASICify
emits a SystemVerilog-ish dialect.

**Synthesis** — Compiling RTL into a netlist of standard cells. The thing
that turns "always @(posedge clk)" into actual flip-flops.

**Yosys** — Open-source synthesis tool. Lattice-class FPGA flow. ASICify's
default for ECP5.

**nextpnr** — Open-source place-and-route. Pairs with Yosys for ECP5.

**Vivado** — Xilinx's commercial synthesis + P&R + bitstream tool. Closed
source but free (gratis) for most parts.

**OpenLane** — Open-source RTL-to-GDSII flow for SkyWater 130 and similar.
Used for tape-outs through TinyTapeout / chipIgnite.

**GDSII** — The file format you submit to a foundry. Polygons on layers.
The end of the EDA flow.

**Verilator** — Open-source Verilog simulator. Compiles RTL to C++ for
fast simulation. Used by ASICify's testbenches.

**Cocotb** — Python framework for verifying hardware designs. Drives RTL
simulators with ordinary Python tests. ASICify generates cocotb testbenches.

**Place-and-route (P&R)** — After synthesis, decide where on the die each
cell goes and how to wire them. Determines the actual area and timing.

**Timing closure** — Iterating P&R until all timing paths meet their
budgets. Where most ASIC engineering schedules go to die.

**Floorplan** — High-level layout: which regions hold which blocks. ASICify
estimates a floorplan from the compute graph; the playground visualizes it.

## Web / infrastructure

**Clerk** — Auth-as-a-service. We use it for sign-in. Issues JWTs the API
verifies.

**Modal** — Compute-on-demand for Python jobs. Containers spin up per call,
GPUs available, scales to zero. Where the worker runs in production.

**R2** — Cloudflare's S3-compatible object storage. No egress fees (vs S3's
$0.09/GB). Where artifacts live.

**MinIO** — Open-source S3-compatible storage. Used in `infra/docker-compose.yml`
for local dev.

**Neon** — Hosted Postgres with branching. Free tier has been generous.

**Upstash** — Serverless Redis. Pay per request.

**Fly.io** — Edge container hosting. Where the API runs in MVP.

**Vercel** — Where the Next.js frontend deploys.

**Turborepo** — Monorepo build orchestrator. Knows the dep graph, parallels
tasks, caches outputs.

**uv** — Fast Python package manager (Rust-based). Replaces pip + virtualenv +
pip-tools.

**pnpm** — Fast Node package manager with workspace support. Stricter than
npm/yarn about phantom dependencies.

**WebSocket** — Browser-native bidirectional connection. ASICify uses one
per active project to stream progress events.

**Pub/sub** — Publish/subscribe messaging pattern. Redis supports it natively;
ASICify uses it for progress events because durability isn't needed.

**BLPOP** — Redis blocking list pop. Worker idiom: block until a job arrives.

**JWT** — JSON Web Token. Self-contained authn token. Clerk issues these;
the API verifies them with Clerk's public key.

## ASICify-specific

**ModelGraph** — Our IR. Layer list + parameter count + per-layer
compression metadata. See [worker.md](worker.md#the-modelgraph-ir).

**CompressionConfig** — User intent: quantization mode + sparsity + decomp +
fine-tune flag. The thing that varies across projects.

**Stage** — One step of the compression pipeline. `(ModelGraph, Config) →
ModelGraph` pure function.

**Effective parameters** — Param count after sparsity and decomposition are
applied. What the area model sums over.

**Effective bits per weight** — Total compressed weight payload bits divided
by parameter count. Includes the quantization choice plus any structural
compression. Lower is denser silicon.

**Multiplier strategy** — Choice of Verilog idiom for multiplication based
on quantization. Five flavors today (binary, ternary, INT4 CSD, INT8 Booth,
FP16 LUT).

**Confidence band** — `±N%` on every estimate. We don't pretend our numbers
are tighter than the underlying data.

**Cell library** — Per-target table of `mul_int8_um2`, `rom_bit_um2`,
`fmax_mhz`, etc. Lives in `apps/worker/worker/estimator/targets.py` (and
is duplicated client-side).

**Hot spot** — Code paths where most contributions land: pipeline/quantize.py,
rtl/templates/, estimator/targets.py, components/playground/. See
[codebase.md](../codebase.md#hot-spots--where-most-changes-will-land).
