from __future__ import annotations

import secrets
from collections.abc import Iterable

from fastapi import Header, HTTPException, status


def parse_api_keys(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    return {item.strip() for item in raw_value.split(",") if item.strip()}


def require_api_key(valid_keys: Iterable[str]):
    keys = set(valid_keys)

    async def dependency(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        if not keys:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API key authentication is not configured",
            )
        if not x_api_key or not any(secrets.compare_digest(x_api_key, key) for key in keys):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )

    return dependency

