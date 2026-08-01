# Architecture

## High-level system

```
┌────────────────────────────────────────────────┐
│                 User (browser)                 │
└───────────────────────┬────────────────────────┘
                        │ HTTPS / WSS
┌───────────────────────▼────────────────────────┐
│           Next.js frontend (Vercel)            │
│    App Router · server components · WebGPU     │
└───────────────────────┬────────────────────────┘
                        │ REST / WebSocket
┌───────────────────────▼────────────────────────┐
│       FastAPI backend (Fly.io / Railway)       │
│       Clerk JWT auth · job orchestration       │
└───────┬────────────────┬────────────────┬──────┘
        │                │                │
        ▼                ▼                ▼
 ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
 │ PostgreSQL  │  │    Redis    │  │ Modal Labs  │
 │   (Neon)    │  │  (Upstash)  │  │ GPU workers │
 └─────────────┘  └─────────────┘  └──────┬──────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │Cloudflare R2│
                                   └─────────────┘
```

## Component responsibilities

### Frontend (`apps/web`)

- All UI rendering, server components for SEO-relevant pages
- Auth flows via Clerk
- WebSocket for real-time job progress
- WebGPU inference for the in-browser model comparison
- Direct-to-R2 uploads via presigned URLs (skip API for large blobs)
- Client-side estimator for sub-500ms playground feedback (`lib/estimator.ts`)

### Backend API (`apps/api`)

- Clerk JWT verification on every authenticated route
- Project CRUD: persists model source, compression config, target list
- Job submission to Redis queue
- WebSocket forwards Redis pub/sub progress events
- Issues presigned R2 URLs for artifact downloads

### Worker (`apps/worker`)

- One job = one Modal container = scales to zero when idle
- Three job types: `compress`, `rtl`, `estimate`
- Reads model from R2 (or downloads from HuggingFace if catalog)
- Emits per-stage progress via Redis pub/sub
- Writes outputs to R2; persists artifact rows via internal API call

### PostgreSQL (Neon)

Tables: `users`, `projects`, `artifacts`, `jobs`. Schema lives in
`apps/api/app/models.py` with Alembic migrations under
`apps/api/alembic/versions/`.

### Redis (Upstash)

- `asicify:jobs`: list, BLPOP'd by workers
- `asicify:progress:<project_id>`: pub/sub channel per project
- Rate-limit counters
- Session cache

### R2 (Cloudflare)

User-uploaded checkpoints, generated RTL packages (zip), generated PDF
reports, sample model cache.

## Data flow for one job

1. User picks model + config in playground or `/projects/new`
2. Frontend → `POST /api/projects` → backend creates Project row, returns id
3. Frontend → `POST /api/projects/{id}/compress`
4. Backend creates Job row, pushes to `asicify:jobs`
5. Worker `BLPOP`s, updates project to `running`
6. Each pipeline stage: parse → quantize → sparsity → decompose → validate
7. Worker emits `stage_start` / `stage_complete` events to Redis
8. Backend WebSocket forwards events to the frontend
9. Worker uploads artifacts to R2, creates Artifact rows
10. Worker emits `complete` event; project status → `complete`
