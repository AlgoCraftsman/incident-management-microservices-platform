from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text


ReadinessCheck = Callable[[], Any | Awaitable[Any]]


async def collect_readiness(service_name: str, checks: dict[str, ReadinessCheck]) -> dict[str, object]:
    results: dict[str, object] = {}
    ready = True
    for name, check in checks.items():
        try:
            result = check()
            if inspect.isawaitable(result):
                await result
            results[name] = {"status": "ok"}
        except Exception as exc:
            ready = False
            results[name] = {"status": "error", "detail": exc.__class__.__name__}

    payload: dict[str, object] = {
        "status": "ready" if ready else "not_ready",
        "service": service_name,
        "checks": results,
    }
    if not ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    return payload


def database_check(session_factory: Callable[[], Any]) -> ReadinessCheck:
    def check() -> None:
        with session_factory() as session:
            session.execute(text("SELECT 1"))

    return check


def redis_check(redis_client: Any) -> ReadinessCheck:
    async def check() -> None:
        pong = await redis_client.ping()
        if pong is False:
            raise RuntimeError("Redis ping failed")

    return check
