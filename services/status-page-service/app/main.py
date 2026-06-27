from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from prometheus_client import make_asgi_app
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.db import SessionLocal
from app.migrations import run_schema_migrations
from app.routes.status import router as status_router
from app.services import apply_auto_update, auto_update_from_event
from app.settings import settings
from platform_common.auth import parse_api_keys, require_api_key
from platform_common.correlation import CorrelationIdMiddleware
from platform_common.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name)
    run_schema_migrations()
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    consumer_task = asyncio.create_task(consume_incident_events(redis))
    app.state.redis = redis
    app.state.service_name = settings.service_name
    try:
        yield
    finally:
        consumer_task.cancel()
        await asyncio.gather(consumer_task, return_exceptions=True)
        await redis.aclose()


app = FastAPI(title="Status Page Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

protected = [Depends(require_api_key(parse_api_keys(settings.platform_api_keys)))]
app.include_router(status_router, dependencies=protected)
app.mount("/metrics", make_asgi_app())


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


async def consume_incident_events(redis: Redis) -> None:
    try:
        await redis.xgroup_create(
            settings.event_stream_name,
            settings.event_consumer_group,
            id="0",
            mkstream=True,
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise

    while True:
        messages = await redis.xreadgroup(
            settings.event_consumer_group,
            settings.service_name,
            {settings.event_stream_name: ">"},
            count=10,
            block=5000,
        )
        for _stream, entries in messages:
            for stream_id, fields in entries:
                raw_event = fields.get(b"event") or fields.get("event")
                if raw_event is None:
                    await redis.xack(settings.event_stream_name, settings.event_consumer_group, stream_id)
                    continue
                try:
                    payload = auto_update_from_event(raw_event)
                    if payload is not None:
                        with SessionLocal() as session:
                            updates = apply_auto_update(session, payload)
                            logger.info(
                                "created_status_updates count=%s incident_id=%s",
                                len(updates),
                                payload.incident_id,
                            )
                except Exception:
                    logger.exception("status_event_processing_failed stream_id=%s", stream_id)
                finally:
                    await redis.xack(settings.event_stream_name, settings.event_consumer_group, stream_id)
