# API Internals: `apps/api`

FastAPI 0.115+, Pydantic v2, SQLAlchemy 2.0 async, Alembic, Redis (asyncio),
boto3 for R2.

## Directory map

```
apps/api/
├── app/
│   ├── __init__.py
│   ├── main.py              FastAPI factory, lifespan, CORS, route mounting
│   ├── config.py            Settings via pydantic-settings, .env loaded
│   ├── auth.py              Clerk JWT verification + dev-mode fallback
│   ├── db.py                Async engine, session factory, get_session dep
│   ├── models.py            ORM: User, Project, Artifact, Job
│   ├── schemas.py           Pydantic request/response models
│   ├── queue.py             Redis enqueue + pub/sub helpers
│   ├── storage.py           R2 / MinIO presigning
│   ├── data/
│   │   ├── catalog.py       Curated model list (mirrors web/lib/catalog.ts)
│   │   └── targets.py       Target catalog + per-node cost-model parameters
│   └── routers/
│       ├── projects.py      Project CRUD + job submission
│       ├── artifacts.py     Artifact list + presigned download URLs
│       ├── progress.py      WebSocket: forward Redis pub/sub to client
│       ├── models_catalog.py Catalog list + presigned upload URL
│       └── targets.py       Target list + cost-model parameters
├── alembic.ini              Alembic config
├── alembic/
│   ├── env.py               Async migration runner
│   ├── script.py.mako       Migration template
│   └── versions/
│       └── 20260101_*_0001_initial.py  Initial schema
├── pyproject.toml           Dependencies + uv config + ruff
└── package.json             pnpm scripts (dev/lint/typecheck), no JS deps
```

## Application factory

[`app/main.py`](../../apps/api/app/main.py) builds a `FastAPI` instance with
lifespan management for logging, CORS for the configured frontend origins, and
five mounted routers. The lifespan currently logs startup/shutdown only; when
we wire Sentry or Modal warmup it goes here.

Key decision: there is **no global app state** beyond what `Settings` carries.
Database engine and Redis pool are module-level singletons in
`app/db.py` and `app/queue.py` respectively. This keeps tests easy: a fresh
test client gets a fresh engine if you re-import.

## Auth model

[`app/auth.py`](../../apps/api/app/auth.py) defines a `CurrentUser`
dataclass and a `get_current_user` dependency. Three modes:

1. **Production**: `CLERK_JWT_KEY` is set. Token verified with RS256 against
   Clerk's signing key. `iss` checked against `CLERK_ISSUER`.
2. **Dev with no Clerk**: `CLERK_JWT_KEY` empty + `X-Dev-User-Id` header
   present. Skip verification, treat the header as the user. This allows
   local development without a Clerk account.
3. **Dev with token but no key**: signature decoded but not verified. Only
   for testing token plumbing.

Mode 3 is dangerous in production; the deploy checklist must verify that
`environment != "development"` and `CLERK_JWT_KEY` is set.

User reconciliation: every authenticated route that needs a user calls
`_ensure_user(session, current)`; see
[`routers/projects.py`](../../apps/api/app/routers/projects.py). This
upserts the User row by `clerk_id`, so the first call after Clerk sign-up
silently creates the row.

## Database

### Schema

Four tables, defined in [`app/models.py`](../../apps/api/app/models.py):

- **`users`**: `clerk_id` is unique. We mirror only what we need.
- **`projects`**: `model_source`, `compression_config`, `target_hardware`
  stored as JSON. We don't normalize because (a) shapes change as we evolve
  the compiler, and (b) we never query into them.
- **`artifacts`**: one row per generated file (RTL zip, PDF report, etc.).
  `r2_key` is the canonical pointer; presigned URLs are issued at read time.
- **`jobs`**: persisted job records. The actual queue lives in Redis; this
  table is for status display and audit.

### Migrations

Async Alembic. The single `0001_initial.py` migration creates all four tables.
Subsequent changes use `uv run alembic revision --autogenerate -m "..."` and
get committed alongside the model change.

`alembic/env.py` reads `app.config.get_settings().database_url` so migrations
honor the same env vars as runtime.

### Sessions

`get_session` is the FastAPI dependency. It yields a session and closes it
after the request. Routers commit explicitly; we don't auto-commit.

For background work that doesn't have a request, use the `session_scope`
context manager (also in `db.py`) which commits on success and rolls back on
exception.

## Routers: the API surface

All five routers are mounted under `/api`. The endpoint table:

```
POST   /api/projects                       Create project
GET    /api/projects                       List user's projects
GET    /api/projects/{id}                  Get project detail
DELETE /api/projects/{id}                  Delete project
POST   /api/projects/{id}/compress         Start compression job
POST   /api/projects/{id}/generate-rtl     Start RTL generation
POST   /api/projects/{id}/estimate-hw      Run hardware estimation
GET    /api/projects/{id}/status           List jobs for project
GET    /api/projects/{id}/artifacts        List artifacts (presigned URLs)
GET    /api/projects/{id}/artifacts/{aid}  One artifact (presigned URL)
WS     /api/projects/{id}/progress         Stream progress events

GET    /api/models/catalog                 Curated model list
POST   /api/models/upload-url              Presigned upload URL

GET    /api/targets                        Hardware target list
GET    /api/targets/{id}/cost-model        Per-target cost model parameters
```

### `routers/projects.py`

The hot path. Three sections:

1. **`_ensure_user`**: User upsert helper.
2. **`_load_project`**: Authorization + 404 helper. Every project route
   calls it; never bypass.
3. **`_enqueue`**: Job creation pattern. Creates a `Job` row, sets project
   status to `queued`, then `enqueue_job` pushes to Redis. The order matters:
   the row exists before the worker can process it, so worker progress
   updates always have a row to update.

Adding a new job type is mechanical:

1. Add a router method `start_<type>` calling `_enqueue(..., job_type="...")`.
2. Add a dispatch case in `apps/worker/worker/main.py:dispatch`.
3. Implement `run_<type>_job(job, emit)` in the worker.

### `routers/progress.py`

A single WebSocket endpoint. The handler accepts the connection, then iterates
`subscribe_progress(project_id)` from `app/queue.py` which is an async
generator over Redis pub/sub. Every message becomes a `ws.send_json` call.

There is **no auth** on this WebSocket today. The bet is that project IDs
are unguessable UUIDs. Before exposing the API publicly we'll switch to a
short-lived signed token in the connection URL, similar to how Sentry and
LiveKit do it.

### `routers/artifacts.py`

Artifact listing with presigned download URLs. R2 (and MinIO locally) issue
URLs that expire in 1 hour by default; adjust via the `expires` argument in
[`app/storage.py`](../../apps/api/app/storage.py).

The artifact routes do their own ownership check inline rather than reusing
`_load_project`. This is intentional duplication; `artifacts.py` doesn't
import from `projects.py`. If you find yourself adding more cross-cutting
auth logic, that's the cue to extract a `deps.py` module.

### `routers/models_catalog.py` and `routers/targets.py`

These wrap the static data in `app/data/`. No database hits. The data is
pulled from the same constants (catalog, targets) that the worker uses for
its calculations. If you change a target's spec, you change it here and in
`apps/worker/worker/estimator/targets.py`; see the sync rule in
[codebase.md](../codebase.md#the-estimator-lives-in-two-places-on-purpose).

## Redis usage

[`app/queue.py`](../../apps/api/app/queue.py) defines two key patterns:

```
asicify:jobs                  # Redis list, BLPOP'd by workers
asicify:progress:<project_id> # pub/sub channel, one per project
```

Both decisions are deliberate:

- **List for jobs**: at MVP volume, BLPOP scales fine. When we need
  visibility (job age, dead-letter, retries), migrate to Redis Streams. The
  worker's only assumption is `BLPOP returns a JSON string`; switching the
  storage shape doesn't break the worker.
- **Pub/sub for progress**: we don't need durability. If a client misses a
  progress event because they reconnected, it's fine; the project status
  in Postgres is the source of truth. Pub/sub gives us the lowest-latency
  delivery and trivial fan-out for shared dashboards.

## Storage (R2 / MinIO)

[`app/storage.py`](../../apps/api/app/storage.py) wraps `boto3.client('s3')`
with R2 credentials. R2 is S3-compatible, and MinIO (in
`infra/docker-compose.yml`) is also S3-compatible: same code path locally
and in production.

The two helpers:

- `presign_upload(key, content_type, expires)`: for direct-from-browser
  uploads. Skips the API for the actual bytes.
- `presign_download(key, expires)`: issued in artifact list responses.

R2 charges nothing for egress, which is why we picked it over S3.

## Configuration

[`app/config.py`](../../apps/api/app/config.py) uses `pydantic-settings` and
reads from `.env` and the project-root `.env`. Settings is `lru_cache`d so
imports get the same instance.

Conventions:

- All env vars are uppercase with the same name as the Settings field.
- Boolean flags default to `False`; "off by default" is the safe choice.
- A field with no default is **required** at startup; FastAPI will fail to
  boot rather than blow up on first request.

## Error handling

We don't have a global exception handler today. FastAPI defaults are
acceptable:

- `HTTPException` → JSON with `detail`.
- Uncaught exceptions → 500, no trace leaked to client.
- Validation errors → 422 with field-by-field messages.

When we add Sentry, the integration goes in `app/main.py`'s lifespan and a
`@app.exception_handler(Exception)` decorator. Don't catch and re-raise just
to add logging; `structlog` already gets the trace.

## Test plan (not yet implemented)

- `pytest-asyncio` for async tests.
- `httpx.AsyncClient(app=app)` for in-process HTTP testing.
- Test database via `testcontainers` Postgres or SQLite-in-memory with a
  compatibility shim (the schema is JSON-heavy so SQLite mostly works).
- Mock Redis with `fakeredis.aioredis`.

The first tests to write: project CRUD with auth happy path, then the
`_enqueue → BLPOP → progress publish` round trip with a fake worker.

## Deploying

The target is **Fly.io**. `apps/api/Dockerfile` and `apps/api/fly.toml`
are committed; see [deployment.md](deployment.md) for the full runbook
(secrets, migrations, scaling, health checks).
