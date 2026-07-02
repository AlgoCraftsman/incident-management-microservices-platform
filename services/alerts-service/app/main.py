from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from prometheus_client import make_asgi_app
from redis.asyncio import Redis

from app.db import SessionLocal
from app.migrations import run_schema_migrations
from app.outbox import publish_outbox_loop
from app.routes.alerts import router as alerts_router
from app.settings import settings
from platform_common.auth import parse_api_keys, require_api_key
from platform_common.correlation import CorrelationIdMiddleware
from platform_common.events import RedisStreamPublisher
from platform_common.logging import configure_logging
from platform_common.readiness import collect_readiness, database_check, redis_check


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name)
    run_schema_migrations()
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    app.state.redis = redis
    app.state.event_publisher = RedisStreamPublisher(redis, settings.event_stream_name)
    app.state.service_name = settings.service_name
    outbox_task = asyncio.create_task(publish_outbox_loop(app.state.event_publisher))
    try:
        yield
    finally:
        outbox_task.cancel()
        await asyncio.gather(outbox_task, return_exceptions=True)
        await redis.aclose()


app = FastAPI(title="Alerts Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

protected = [
    Depends(
        require_api_key(
            parse_api_keys(settings.platform_api_keys),
            required_scopes={f"{settings.service_name}:access"},
        )
    )
]
app.include_router(alerts_router, dependencies=protected)
app.mount("/metrics", make_asgi_app())


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/ready", tags=["health"])
async def ready(request: Request) -> dict[str, object]:
    return await collect_readiness(
        settings.service_name,
        {
            "database": database_check(SessionLocal),
            "redis": redis_check(request.app.state.redis),
        },
    )
