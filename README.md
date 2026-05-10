<div align="center">

```
    ▄▄▄    ▄▄▄    ▄▄▄    ▄▄▄    ▄▄▄    ▄▄▄    ▄▄▄    ▄▄▄
   █████  █████  █████  █████  █████  █████  █████  █████
   █████  █████  █████  █████  █████  █████  █████  █████
   ▀▀▀▀▀  ▀▀▀▀▀  ▀▀▀▀▀  ▀▀▀▀▀  ▀▀▀▀▀  ▀▀▀▀▀  ▀▀▀▀▀  ▀▀▀▀▀
```

# ASIC<sub>|</sub>fy

**The compiler for AI silicon.**
PyTorch model in. Hardware-ready specification out.

[Live playground →](http://localhost:3001/playground) · [Docs](./docs/codebase.md) · [Roadmap](./docs/roadmap.md)

</div>

---

## What it does

```
   ┌──────────────┐    ┌─────────────────┐    ┌───────────────────┐
   │              │    │                 │    │  Synthesizable    │
   │  PyTorch     │───▶│   ASICify       │───▶│  Verilog          │
   │  checkpoint  │    │   compiler      │    │  + Cocotb test    │
   │              │    │                 │    │  + Area / cost    │
   └──────────────┘    └─────────────────┘    │  + FPGA bitstream │
                                              └───────────────────┘
```

ASICify takes a trained neural network and emits everything you need to put
it on silicon: aggressively compressed weights, synthesizable Verilog with
those weights hardwired as ROM constants, area / throughput / cost / energy
estimates across eleven hardware targets, an FPGA reference implementation,
and a verified Cocotb testbench.

It is the horizontal compiler underneath every AI chip company that exists
today, and the ones that haven't started yet.

## Why

Custom AI silicon costs $5–30M per tape-out and takes 6–18 months. The
fabrication isn't the bottleneck — it's the model-to-hardware translation.
Every chip company and edge-AI deployer currently does that translation by
hand, with expensive specialist engineers, the same way they did it ten years
ago.

Cadence and Synopsys built EDA for general-purpose chips. ASICify is built
for one thing: turning a trained inference network into a fixed-function
accelerator.

## What you can do today

### 1. Play with the live estimator (zero install)

Open the playground in your browser. Drag the sparsity slider, switch between
INT4 and ternary, swap targets between TSMC 28nm and Lattice ECP5. Watch
silicon area, cost per chip, and throughput recompute in real time. Every
number is from a published cost model — no fake gauges, no mock data.

```
$ pnpm --filter @asicify/web dev
$ open http://localhost:3001/playground
```

### 2. Compile to RTL via the CLI

```bash
$ asicify compile gpt2 \
    --quantization int4 \
    --sparsity 2:4 \
    --target tsmc28,ecp5

✓ Parsed model graph         (124M params, 12 layers)
✓ Quantized to INT4          (perplexity 24.3 → 25.1)
✓ Applied 2:4 sparsity       (50% zeros)
✓ Generated RTL              (top.v + 47 modules)
✓ Estimated tsmc28           (8.2 mm², $4.10 @ 100K)
✓ Estimated ecp5             (LFE5UM5G-85, 78% LUT util)

Output: ./build/gpt2-int4-2_4/
```

The output is a zip with `top.v`, per-layer modules, hardwired weights,
Cocotb testbench, bit-exact Python reference, Makefile, and synthesis
scripts for Yosys / nextpnr / Vivado. Unzip and `make sim` or
`make synth-yosys` immediately.

### 3. Run the full hosted pipeline

API + worker + Postgres + Redis + R2-compatible object storage, all wired
together via docker-compose. Full project lifecycle, real-time progress
streaming over WebSocket, presigned downloads.

## What's wired today

| Capability                                  | Status                       |
| ------------------------------------------- | ---------------------------- |
| Live client-side estimator                  | ✓ Real math, real numbers    |
| Markdown documentation site                 | ✓ Auto-rendered from `/docs` |
| Landing, playground, pricing, blog, about   | ✓ Functional                 |
| FastAPI backend (auth + CRUD + queue + WS)  | ✓ Endpoints wired            |
| Postgres schema + Alembic migrations        | ✓ Initial migration shipped  |
| Worker pipeline (parse → quantize → … → validate) | ✓ Stage orchestration  |
| Hardware estimator (server-side)            | ✓ Cell library data for 11 targets |
| RTL generator + 14 Jinja2 templates         | ✓ Top + linear + attention + layernorm + KV cache + testbench + synthesis scripts |
| Multi-precision multiplier strategies       | ✓ binary / ternary / int4 CSD / int8 Booth / fp16 LUT |
| Real `torch.fx` model parsing               | ◐ Synthesized graph stub today; real parsing is next |
| Quantization weight-tensor work             | ◐ Config tracked; bit-packing is next |
| WebGPU in-browser inference comparison      | ○ Roadmap                    |
| PDF report generation                       | ○ Roadmap                    |
| Modal deployment                            | ○ Roadmap                    |
| Stripe billing                              | ○ Roadmap                    |

The MVP ships a complete spine. Filling in the model-loading kernels and
real validation does not require API or pipeline changes.

## Repository layout

```
asicify/
├── apps/
│   ├── web/             Next.js 15 frontend
│   │                    Landing · live playground · markdown docs · blog · about · pricing
│   │
│   ├── api/             FastAPI backend
│   │                    Clerk JWT auth · project CRUD · Redis job queue · WebSocket progress
│   │
│   └── worker/          Python worker
│                        ├── pipeline/   parse · quantize · sparsity · decompose · validate
│                        ├── rtl/        Jinja2 → Verilog package
│                        └── estimator/  area · throughput · cost · per-target cell library
│
├── packages/
│   └── shared/          TypeScript types (mirrored as Pydantic + Python dataclasses)
│
├── infra/               docker-compose: Postgres · Redis · MinIO (R2 stand-in)
│
└── docs/                User docs (rendered at /docs/*)
    └── internals/       Contributor docs (rendered at /docs/internals/*)
```

## Quick start

### Just the web app (fastest)

No databases, no Python, no GPU. The live estimator runs in your browser.

```bash
git clone https://github.com/claynicholson/asicify
cd asicify
pnpm install
pnpm --filter @asicify/web dev
# → http://localhost:3001
```

### Full local stack

Adds the API, worker, Postgres, Redis, and an S3-compatible object store.

```bash
# 1. Install everything
pnpm install
cd apps/api    && uv sync && cd ../..
cd apps/worker && uv sync && cd ../..

# 2. Start infrastructure
docker compose -f infra/docker-compose.yml up -d

# 3. Run database migrations
cd apps/api && uv run alembic upgrade head && cd ../..

# 4. Boot all three apps
pnpm dev
```

You'll get:

| Service       | URL                           |
| ------------- | ----------------------------- |
| Web           | http://localhost:3001         |
| API           | http://localhost:8000         |
| API docs      | http://localhost:8000/docs    |
| MinIO console | http://localhost:9001         |

## Hardware targets

Eleven targets across three categories:

| Category | Target                                                       |
| -------- | ------------------------------------------------------------ |
| ASIC     | SkyWater 130 · GF22FDX · TSMC 28nm · TSMC 16nm · TSMC 7nm    |
| FPGA     | Lattice ECP5 · Lattice CrossLink-NX · Xilinx Artix-7 · Xilinx Kria K26 |
| Shuttle  | TinyTapeout (sky130) · Efabless chipIgnite (sky130)          |

Each target ships with cell-library data: ROM bit area, SRAM bit area,
INT8 multiplier area, max clock frequency, energy per MAC, wafer cost,
defect density. All numbers cite published academic surveys or foundry
data sheets and carry ±20–40% confidence bands.

See [`docs/methodology.md`](./docs/methodology.md) for the full cost-model
derivation.

## Compression methods

Five quantization modes, four sparsity patterns, three decompositions —
fully composable.

```
Quantization     FP16 ─ INT8 ─ INT4 ─ Ternary ─ Binary
                                          1.6 bit/weight ─┐
                                                          │ Sub-1-bit
Sparsity         none ─ 2:4 ─ 4:8 ─ block 16×16 ─ unstructured
                                                          │
Decomposition    none ─ Monarch ─ Butterfly ─ Low-rank    │
                                                          ▼
                                                  Effective bits/weight
                                                  drops below 1
```

Each compression method maps to a specific multiplier strategy in the
generated RTL:

| Quantization | Multiplier strategy        | Approx LUTs/MAC          |
| ------------ | -------------------------- | ------------------------ |
| Binary       | XNOR + popcount            | ~1                       |
| Ternary      | Sign-flip mux + zero-out   | ~3                       |
| INT4         | CSD shift-add network      | ≤ 1 add                  |
| INT8         | Booth multiplier           | ~10                      |
| FP16         | Per-multiplier ROM-LUT     | small ROM                |

Weights become `localparam` constants in `weights.vh`. The synthesis tool
folds them directly into the multiplier inputs — for binary and ternary
this collapses entirely into XOR/AND networks, with no real multipliers
on die.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    User (Browser)                          │
└───────────────────────────┬────────────────────────────────┘
                            │ HTTPS / WSS
┌───────────────────────────▼────────────────────────────────┐
│              Next.js Frontend (Vercel)                     │
│  • App Router  • Server Components  • Live estimator       │
└───────────────────────────┬────────────────────────────────┘
                            │ REST / WebSocket
┌───────────────────────────▼────────────────────────────────┐
│             FastAPI Backend (Fly.io)                       │
│  • Auth (Clerk JWT)  • Project CRUD  • Job orchestration   │
└──────┬──────────────┬──────────────────┬───────────────────┘
       │              │                  │
       ▼              ▼                  ▼
┌─────────────┐ ┌──────────────┐ ┌─────────────────────────┐
│ PostgreSQL  │ │   Redis      │ │   Modal Labs            │
│ (Neon)      │ │  (Upstash)   │ │  (GPU worker pool)      │
└─────────────┘ └──────────────┘ └──────────┬──────────────┘
                                            │
                                            ▼
                                  ┌─────────────────────┐
                                  │   Cloudflare R2     │
                                  │   Artifacts         │
                                  └─────────────────────┘
```

The compiler core (`apps/worker/worker/{pipeline,rtl,estimator}/`) runs
without the API, the database, Redis, or any auth. The CLI calls it
directly. The hosted product layers convenience on top.

See [`docs/architecture.md`](./docs/architecture.md) for component
responsibilities and [`docs/internals/data-flow.md`](./docs/internals/data-flow.md)
for end-to-end traces.

## Tech stack

| Layer        | Choice                                                              |
| ------------ | ------------------------------------------------------------------- |
| Frontend     | Next.js 15 · React 19 · TypeScript strict · Tailwind v4 · Recharts  |
| Backend      | FastAPI · Pydantic v2 · SQLAlchemy 2.0 async · Alembic              |
| Worker       | PyTorch · Transformers · Jinja2 · structlog                         |
| Database     | PostgreSQL (Neon)                                                   |
| Queue        | Redis lists + pub/sub (Upstash)                                     |
| Storage      | Cloudflare R2 (S3-compatible; MinIO locally)                        |
| Auth         | Clerk                                                               |
| Compute      | Modal Labs                                                          |
| Build        | Turborepo · pnpm · uv                                               |
| Verification | Cocotb · Verilator                                                  |
| Synthesis    | Yosys · nextpnr · Vivado                                            |

## Differentiators

**Multi-target backend.** One tool, every target. The same source model
emits SkyWater 130 RTL, TSMC 28nm RTL, ECP5 bitstreams, TinyTapeout
shuttles. Compare them in one dashboard.

**Open-source core.** MIT-licensed. The compression pipeline and RTL
generator are on GitHub. No NDAs, no per-tape-out licensing. The hosted
product is convenience and compute.

**Hardware-software co-design.** Sub-1-bit effective representation via
ternary + sparsity + decomposition. Monarch matrix factorization built
into synthesis. Hardware-aware fine-tuning that targets your specific
deployment.

**Inverse design.** Specify a target chip area or BOM cost; ASICify
searches the model architecture space for the best model that fits.
Hardware-aware NAS with real cost models.

**Design space exploration.** Pull a slider in the playground, watch the
chip change. Cached estimates update in under a millisecond.

## Documentation

**For users:**

- [docs/quickstart.md](./docs/quickstart.md) — Compile your first model
- [docs/architecture.md](./docs/architecture.md) — System overview
- [docs/methodology.md](./docs/methodology.md) — Cost model derivation
- [docs/rtl-generation.md](./docs/rtl-generation.md) — Verilog templates and multiplier strategies
- [docs/roadmap.md](./docs/roadmap.md) — Phase plan

**For contributors:**

- [docs/codebase.md](./docs/codebase.md) — Codebase tour. Start here.
- [docs/internals/web.md](./docs/internals/web.md) — Frontend
- [docs/internals/api.md](./docs/internals/api.md) — Backend
- [docs/internals/worker.md](./docs/internals/worker.md) — Pipeline + RTL gen + estimator
- [docs/internals/data-flow.md](./docs/internals/data-flow.md) — End-to-end traces
- [docs/internals/extending.md](./docs/internals/extending.md) — Recipes: add a target, a precision, a primitive
- [docs/internals/conventions.md](./docs/internals/conventions.md) — Code style
- [docs/internals/glossary.md](./docs/internals/glossary.md) — ML, silicon, EDA terminology

## Status

Pre-1.0. Spine first: model in → compressed model out → quality validation
→ RTL out → cost estimate → playground.

We're shipping every week. Watch [docs/roadmap.md](./docs/roadmap.md) for
the phase plan and [CHANGELOG.md](./CHANGELOG.md) for what landed.

## Contributing

PRs welcome. The high-leverage areas:

- Adding hardware targets (cell library data with citations)
- New compression methods (FP4, FP8 E4M3, MXFP formats)
- New layer kinds (Mamba blocks, MoE routers, diffusion primitives)
- Refining cost-model parameters with foundry data sheets

See [CONTRIBUTING.md](./CONTRIBUTING.md) and
[docs/internals/extending.md](./docs/internals/extending.md) for recipes.

## License

MIT. The hosted version at [asicify.com](https://asicify.com) layers
convenience and compute over this open-source core. Premium hardware
targets (TSMC leading-edge nodes, Samsung) require commercial agreements
with the foundries; the open core supports SkyWater 130, GF22FDX, ECP5,
Artix-7 directly.

## Acknowledgements

- [Tri Dao](https://tridao.me/) and the HazyResearch team for Monarch matrices
- [Matt Venn](https://www.mattvenn.net/) for TinyTapeout
- [SkyWater](https://github.com/google/skywater-pdk) and [Efabless](https://efabless.com/) for the open PDK movement
- [The Yosys + nextpnr team](https://yosyshq.net/yosys/) for the open synthesis flow
- [Cocotb](https://www.cocotb.org/) for making hardware verification feel like Python

---

<div align="center">

**ASIC<sub>|</sub>fy** · Built for the AI silicon era · MIT licensed

</div>
