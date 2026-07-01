from __future__ import annotations

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import outbox
from app.db import Base
from app.models import OutboxEvent


class FakePublisher:
    def __init__(self) -> None:
        self.published_event_ids: list[str] = []

    async def publish(self, envelope) -> str:
        self.published_event_ids.append(envelope.event_id)
        return "1-0"


def make_sessionmaker():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_publish_pending_outbox_events_marks_event_published(monkeypatch):
    session_factory = make_sessionmaker()
    monkeypatch.setattr(outbox, "SessionLocal", session_factory)
    with session_factory() as session:
        session.add(
            OutboxEvent(
                id="event-1",
                event_type="incident.created",
                producer="incidents-service",
                correlation_id="correlation-1",
                payload={"incident_id": "incident-1"},
            )
        )
        session.commit()

    publisher = FakePublisher()

    published = asyncio.run(outbox.publish_pending_outbox_events(publisher))

    with session_factory() as session:
        event = session.get(OutboxEvent, "event-1")
        assert published == 1
        assert publisher.published_event_ids == ["event-1"]
        assert event.status == "published"
        assert event.stream_id == "1-0"
        assert event.attempts == 1
        assert event.published_at is not None
