# ASICify

> The compiler for AI silicon. PyTorch model in, hardware-ready specification out.

ASICify converts trained neural network models into hardware-ready specifications: aggressively compressed weights, synthesizable Verilog with hardwired multipliers, area/cost/throughput estimates across foundry nodes and FPGA targets, and a verified testbench.

**One-line pitch:** From PyTorch to tape-out in minutes, not months.

## Repository layout

```
asicify/
├── apps/
│   ├── web/        Next.js 15 frontend (landing, playground, dashboard)
│   ├── api/        FastAPI backend (auth, project CRUD, job orchestration)
│   └── worker/     Python worker (compression pipeline, RTL gen, estimator)
├── packages/
│   └── shared/     Shared TypeScript types
├── infra/          docker-compose for local dev
└── docs/           Architecture, methodology, API reference
```

## Quick start (local dev)

Requirements: Node 20+, pnpm 9+, Python 3.11+, Docker (for Postgres + Redis).

```bash
# 1. Install JS deps
pnpm install

# 2. Start Postgres + Redis
docker compose -f infra/docker-compose.yml up -d

# 3. Install Python deps
cd apps/api && uv sync && cd ../..
cd apps/worker && uv sync && cd ../..

# 4. Run migrations
cd apps/api && uv run alembic upgrade head && cd ../..

# 5. Start everything
pnpm dev
```

The web app starts on `http://localhost:3000`, API on `http://localhost:8000`.

## Status

MVP in progress. Spine first: model in → compressed model out → quality validation → RTL out → simple cost estimate → playground.

## Docs

**For users:**
- [docs/quickstart.md](docs/quickstart.md) — Compile your first model in 5 minutes
- [docs/architecture.md](docs/architecture.md) — System design overview
- [docs/methodology.md](docs/methodology.md) — How our cost models work
- [docs/rtl-generation.md](docs/rtl-generation.md) — Verilog generation details
- [docs/roadmap.md](docs/roadmap.md) — What's shipped, what's next

**For contributors:**
- [docs/codebase.md](docs/codebase.md) — Codebase tour. Read first.
- [docs/internals/](docs/internals/) — Per-app deep dives, data flow traces,
  extension recipes, conventions, glossary.

## License

MIT. The hosted version at asicify.com layers convenience and compute over this open-source core.
