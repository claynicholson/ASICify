"""Curated catalog of models that compress + synthesize well."""

from __future__ import annotations

from fastapi import APIRouter

from app.data.catalog import CATALOG
from app.schemas import CatalogModel
from app.storage import presign_upload

router = APIRouter()


@router.get("/catalog", response_model=list[CatalogModel])
async def list_catalog() -> list[CatalogModel]:
    return CATALOG


@router.post("/upload-url")
async def upload_url(filename: str) -> dict[str, str]:
    """Generate a presigned URL for direct-to-R2 model upload."""
    key = f"uploads/{filename}"
    return {"upload_url": presign_upload(key), "key": key}
