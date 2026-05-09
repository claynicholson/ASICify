"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import artifacts, models_catalog, progress, projects, targets

settings = get_settings()

logging.basicConfig(level=settings.log_level)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info("api.startup", env=settings.environment)
    yield
    log.info("api.shutdown")


app = FastAPI(
    title="ASICify API",
    version="0.1.0",
    description="The compiler for AI silicon. PyTorch model in, hardware-ready specification out.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(artifacts.router, prefix="/api/projects", tags=["artifacts"])
app.include_router(progress.router, prefix="/api/projects", tags=["progress"])
app.include_router(models_catalog.router, prefix="/api/models", tags=["models"])
app.include_router(targets.router, prefix="/api/targets", tags=["targets"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "asicify-api",
        "docs": "/docs",
        "health": "/health",
    }
