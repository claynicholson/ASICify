"""Worker entry point. Pulls jobs from Redis, dispatches by job_type."""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import redis.asyncio as redis
import structlog

from worker.estimator.runner import run_estimate_job
from worker.pipeline.orchestrator import run_compression_job
from worker.rtl.generator import run_rtl_job

log = structlog.get_logger()

JOB_QUEUE_KEY = "asicify:jobs"
PROGRESS_CHANNEL_PREFIX = "asicify:progress:"


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    client = redis.Redis.from_url(redis_url, decode_responses=True)
    log.info("worker.start", redis=redis_url)

    while True:
        try:
            # Block up to 30s waiting for a job
            popped = await client.blpop([JOB_QUEUE_KEY], timeout=30)
            if popped is None:
                continue
            _, raw = popped
            job: dict[str, Any] = json.loads(raw)
            await dispatch(client, job)
        except asyncio.CancelledError:
            log.info("worker.shutdown")
            break
        except Exception as e:
            log.exception("worker.error", error=str(e))
            await asyncio.sleep(1)


async def dispatch(client: redis.Redis, job: dict[str, Any]) -> None:
    job_id = job["job_id"]
    project_id = job["project_id"]
    job_type = job["job_type"]
    log.info("job.start", job_id=job_id, type=job_type)

    async def emit(event: dict[str, Any]) -> None:
        event["project_id"] = project_id
        await client.publish(
            f"{PROGRESS_CHANNEL_PREFIX}{project_id}", json.dumps(event)
        )

    started = time.monotonic()
    try:
        if job_type == "compress":
            await run_compression_job(job, emit)
        elif job_type == "rtl":
            await run_rtl_job(job, emit)
        elif job_type == "estimate":
            await run_estimate_job(job, emit)
        else:
            await emit({"event": "error", "message": f"Unknown job type: {job_type}"})
            return

        await emit({"event": "complete"})
        log.info("job.done", job_id=job_id, elapsed=time.monotonic() - started)
    except Exception as e:
        log.exception("job.failed", job_id=job_id)
        await emit({"event": "error", "message": str(e)})


if __name__ == "__main__":
    asyncio.run(main())
