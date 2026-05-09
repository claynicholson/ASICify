"""WebSocket endpoint for streaming progress events to the frontend."""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.queue import subscribe_progress

router = APIRouter()


@router.websocket("/{project_id}/progress")
async def progress_ws(websocket: WebSocket, project_id: UUID):
    """Forward Redis pub/sub events for `project_id` to the connected client.

    Note: Auth is best done via signed query token here. For MVP we trust
    that project IDs are unguessable UUIDs and gate on existence elsewhere.
    """
    await websocket.accept()
    try:
        async for event in subscribe_progress(project_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    except asyncio.CancelledError:
        return
