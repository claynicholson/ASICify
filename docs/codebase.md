# Codebase Guide

This document is the entry point for understanding the ASICify codebase. It
assumes you have read [README.md](../README.md) and want to actually work
inside the repo: fix a bug, add a target, ship a feature.

## What ASICify is, in one paragraph

ASICify is a compiler. The input is a trained neural network (usually a
PyTorch checkpoint or a HuggingFace model id). The output is a hardware-ready
specification: aggressively compressed weights, synthesizable Verilog with
those weights hardwired as constants, area / throughput / cost / energy
estimates across foundry nodes and FPGAs, and a verified testbench. The
hosted product is a thin web app over a Python pipeline; the same pipeline is
also a CLI you can run locally.

## Repository at a glance

```
asicify/
├── apps/
│   ├── web/        Next.js 15 frontend (landing + playground + docs)
│   ├── api/        FastAPI backend (auth + project CRUD + job orchestration)
│   └── worker/     Python worker (compression pipeline + RTL gen + estimator)
├── packages/
│   └── shared/     TypeScript types (mirrored as Pydantic schemas in api,
│                   and as dataclasses in worker)
├── infra/          docker-compose for local dev (Postgres + Redis + MinIO)
└── docs/           User-facing + internal documentation
```

The repo is a pnpm workspace driven by Turborepo for the JS side, and `uv` for
each Python package. There are **no cross-package imports** between Python
apps: `apps/api` and `apps/worker` are independent processes that communicate
only via Redis and Postgres. They share *types* by convention, not by code.

## How to navigate this guide

| Topic                                     | Read                                                                  |
| ----------------------------------------- | --------------------------------------------------------------------- |
| What every file does                      | [internals/web.md](internals/web.md), [internals/api.md](internals/api.md), [internals/worker.md](internals/worker.md) |
| What happens when a user clicks "Compile" | [internals/data-flow.md](internals/data-flow.md)                      |
| How to add a new hardware target          | [internals/extending.md](internals/extending.md#add-a-hardware-target) |
| How to add a new RTL primitive            | [internals/extending.md](internals/extending.md#add-a-layer-kind) |
| Coding conventions                        | [internals/conventions.md](internals/conventions.md)                  |
| Domain vocabulary                         | [internals/glossary.md](internals/glossary.md)                        |
| User-facing methodology                   | [methodology.md](methodology.md)                                      |
| User-facing architecture                  | [architecture.md](architecture.md)                                    |

## The four-layer mental model

ASICify is four stacked layers, each with one job:

1. **Presentation** (`apps/web`): renders configuration UI, streams job
   progress, shows cached estimates within ~500ms of any slider move.
2. **Orchestration** (`apps/api`): auth, persistence, job queueing. Owns
   no compute.
3. **Pipeline** (`apps/worker/worker/pipeline`): parse → quantize →
   sparsity → decompose → validate. Each stage is a pure function
   (`ModelGraph → ModelGraph`).
4. **Codegen** (`apps/worker/worker/{rtl,estimator}`): `ModelGraph` +
   `CompressionConfig` → Verilog package + cost numbers. Pure functions,
   deterministic, cacheable.

The hard rule: **layers below never call layers above**. Layer 4 only sees a
`ModelGraph` and a `CompressionConfig`; it never knows it ran in a hosted
environment, never touches Redis, never checks auth. This is what lets the
same code drive the CLI, the hosted job worker, and any future on-prem
deployment.

## The two core contracts

Two data structures hold the system together.

### `ModelGraph`: the IR between pipeline stages

Defined in three places that must stay in sync:

- TypeScript: `packages/shared/src/types.ts` (no `ModelGraph` per se on the
  client, but related types live here)
- Pydantic: `apps/api/app/schemas.py`
- Python dataclass: `apps/worker/worker/types.py` (`ModelGraph`)

`ModelGraph` is what you get out of stage 1 (parse) and what every other
pipeline stage takes and returns. It carries layers (`LayerInfo`), per-layer
quantization decisions, sparsity masks, and decomposition metadata. It is
**immutable in spirit**: stages return a new graph via `dataclasses.replace`
rather than mutating in place.

### `CompressionConfig`: the user's intent

A `CompressionConfig` is what the user picks in the playground or sends in
`POST /api/projects`. It's the *only* thing that makes one project's output
differ from another's, given the same model. Same definition, three places:

- `packages/shared/src/types.ts` (`CompressionConfig`)
- `apps/api/app/schemas.py` (Pydantic, used in request bodies)
- `apps/worker/worker/types.py` (dataclass, used in pipeline)

Every cache key in the worker is a hash of `(model_source, compression_config,
target)`, which is what makes runs reproducible.

## The estimator lives in two places on purpose

There are **two** hardware estimators, and you need both.

1. **Client-side estimator**: `apps/web/lib/estimator.ts`. Pure TypeScript,
   no network. Runs every time the user moves a slider. Cached cell library
   numbers, simplified math, ±30% confidence band. Hits in < 1ms so the
   playground feels instant.

2. **Server-side estimator**: `apps/worker/worker/estimator/`. Real
   compute graph, real area/throughput/cost models, runs as part of a job.
   Authoritative; what gets written to the database and the PDF report.

These two share the same numerical constants (per-target cell library data),
but the duplication is deliberate. The client is read-only and stateless;
shipping the worker code to the browser would be wrong on every axis. When
you change cell library numbers, you change them in both:

- TS: `apps/web/lib/estimator.ts` (`NODE_PARAMS`)
- Python: `apps/worker/worker/estimator/targets.py` (`ASIC_NODES`)

A future improvement would be a build-step codegen that derives one from the
other. For now, conventions enforce the sync.

## The control flow, once

A single sentence per major path:

- **User opens playground**: `apps/web/app/playground/page.tsx` mounts;
  `quickEstimate` from `apps/web/lib/estimator.ts` runs synchronously on every
  config change.
- **User signs up + creates project**: frontend POSTs to `/api/projects` →
  `apps/api/app/routers/projects.py` writes a row, returns it.
- **User clicks Compile**: frontend POSTs to `/api/projects/{id}/compress` →
  router creates a `Job`, pushes JSON to Redis list `asicify:jobs`.
- **Worker runs the job**: `apps/worker/worker/main.py` BLPOPs the list,
  dispatches by `job_type` to one of `run_compression_job`, `run_rtl_job`, or
  `run_estimate_job`, each emitting progress events to
  `asicify:progress:<project_id>`.
- **Frontend hears progress**: WebSocket at
  `/api/projects/{id}/progress` (handled by `apps/api/app/routers/progress.py`)
  forwards Redis pub/sub messages to the browser.
- **Worker finishes**: uploads artifacts to R2, writes Artifact rows,
  publishes `complete`, project status flips to `complete`.

A more rigorous trace lives in [internals/data-flow.md](internals/data-flow.md).

## Conventions in 90 seconds

- **Import order**: stdlib → third-party → first-party. Ruff `I` enforces.
- **Type annotations**: required everywhere in Python. `Mapped[X]` for ORM,
  Pydantic for schemas, plain dataclasses for worker IR.
- **Imports across apps**: forbidden. Apps share data through Redis +
  Postgres, not Python imports.
- **No `from app.*` in worker code** and vice versa.
- **TypeScript**: strict mode, named exports, no default exports for
  components except Next.js page files.
- **Prefer named arguments at call sites** when the call has > 2 args.
- **Comments explain *why***, not *what*. The code says what.
- **No premature abstractions.** Three similar bits of code is fine; abstract
  on the fourth.

Full version: [internals/conventions.md](internals/conventions.md).

## What's implemented vs. pending

The compiler core works end-to-end: real parsing, real quantization across
five precisions, real sparsity, SVD / Monarch / butterfly decomposition, and
RTL generation with a bit-exact reference, all locked in by the pytest suite.
The authoritative list of what's shipped, partial, and not started is
[roadmap.md](roadmap.md); if this table and the roadmap ever disagree, the
roadmap wins.

| Component                              | Status                                          |
| -------------------------------------- | ----------------------------------------------- |
| Frontend pages + playground            | Complete                                        |
| Client-side estimator                  | Complete (with simplified math)                 |
| API endpoints + auth + queue + WS      | Complete                                        |
| Database schema + migrations           | Complete                                        |
| Worker job dispatch + progress events  | Complete                                        |
| Pipeline orchestration + kernels       | Complete (parse, quantize, sparsity, validate)  |
| Decomposition (SVD, Monarch, butterfly) | Complete                                       |
| Hardware estimator (server)            | Complete (first-order)                          |
| RTL templates + packaging + synthesis scripts | Complete                                 |
| Public deployment of API + worker      | Not started                                     |
| Hardware-aware fine-tuning             | Not started                                     |
| Stripe billing                         | Not started                                     |

## Hot spots: where most changes will land

If you're going to spend time anywhere, it'll be one of these:

1. `apps/worker/worker/pipeline/quantize.py`: when adding new precisions
   (FP4, FP8 E4M3, MXFP4, etc.) or improving sensitivity-driven mixed precision.
2. `apps/worker/worker/rtl/templates/`: adding new layer kinds (Mamba,
   diffusion blocks, MoE routers) or new multiplier strategies.
3. `apps/worker/worker/estimator/targets.py` + `apps/web/lib/estimator.ts`:
   adding hardware targets or refining cell library numbers.
4. `apps/web/components/playground/`: UX iteration on the demo that drives
   most signups.

If you're touching anything else, double-check that you're not solving a
problem that should be solved in one of those four places instead.

## The MIT-licensed promise

Every file under `apps/worker/worker/{pipeline,rtl,estimator}/` is part of the
**open-source core**. It must continue to run standalone via the CLI without
the API, the database, Redis, or any auth. When you're tempted to import
`app.something` or assume a Redis connection, stop and find another way.

The hosted product layers convenience and compute on top of this core. The
core is what gives ASICify its credibility with researchers and hardware
engineers; keep it self-contained.
