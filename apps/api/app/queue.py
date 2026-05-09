"""Redis-backed job queue and pub/sub for progress events."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

JOB_QUEUE_KEY = "asicify:jobs"
PROGRESS_CHANNEL_PREFIX = "asicify:progress:"


_pool: redis.ConnectionPool | None = None


def get_pool() -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url, decode_responses=True
        )
    return _pool


def get_client() -> redis.Redis:
    return redis.Redis(connection_pool=get_pool())


async def enqueue_job(job: dict[str, Any]) -> None:
    """Push a job onto the queue. Workers BLPOP this key."""
    client = get_client()
    await client.rpush(JOB_QUEUE_KEY, json.dumps(job))


async def publish_progress(project_id: UUID, event: dict[str, Any]) -> None:
    client = get_client()
    await client.publish(
        f"{PROGRESS_CHANNEL_PREFIX}{project_id}", json.dumps(event)
    )


async def subscribe_progress(project_id: UUID) -> AsyncIterator[dict[str, Any]]:
    """Yield progress events for a project until cancelled."""
    client = get_client()
    pubsub = client.pubsub()
    await pubsub.subscribe(f"{PROGRESS_CHANNEL_PREFIX}{project_id}")
    try:
        async for msg in pubsub.listen():
            if msg["type"] != "message":
                continue
            try:
                yield json.loads(msg["data"])
            except json.JSONDecodeError:
                continue
    finally:
        await pubsub.unsubscribe(f"{PROGRESS_CHANNEL_PREFIX}{project_id}")
        await pubsub.aclose()
