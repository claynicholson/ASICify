"""Artifact listing + presigned download URLs."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models import Artifact, Project, User
from app.schemas import ArtifactResponse
from app.storage import presign_download

router = APIRouter()


@router.get("/{project_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    user = (
        await session.execute(select(User).where(User.clerk_id == current.clerk_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    project = await session.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    rows = (
        await session.execute(
            select(Artifact)
            .where(Artifact.project_id == project_id)
            .order_by(Artifact.created_at.desc())
        )
    ).scalars().all()

    return [
        ArtifactResponse(
            id=a.id,
            project_id=a.project_id,
            type=a.type,
            size_bytes=a.size_bytes,
            created_at=a.created_at,
            download_url=presign_download(a.r2_key),
        )
        for a in rows
    ]


@router.get("/{project_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    project_id: UUID,
    artifact_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    artifact = await session.get(Artifact, artifact_id)
    if not artifact or artifact.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return ArtifactResponse(
        id=artifact.id,
        project_id=artifact.project_id,
        type=artifact.type,
        size_bytes=artifact.size_bytes,
        created_at=artifact.created_at,
        download_url=presign_download(artifact.r2_key),
    )
