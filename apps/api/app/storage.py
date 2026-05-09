"""Cloudflare R2 (S3-compatible) helpers for upload presigning + downloads."""

from __future__ import annotations

import boto3
from botocore.client import Config

from app.config import get_settings

settings = get_settings()


def s3_client():
    endpoint = settings.r2_endpoint or (
        f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
        if settings.r2_account_id
        else "http://localhost:9000"  # MinIO fallback for local dev
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.r2_access_key_id or "minioadmin",
        aws_secret_access_key=settings.r2_secret_access_key or "minioadmin",
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def presign_upload(key: str, content_type: str = "application/octet-stream", expires: int = 3600) -> str:
    return s3_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.r2_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
    )


def presign_download(key: str, expires: int = 3600) -> str:
    return s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=expires,
    )
