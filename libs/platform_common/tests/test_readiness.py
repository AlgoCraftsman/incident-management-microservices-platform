from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from platform_common.readiness import collect_readiness


def test_collect_readiness_returns_ready_payload():
    async def async_check():
        return None

    payload = asyncio.run(
        collect_readiness(
            "demo-service",
            {
                "database": lambda: None,
                "redis": async_check,
            },
        )
    )

    assert payload["status"] == "ready"
    assert payload["service"] == "demo-service"
    assert payload["checks"] == {"database": {"status": "ok"}, "redis": {"status": "ok"}}


def test_collect_readiness_raises_503_with_failed_check_detail():
    def failing_check():
        raise TimeoutError("database timeout")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(collect_readiness("demo-service", {"database": failing_check}))

    assert exc.value.status_code == 503
    assert exc.value.detail["status"] == "not_ready"
    assert exc.value.detail["checks"]["database"] == {"status": "error", "detail": "TimeoutError"}
