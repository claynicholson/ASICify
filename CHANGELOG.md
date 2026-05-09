# Changelog

All notable changes to ASICify are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — Initial scaffold

### Added
- Monorepo (Turborepo): `apps/web`, `apps/api`, `apps/worker`, `packages/shared`
- Next.js frontend with landing, playground, projects, pricing, docs
- Live client-side hardware estimator (sub-500ms feedback)
- FastAPI backend with project CRUD, job orchestration, WebSocket progress
- Worker with compression pipeline (parse, quantize, sparsity, decompose, validate)
- RTL generator with Jinja2 templates for linear, attention, layernorm, embedding, KV cache
- Hardware estimator with area/throughput/cost models for sky130, GF22FDX, TSMC 28/16/7, ECP5, Artix-7, Kria, TinyTapeout, chipIgnite
- Local dev: docker-compose with Postgres + Redis + MinIO
- Documentation: architecture, methodology, RTL generation, quickstart, roadmap
