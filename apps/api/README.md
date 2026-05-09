# asicify-api

FastAPI backend for ASICify. Handles auth, project CRUD, job orchestration,
and the WebSocket progress stream.

## Run locally

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

OpenAPI docs at `http://localhost:8000/docs`.

## Routes

- `GET /api/projects` — list projects for current user
- `POST /api/projects` — create project
- `GET /api/projects/{id}` — get project detail
- `DELETE /api/projects/{id}` — delete project
- `POST /api/projects/{id}/compress` — start compression job
- `POST /api/projects/{id}/generate-rtl` — start RTL generation job
- `POST /api/projects/{id}/estimate-hw` — start HW estimation job
- `GET /api/projects/{id}/status` — list jobs for project
- `GET /api/projects/{id}/artifacts` — list artifacts (with presigned download URLs)
- `WS  /api/projects/{id}/progress` — real-time progress events
- `GET /api/models/catalog` — curated model catalog
- `POST /api/models/upload-url` — presigned upload URL for custom checkpoints
- `GET /api/targets` — hardware target list
- `GET /api/targets/{id}/cost-model` — cost-model parameters

## Auth

Production uses Clerk. For local development, omit `CLERK_JWT_KEY` and pass
`X-Dev-User-Id: <uuid>` to act as that user. See `app/auth.py`.
