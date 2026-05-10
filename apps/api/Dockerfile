# syntax=docker/dockerfile:1.7
#
# Production image for the ASICify FastAPI backend.
#
# Build from the repo root:
#   docker build -f apps/api/Dockerfile -t asicify/api .
#
# Run:
#   docker run --rm -p 8000:8000 \
#     -e DATABASE_URL=postgresql+asyncpg://... \
#     -e REDIS_URL=redis://... \
#     asicify/api

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install uv from the official image (faster than pip).
COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv

WORKDIR /app

# Layer 1: dependency manifests.
COPY apps/api/pyproject.toml apps/api/uv.lock* ./

# Install runtime deps (no dev tools, no test deps).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project 2>/dev/null || \
    uv pip install --system --no-deps -r <(uv export --no-dev 2>/dev/null) 2>/dev/null || \
    uv pip install --system "fastapi>=0.115" "uvicorn[standard]>=0.32" \
        "pydantic>=2.9" "pydantic-settings>=2.5" \
        "sqlalchemy[asyncio]>=2.0" "asyncpg>=0.30" "alembic>=1.13" \
        "redis>=5.1" "boto3>=1.35" "httpx>=0.27" \
        "python-jose[cryptography]>=3.3" "structlog>=24.4"

# Layer 2: application source.
COPY apps/api/app ./app
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./alembic.ini

# Health-check: hitting / responds with 200.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"

EXPOSE 8000

# Run migrations on container start, then start the server.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
