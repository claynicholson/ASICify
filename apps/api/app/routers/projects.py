"""Project CRUD + job submission."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models import Job, Project, User
from app.queue import enqueue_job
from app.schemas import (
    CreateProjectRequest,
    JobResponse,
    ProjectResponse,
)

router = APIRouter()


async def _ensure_user(session: AsyncSession, current: CurrentUser) -> User:
    user = (
        await session.execute(select(User).where(User.clerk_id == current.clerk_id))
    ).scalar_one_or_none()
    if not user:
        user = User(clerk_id=current.clerk_id, email=current.email or "unknown")
        session.add(user)
        await session.flush()
    return user


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    user = await _ensure_user(session, current)
    rows = (
        await session.execute(
            select(Project)
            .where(Project.user_id == user.id)
            .order_by(Project.updated_at.desc())
        )
    ).scalars().all()
    await session.commit()
    return list(rows)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: CreateProjectRequest,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    user = await _ensure_user(session, current)
    project = Project(
        user_id=user.id,
        name=body.name,
        model_source=body.model_source.model_dump(),
        compression_config=body.compression.model_dump(),
        target_hardware=list(body.targets),
        status="draft",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    project = await _load_project(session, project_id, current)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    project = await _load_project(session, project_id, current)
    await session.delete(project)
    await session.commit()


@router.post("/{project_id}/compress", response_model=JobResponse)
async def start_compress(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    project = await _load_project(session, project_id, current)
    return await _enqueue(session, project, job_type="compress")


@router.post("/{project_id}/generate-rtl", response_model=JobResponse)
async def start_generate_rtl(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    project = await _load_project(session, project_id, current)
    return await _enqueue(session, project, job_type="rtl")


@router.post("/{project_id}/estimate-hw", response_model=JobResponse)
async def start_estimate(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    project = await _load_project(session, project_id, current)
    return await _enqueue(session, project, job_type="estimate")


@router.get("/{project_id}/status", response_model=list[JobResponse])
async def project_status(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: CurrentUser = Depends(get_current_user),
):
    project = await _load_project(session, project_id, current)
    rows = (
        await session.execute(
            select(Job).where(Job.project_id == project.id).order_by(Job.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


# ---------- helpers ----------

async def _load_project(
    session: AsyncSession, project_id: UUID, current: CurrentUser
) -> Project:
    user = await _ensure_user(session, current)
    project = await session.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


async def _enqueue(session: AsyncSession, project: Project, job_type: str) -> Job:
    job = Job(
        id=uuid4(),
        project_id=project.id,
        job_type=job_type,
        status="queued",
    )
    session.add(job)
    project.status = "queued"
    await session.commit()
    await session.refresh(job)

    await enqueue_job(
        {
            "job_id": str(job.id),
            "project_id": str(project.id),
            "job_type": job_type,
            "model_source": project.model_source,
            "compression_config": project.compression_config,
            "target_hardware": project.target_hardware,
        }
    )
    return job
