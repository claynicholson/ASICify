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

## Web app

The web app ships as a single Docker image: a Next.js standalone server
plus the markdown content from `docs/`. No database, no Redis, no other
external dependencies. The playground runs in the browser and the docs
are baked into the image.

### Build and run

From the repo root:

```bash
docker build -t asicify/web .
docker run --rm -p 3000:3000 asicify/web
```

First build takes around 60 to 90 seconds; subsequent builds reuse the
layer cache for `pnpm install` unless `pnpm-lock.yaml` changed. The image
runs as a non-root user, listens on `0.0.0.0:3000`, and reaps signals via
`tini`.

The Dockerfile uses three stages:

1. **`deps`**: installs workspace dependencies. Cached on `pnpm-lock.yaml`.
2. **`builder`**: runs `pnpm --filter @asicify/web build`, producing the
   Next.js standalone bundle.
3. **`runner`**: copies the standalone server, the static assets, and the
   `docs/` directory into a slim `node:22-alpine` image. No source code
   in the final layer.

The final image is a few hundred MB; most of that is the Node runtime.

### Runtime environment variables

| Variable    | Default      | Purpose                                |
| ----------- | ------------ | -------------------------------------- |
| `PORT`      | `3000`       | Bind port for the Next.js server.      |
| `HOSTNAME`  | `0.0.0.0`    | Bind host. Leave alone in containers.  |
| `NODE_ENV`  | `production` | Don't override.                        |

If the API and worker get deployed in the future, the web app will gain a
`NEXT_PUBLIC_API_BASE_URL` env var to point at them.

### Why `docs/` is copied into the image

The `/docs/[...slug]` route reads markdown files at request time via
`apps/web/lib/docs.ts`. That code resolves `../../docs/` relative to the
working directory. The Dockerfile copies `docs/` into the right path
(`/app/docs/`) and sets `WORKDIR /app/apps/web` so the path math lines
up. If you add new markdown under `docs/` you need to rebuild the image.
The trade-off (vs. mounting a volume) is that deployments are atomic and
cacheable.

### Fly.io

Drop this into a `fly.toml` at the repo root, then `fly launch` (first
time) or `fly deploy` (subsequent):

```toml
app = "asicify-web"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 3000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512
```

### Railway

Connect the repo. Railway detects the `Dockerfile` automatically. Set
`PORT=3000` in service variables. No other config needed.

### Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/asicify-web
gcloud run deploy asicify-web \
  --image gcr.io/PROJECT_ID/asicify-web \
  --platform managed \
  --port 3000 \
  --allow-unauthenticated
```

Cloud Run scales to zero when idle, which fits the workload: the
playground is the only stateful interaction, and that state lives in the
user's browser.

### Vercel (no Docker)

Vercel deploys Next.js directly without the Dockerfile. The
`output: "standalone"` setting is harmless; Vercel uses its own runtime.
Connect the repo and configure `apps/web` as the root directory in the
project settings. This is the lowest-friction option for the web app
today. Use the Dockerfile when you need to deploy alongside the API and
worker on shared infra.

### Health check

The image has no dedicated `/healthz` route. Use `GET /` for liveness
probes. A 200 response means Next is up and the markdown content is
reachable.

### Troubleshooting

**`/docs/quickstart` returns 404 in the container.**
The `docs/` directory wasn't copied into the image. Rebuild from the
repo root, not from `apps/web/`. The build context must include `docs/`.

**Build fails at `pnpm install` with a lockfile error.**
You changed `package.json` without updating `pnpm-lock.yaml`. Run
`pnpm install` locally first, commit the new lockfile, then rebuild.

**Container starts but refuses connections.**
Verify `PORT` and `HOSTNAME`. The default is `0.0.0.0:3000`. If your
platform sets a different port (Cloud Run uses `8080`), pass it as an
env var.

**Image is larger than expected.**
Check that `.dockerignore` is being respected. `apps/api`, `apps/worker`,
and `infra/` should not be in the build context for the web image.

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

Default in `fly.toml` is shared-cpu 1x, 512 MB, which covers low-traffic
use. The app is async, so a single worker handles many concurrent
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

1. Per-call billing fits a small-project budget.
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

The default `gpu="A10G"` is more than the current pipeline needs (no
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

Runs the full pytest suite (most of the wall-clock time is the uv
install).

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
- [ ] Cost monitoring on Modal (per-call billing, but a stuck
      queue_pump can run away)
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
this is free or near-free. The first cost to materialize is Clerk past
10K MAU.

## Remaining work

- **No service has been pushed live yet.** Everything above is the
  recipe; running it requires hosting account credentials.
- **DNS.** The web app, API, and worker need real domain names
  (e.g. `asicify.com`, `api.asicify.com`) before production cert
  pinning.
- **Monitoring.** The Sentry SDK is referenced but not wired into the
  API's exception handler.
- **WebSocket hardening.** The endpoint currently trusts the project
  ID. Before opening to the public, add signed connection tokens.

None of these block local development.
