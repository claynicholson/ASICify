# Contributing to ASICify

Thanks for your interest. The core compiler is MIT-licensed and the project
runs on contributions from researchers, hardware engineers, and ML systems
folks.

## Where to start

- **Issues labeled `good first issue`** — usually new template additions, a new
  hardware target's cell library data, or a bug in the cost model.
- **New hardware target** — add a cell library to
  `apps/worker/worker/estimator/targets.py` and a `TargetSpec` to
  `apps/api/app/data/targets.py` plus the matching entry in
  `packages/shared/src/targets.ts`.
- **New compression method** — implement a new pipeline stage in
  `apps/worker/worker/pipeline/` and wire it into the orchestrator.
- **New RTL primitive** — add a `*.v.j2` template in
  `apps/worker/worker/rtl/templates/` and reference it from `generator.py`.

## Development setup

```bash
pnpm install
docker compose -f infra/docker-compose.yml up -d
cd apps/api && uv sync && uv run alembic upgrade head && cd ../..
cd apps/worker && uv sync && cd ../..
pnpm dev
```

## Pull requests

- Run `pnpm lint` and `pnpm typecheck` before submitting
- New features need at least a smoke test in `apps/<package>/tests/`
- Cost model changes must include a citation to the data source
- RTL template changes must include before/after Verilator + cocotb output

## Releases

Versions are bumped together across the monorepo. Changelog lives at
`CHANGELOG.md` (one entry per minor version).
