# Roadmap

The MVP spine: model in → compressed model out → quality validation → RTL out
→ simple cost estimate → playground. Everything else is post-MVP.

## Phase 1 — Foundation (weeks 1–3)

- [x] Monorepo (Turborepo: web, api, worker, shared)
- [x] Database schema + Alembic migrations
- [x] Clerk auth scaffolding
- [x] R2 / MinIO storage helpers
- [x] Skeleton landing page

## Phase 2 — ML pipeline core (weeks 4–6)

- [x] Pipeline orchestrator with stage hooks
- [x] Quantization stage (INT8, INT4, ternary, binary)
- [x] Sparsity stage (2:4, 4:8, unstructured)
- [x] Quality validation harness
- [ ] Wire `torch.fx` real model parsing (currently synthesized)
- [ ] Wire `bitsandbytes` for INT4 GPTQ
- [ ] Modal deployment for GPU jobs

## Phase 3 — Hardware estimation (weeks 7–8)

- [x] Area / throughput / cost models
- [x] Cell library data for sky130, GF22FDX, TSMC 28/16/7
- [x] Multi-target comparison
- [x] Pareto plot in playground

## Phase 4 — RTL generation (weeks 9–10)

- [x] Jinja2 templates for linear, attention, FFN, layernorm, embedding, KV cache
- [x] Multi-precision multiplier strategies
- [x] Cocotb testbench scaffold
- [x] Yosys / nextpnr / Vivado synthesis scripts
- [ ] Bit-exact Python reference (currently stubbed)
- [ ] End-to-end synthesis verification on ECP5

## Phase 5 — Playground & polish (weeks 11–12)

- [x] Three-column interactive playground
- [x] Live cached estimator (<500ms feedback)
- [x] Pricing, docs, dashboard pages
- [ ] WebGPU inference comparison (transformers.js)
- [ ] PDF report generation (`@react-pdf/renderer`)
- [ ] Open-source the core on GitHub

## Phase 6 — Post-MVP

- Monarch matrix decomposition built into synthesis
- Hardware-aware fine-tuning in the loop
- TinyTapeout submission integration
- Speculative decoding hardware partitioning
- Multi-model deployment with shared backbone
- Diffusion LM and Mamba support
- API keys for programmatic access
- Stripe billing for paid tiers
- Self-hosted Enterprise option
