"""Hardware target catalog + cost-model parameters."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.data.targets import TARGETS, COST_MODELS
from app.schemas import TargetSpec

router = APIRouter()


@router.get("", response_model=list[TargetSpec])
async def list_targets() -> list[TargetSpec]:
    return TARGETS


@router.get("/{target_id}/cost-model")
async def cost_model(target_id: str) -> dict:
    if target_id not in COST_MODELS:
        raise HTTPException(404, f"Unknown target: {target_id}")
    return COST_MODELS[target_id]
