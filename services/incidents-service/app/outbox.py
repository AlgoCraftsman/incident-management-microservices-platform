from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.models import OutboxEvent
from platform_common.events import EventEnvelope, RedisStreamPublisher

logger = logging.getLogger(__name__)


async def publish_outbox_loop(
    publisher: RedisStreamPublisher,
    *,
    poll_interval_seconds: float = 1.0,
    batch_size: int = 20,
) -> None:
    while True:
        published_count = await publish_pending_outbox_events(publisher, limit=batch_size)
        if published_count == 0:
            await asyncio.sleep(poll_interval_seconds)


async def publish_pending_outbox_events(publisher: RedisStreamPublisher, *, limit: int = 20) -> int:
    published_count = 0
    with SessionLocal() as session:
        events = list(
            session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.status.in_(("pending", "failed")))
                .order_by(OutboxEvent.created_at.asc())
                .limit(limit)
            ).all()
        )
        for event in events:
            try:
                stream_id = await publisher.publish(to_envelope(event))
            except Exception as exc:
                event.status = "failed"
                event.attempts += 1
                event.last_error = str(exc)[:1000]
                session.commit()
                logger.exception("outbox_publish_failed event_id=%s event_type=%s", event.id, event.event_type)
                continue

            event.status = "published"
            event.attempts += 1
            event.stream_id = stream_id
            event.last_error = None
            event.published_at = datetime.now(UTC)
            session.commit()
            published_count += 1
            logger.info(
                "outbox_event_published event_id=%s event_type=%s stream_id=%s",
                event.id,
                event.event_type,
                stream_id,
            )
    return published_count


def to_envelope(event: OutboxEvent) -> EventEnvelope:
    return EventEnvelope(
        event_id=event.id,
        event_type=event.event_type,
        event_version=event.event_version,
        occurred_at=event.created_at.isoformat(),
        producer=event.producer,
        correlation_id=event.correlation_id,
        idempotency_key=event.idempotency_key,
        payload=event.payload,
    )
