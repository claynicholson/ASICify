"""Clerk JWT verification.

In production, fetch and cache Clerk's JWKS and verify against it. For dev,
falls back to accepting any token if `clerk_jwt_key` is unset and the request
includes an `X-Dev-User-Id` header — keeps local development frictionless.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

settings = get_settings()
bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: UUID
    clerk_id: str
    email: str | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_dev_user_id: str | None = Header(default=None),
) -> CurrentUser:
    # Dev mode shortcut
    if not settings.clerk_jwt_key and x_dev_user_id:
        return CurrentUser(
            id=UUID(x_dev_user_id) if _is_uuid(x_dev_user_id) else uuid4(),
            clerk_id=f"dev_{x_dev_user_id}",
            email="dev@asicify.local",
        )

    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        if settings.clerk_jwt_key:
            payload = jwt.decode(
                credentials.credentials,
                settings.clerk_jwt_key,
                algorithms=["RS256"],
                issuer=settings.clerk_issuer or None,
                options={"verify_aud": False},
            )
        else:
            # Unverified decode for dev — never use in prod
            payload = jwt.decode(
                credentials.credentials, options={"verify_signature": False}
            )
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}") from e

    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing subject")

    return CurrentUser(
        id=uuid4(),  # Will be reconciled with the DB user record by routers.
        clerk_id=clerk_id,
        email=payload.get("email"),
    )


def _is_uuid(s: str) -> bool:
    try:
        UUID(s)
        return True
    except ValueError:
        return False
