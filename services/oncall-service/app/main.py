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
from app.routes.oncall import router as oncall_router
from app.services import (
    already_processed_event,
    dispatch_notification,
    notification_from_incident_event,
    parse_event,
    record_processed_event,
)
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


app = FastAPI(title="On-Call Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

protected = [
    Depends(
        require_api_key(
            parse_api_keys(settings.platform_api_keys),
            required_scopes={f"{settings.service_name}:access"},
        )
    )
]
app.include_router(oncall_router, dependencies=protected)
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
                    event = parse_event(raw_event)
                    stream_id_value = _stream_id_to_str(stream_id)
                    with SessionLocal() as session:
                        if already_processed_event(session, event["event_id"]):
                            await redis.xack(settings.event_stream_name, settings.event_consumer_group, stream_id)
                            continue
                        payload = notification_from_incident_event(raw_event)
                        if payload is None:
                            record_processed_event(
                                session,
                                event=event,
                                stream_id=stream_id_value,
                                status_value="ignored",
                            )
                        else:
                            notification = dispatch_notification(session, payload, source_event_id=event["event_id"])
                            record_processed_event(
                                session,
                                event=event,
                                stream_id=stream_id_value,
                                status_value="processed",
                            )
                            logger.info(
                                "created_notification notification_id=%s incident_id=%s",
                                notification.id,
                                notification.incident_id,
                            )
                except Exception as exc:
                    logger.exception("oncall_event_processing_failed stream_id=%s", stream_id)
                    try:
                        event = parse_event(raw_event)
                        with SessionLocal() as session:
                            record_processed_event(
                                session,
                                event=event,
                                stream_id=_stream_id_to_str(stream_id),
                                status_value="failed",
                                error=str(exc),
                            )
                    except Exception:
                        logger.exception("oncall_failed_event_record_failed stream_id=%s", stream_id)
                finally:
                    await redis.xack(settings.event_stream_name, settings.event_consumer_group, stream_id)


def _stream_id_to_str(stream_id: bytes | str) -> str:
    return stream_id.decode("utf-8") if isinstance(stream_id, bytes) else stream_id
