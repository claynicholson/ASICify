"""Modal deployment of the worker.

To deploy:
    cd apps/worker
    uv run --with modal modal deploy worker/modal_app.py

Once deployed, the API enqueues jobs to Redis and Modal-side functions pull
them off the same queue. The Modal container has a real GPU available for
the kernel-heavy parts (HF model loading, activation-MSE validation, future
hardware-aware fine-tuning).

Why Modal:
  - Scales to zero between bursts.
  - Per-call billing fits a hobby project budget.
  - One-line GPU access (`modal.gpu.A10G()`).

Deployment requires the `hosted` extra plus `modal`:
    uv sync --extra hosted
    uv pip install modal
"""

from __future__ import annotations

import os
from typing import Any

# Import is lazy so the rest of the worker package doesn't depend on modal.
try:
    import modal  # type: ignore
except ImportError:  # pragma: no cover
    modal = None  # type: ignore


if modal is not None:
    image = (
        modal.Image.debian_slim(python_version="3.12")
        .apt_install("git", "build-essential")
        .pip_install(
            "torch>=2.5.0",
            "numpy>=2.1.0",
            "pydantic>=2.9.0",
            "jinja2>=3.1.4",
            "structlog>=24.4.0",
            "transformers>=4.45.0",
            "accelerate>=1.0.0",
            "safetensors>=0.4.5",
            "redis>=5.1.1",
            "boto3>=1.35.0",
            "httpx>=0.27.2",
        )
        # Mount the worker package source.
        .add_local_python_source("worker")
    )

    app = modal.App("asicify-worker", image=image)

    secrets = [
        modal.Secret.from_name("asicify-redis", required_keys=["REDIS_URL"]),
        modal.Secret.from_name("asicify-r2", required_keys=["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"]),
    ]

    # Single-job container. Modal spins one up per call and tears it down after.
    @app.function(
        secrets=secrets,
        gpu="A10G",
        timeout=1800,
        cpu=2.0,
        memory=8192,
    )
    def run_job(job: dict[str, Any]) -> dict[str, Any]:
        """Run one compression / RTL / estimate job.

        Job shape mirrors the orchestrator API; see worker.main.dispatch.
        """
        import asyncio

        from worker.main import dispatch

        outputs: list[dict[str, Any]] = []

        async def emit(event: dict[str, Any]) -> None:
            outputs.append(event)

        async def run():
            # We don't need a real Redis client here; pass None.
            await dispatch(client=None, job=job, emit_override=emit)

        asyncio.run(run())
        return {"events": outputs}

    # Long-running pump that reads jobs off Redis directly. Use either this or
    # `run_job(...)` triggered from the API; not both.
    @app.function(
        secrets=secrets,
        gpu="A10G",
        timeout=86400,
        cpu=2.0,
        memory=8192,
    )
    def queue_pump() -> None:
        """Block on REDIS_URL queue and dispatch one job at a time."""
        import asyncio

        from worker.main import main as worker_main

        asyncio.run(worker_main())


def maybe_local_entry() -> None:
    """When called as `python -m worker.modal_app`, run a smoke job locally."""
    if modal is None:
        print("modal is not installed. Run: uv pip install modal")
        return
    print("modal app is defined. Deploy with: modal deploy worker/modal_app.py")


if __name__ == "__main__":
    maybe_local_entry()
