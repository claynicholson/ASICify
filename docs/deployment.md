# Deployment

The web app ships as a single Docker image. The image bundles a Next.js
standalone server plus the markdown content from `docs/`. No external
dependencies, no database, no Redis.

## Build

From the repo root:

```bash
docker build -t asicify/web .
```

First build is around 60 to 90 seconds. Subsequent builds reuse the layer
cache for `pnpm install` unless `pnpm-lock.yaml` changed.

## Run

```bash
docker run --rm -p 3000:3000 asicify/web
```

Open `http://localhost:3000`. That's it. The image runs as a non-root user,
listens on `0.0.0.0:3000`, and reaps signals via `tini`.

## Environment variables

The image picks up these at runtime:

| Variable                   | Default                  | Purpose                              |
| -------------------------- | ------------------------ | ------------------------------------ |
| `PORT`                     | `3000`                   | Bind port for the Next.js server.    |
| `HOSTNAME`                 | `0.0.0.0`                | Bind host. Leave alone in containers.|
| `NODE_ENV`                 | `production`             | Don't override.                      |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000`  | Backend API for the rewrite proxy. Only matters when the backend is wired. |

Example with a real backend:

```bash
docker run --rm -p 3000:3000 \
  -e NEXT_PUBLIC_API_BASE_URL=https://api.asicify.example \
  asicify/web
```

## Image anatomy

The Dockerfile uses three stages:

1. **`deps`** — installs workspace dependencies. Cached on `pnpm-lock.yaml`.
2. **`builder`** — runs `pnpm --filter @asicify/web build`, producing the
   Next.js standalone bundle.
3. **`runner`** — copies the standalone server, the static assets, and the
   `docs/` directory into a slim `node:22-alpine` image. No source code in
   the final layer.

Final image is around 180 to 220 MB. Most of that is the node runtime.

## Why `docs/` is copied into the image

The `/docs/[...slug]` route reads markdown files at request time via
`apps/web/lib/docs.ts`. That code resolves `../../docs/` relative to the
working directory. The Dockerfile copies `docs/` into the right path
(`/app/docs/`) and sets `WORKDIR /app/apps/web` so the path math lines up.

If you add new markdown under `docs/` you need to rebuild the image. The
trade-off (vs. mounting a volume) is that deployments are atomic and
cacheable.

## Deploying to Fly.io

Drop this into a `fly.toml` at the repo root:

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

Then `fly launch` (first time) or `fly deploy` (subsequent).

## Deploying to Railway

Connect the repo. Railway detects the `Dockerfile` automatically. Set
`PORT=3000` in service variables. No other config needed.

## Deploying to Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/asicify-web
gcloud run deploy asicify-web \
  --image gcr.io/PROJECT_ID/asicify-web \
  --platform managed \
  --port 3000 \
  --allow-unauthenticated
```

Cloud Run scales to zero when idle, which fits the workload (the playground
is the only stateful interaction, and that state lives in the user's
browser).

## Deploying to Vercel without Docker

Vercel deploys Next.js directly without the Dockerfile. The
`output: "standalone"` setting is harmless; Vercel uses its own runtime.
Connect the repo and Vercel detects `apps/web` automatically (configure
the root directory in the project settings).

This is the lowest-friction option for the web app today. Use the Dockerfile
when you need to deploy alongside the API and worker on shared infra.

## Health check

The image has no dedicated `/healthz` route. Use `GET /` for liveness probes.
A 200 response means Next is up and the markdown content is reachable.

## Troubleshooting

**`/docs/quickstart` returns 404 in the container.**
The `docs/` directory wasn't copied into the image. Rebuild from the repo
root, not from `apps/web/`. The build context must include `docs/`.

**Build fails at `pnpm install` with a lockfile error.**
You changed `package.json` without updating `pnpm-lock.yaml`. Run
`pnpm install` locally first, commit the new lockfile, then rebuild.

**Container starts but refuses connections.**
Verify `PORT` and `HOSTNAME`. The default is `0.0.0.0:3000`. If your platform
sets a different port (Cloud Run uses `8080`), pass it as an env var.

**Image is larger than expected.**
Check that `.dockerignore` is being respected. `apps/api`, `apps/worker`,
and `infra/` should not be in the build context for the web image.
