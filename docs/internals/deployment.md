# Deployment runbook

All three services have deployment files committed. Each one needs hosting
account credentials to actually push live; this doc is the playbook for
when that happens.

## Service inventory

| Service | What | Where the files live | Where it deploys |
|---------|------|---------------------|------------------|
| Web app | Next.js standalone server + markdown docs | `Dockerfile`, `apps/web/` | Fly.io / Railway / Cloud Run / Vercel |
| FastAPI backend | Auth, project CRUD, job queue, WebSocket progress | `apps/api/Dockerfile`, `apps/api/fly.toml` | Fly.io |
| Python worker | Compression pipeline, RTL gen, kernels | `apps/worker/worker/modal_app.py` | Modal Labs (per-call GPU) |

Plus shared infra:

| Service | Provider | Why |
|---------|----------|-----|
| Postgres | Neon | Free tier, branching, async-ready |
| Redis | Upstash | Serverless, scales to zero |
| Object storage | Cloudflare R2 | S3-compatible, no egress fees |
| Auth | Clerk | JWT issuance + management |

## Web app (already deployable)

See [docs/deployment.md](../deployment.md) for the user-facing version.
Recap:

```bash
docker build -t asicify/web .
docker run --rm -p 3000:3000 asicify/web
```

Image is ~340 MB, cold-starts in ~150ms. The image is fully self-contained
(markdown docs are baked in, the playground is client-only). No env vars
required.

To deploy on Fly.io: `fly launch --no-deploy` once, then `fly deploy`.
A `fly.toml` for the web app would mirror the API's:

```toml
app = "asicify-web"
[build]
  dockerfile = "Dockerfile"
[http_service]
  internal_port = 3000
```

## FastAPI backend

### Dockerfile

`apps/api/Dockerfile` builds from python:3.12-slim, installs runtime deps
via `uv` from `apps/api/pyproject.toml`, copies the app source, and runs:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The Alembic migration step runs every time the container starts. For
production this is fine because migrations are idempotent; for serverless
contexts where containers cycle frequently, move the migration into a
separate one-shot `release_command` (Fly supports this).

### Required environment variables

The API will refuse to start if these aren't set in production
(controlled by `apps/api/app/config.py`):

| Var | Source | Purpose |
|-----|--------|---------|
| `DATABASE_URL` | Neon connection string | Async Postgres |
| `REDIS_URL` | Upstash connection string | Job queue + pub/sub |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 token | Artifact storage |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 token | |
| `R2_BUCKET` | Bucket name | |
| `R2_ENDPOINT` | Cloudflare R2 endpoint URL | |
| `CLERK_JWT_KEY` | Clerk dashboard | RS256 verification |
| `CLERK_ISSUER` | Clerk dashboard | JWT `iss` claim |

In dev with `CLERK_JWT_KEY` empty, the API accepts an `X-Dev-User-Id`
header instead of a JWT (see `apps/api/app/auth.py`). Don't deploy with
that mode enabled.

### Deploying to Fly.io

```bash
cd apps/api

# First time:
fly launch --no-deploy --name asicify-api --region iad
# (Pick a region close to your users; iad = US East)

# Set secrets
fly secrets set \
  DATABASE_URL="postgresql+asyncpg://..." \
  REDIS_URL="redis://..." \
  R2_ACCESS_KEY_ID="..." \
  R2_SECRET_ACCESS_KEY="..." \
  R2_BUCKET="asicify-artifacts" \
  R2_ENDPOINT="https://<account>.r2.cloudflarestorage.com" \
  CLERK_JWT_KEY="-----BEGIN PUBLIC KEY-----..." \
  CLERK_ISSUER="https://<your-clerk>.clerk.accounts.dev"

# Deploy
fly deploy

# Check
fly logs -a asicify-api
fly status -a asicify-api
```

### Health check

The Dockerfile's `HEALTHCHECK` polls `GET /health` every 30s. The route
exists in `apps/api/app/main.py`. Fly uses this to gate traffic.

### Scaling

```bash
fly scale count 2 -a asicify-api               # two machines
fly scale memory 1024 -a asicify-api           # 1 GB RAM
fly scale vm shared-cpu-2x -a asicify-api      # 2 vCPU
```

Default in `fly.toml` is shared-cpu 1x, 512 MB. Plenty for low-traffic
MVP. The app is async, so a single worker handles many concurrent
WebSocket connections.

### Migrations

Apply via the deploy step (auto), or manually:

```bash
fly ssh console -a asicify-api -C "alembic upgrade head"
```

To create a new migration:

```bash
cd apps/api
uv run alembic revision --autogenerate -m "what changed"
# Review the generated file in alembic/versions/, then commit.
# Next deploy applies it automatically.
```

## Python worker

The worker is deployed on Modal because:

1. Per-call billing fits a hobby-project budget.
2. One-line GPU access (`modal.gpu.A10G()`).
3. Scales to zero between bursts.

### Modal app definition

`apps/worker/worker/modal_app.py` defines:

- An `image` with apt + pip dependencies (CPU torch + transformers + the
  hosted-extra deps).
- `secrets`: `asicify-redis` and `asicify-r2` (created via `modal secret
  create`).
- `run_job(job)`: a single-call function. The API can invoke this
  directly via `app.functions.run_job.remote(job_dict)`.
- `queue_pump()`: a long-running function that BLPOPs the Redis queue
  and dispatches jobs. Use this *or* `run_job` direct invocation,
  not both.

### Deploying

```bash
# One-time setup
uv pip install modal
modal token new   # opens browser to authenticate

# Create secrets
modal secret create asicify-redis REDIS_URL="redis://..."
modal secret create asicify-r2 \
  R2_ACCESS_KEY_ID="..." \
  R2_SECRET_ACCESS_KEY="..."

# Deploy
cd apps/worker
modal deploy worker/modal_app.py

# Watch logs
modal app logs asicify-worker
```

### Choosing run_job vs queue_pump

**`run_job` (preferred)**: the API enqueues by calling
`app.functions.run_job.spawn(job_dict)`. Modal spins a container,
runs the job, returns. Per-call billing kicks in only when there's
work. Good for low traffic.

**`queue_pump`**: a single long-running function that reads from
Redis. Always running (and billing). Only use this if you have
sustained, bursty load that would be slow with cold-starts.

### GPU vs CPU

The default `gpu="A10G"` is overkill for the current pipeline (no
real model fine-tuning yet). For the demo + INT8 quantization +
RTL gen, switch to:

```python
@app.function(image=image, cpu=2.0, memory=8192, timeout=1800)
def run_job(job): ...
```

When real model loading and validation come online, reinstate the GPU.

## CI / GitHub Actions

`.github/workflows/ci.yml` runs three jobs in parallel on every push to
`main` and every PR:

### `worker-tests`

```yaml
- uses: astral-sh/setup-uv@v3
- working-directory: apps/worker
  run: uv sync --extra dev
- working-directory: apps/worker
  run: uv run pytest -q
```

Runs all 80 tests. Currently ~15 seconds end-to-end (most of which is
the uv install).

### `rtl-lint-and-synth`

```yaml
- run: sudo apt-get install -y verilator yosys
- working-directory: apps/worker
  run: uv run asicify demo --output ./build/demo
- working-directory: apps/worker/build/demo
  run: |
    verilator --lint-only -Wall -Wno-DECLFILENAME \
      top.v modules/*.v softmax.v kv_cache.v
    yosys -p "read_verilog -sv top.v modules/*.v softmax.v kv_cache.v; \
              hierarchy -top top; proc; flatten; stat"
```

Catches regressions where templates emit Python-valid but
synthesis-invalid Verilog. The `stat` command at the end of the yosys
run prints the gate count so reviewers can spot suspicious changes.

### `web-build`

```yaml
- pnpm install --filter @asicify/web... --frozen-lockfile
- pnpm --filter @asicify/web typecheck
- pnpm --filter @asicify/web build
- docker build -t asicify/web:ci .
```

Catches TS errors and Docker-build issues.

## Local dev parity

For everything to work locally with the same shape as production:

```bash
# Start infra
docker compose -f infra/docker-compose.yml up -d
# This brings up: Postgres on :5432, Redis on :6379, MinIO on :9000

# Initialize DB
cd apps/api && uv run alembic upgrade head

# Set local env
cp env.example .env  # then edit values

# Run all three apps in parallel
pnpm dev
# Web on :3001, API on :8000, worker pulls from local Redis
```

MinIO is the local stand-in for R2; the boto3 client config in
`apps/api/app/storage.py` uses `R2_ENDPOINT` so the same code path
works against either.

## Production-readiness checklist

When promoting from dev to production:

- [ ] `CLERK_JWT_KEY` set (no `X-Dev-User-Id` fallback)
- [ ] `DATABASE_URL` points at Neon (not local Postgres)
- [ ] `REDIS_URL` points at Upstash (not local Redis)
- [ ] R2 credentials are scoped to a single bucket
- [ ] Sentry DSN configured (if using)
- [ ] CORS origins in `apps/api/app/main.py` include the production
      web app domain only
- [ ] WebSocket auth wired (today the WS endpoint trusts the project
      ID; before going public, add a short-lived signed token in the
      connection URL)
- [ ] Modal secrets set (`asicify-redis`, `asicify-r2`)
- [ ] Cost monitoring on Modal (it's per-call but easy to runaway with
      a stuck queue_pump)
- [ ] Database backups enabled on Neon
- [ ] DNS pointed at the deployed services

## Cost estimate (rough, MVP traffic)

| Service | Free tier | Paid tier kicks in at |
|---------|-----------|----------------------|
| Vercel (web)        | Generous | ~100 GB bandwidth/mo |
| Fly.io (API)        | 3 shared VMs | extra machines or autoscaling |
| Neon (Postgres)     | 0.5 GB storage, 100 hrs compute | beyond that |
| Upstash (Redis)     | 10K commands/day | beyond that |
| Cloudflare R2       | 10 GB storage, 1M Class A ops/mo | beyond that |
| Clerk               | 10K MAU | beyond that |
| Modal               | $30/mo free credit | beyond that, ~$1-3/hr A10G when running |

For a pre-launch tool that runs maybe 100 compile jobs a week, all of
this is free or near-free. The first cost to materialize is Clerk if
you cross 10K MAU.

## What I haven't done

- **Actually pushed to any of these services.** Everything above is the
  recipe; running it requires the user's accounts.
- **Wired DNS.** The web app, API, and worker need real domain names
  (e.g. `asicify.com`, `api.asicify.com`) for production cert pinning.
- **Set up monitoring.** Sentry SDK is referenced but not wired into
  the API's exception handler. Adding it is a 5-line change.
- **Production-hardened the WebSocket.** It currently trusts the
  project ID. Before opening to the public, add signed connection
  tokens.

These are the next deployment chores; they're not blockers on the
dev experience.
