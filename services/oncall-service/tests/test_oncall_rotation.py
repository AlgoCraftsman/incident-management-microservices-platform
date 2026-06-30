from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Notification, NotificationChannel, NotificationStatus, RotationType, Schedule
from app.schemas import NotifyRequest
from app.services import (
    MAX_CHANNEL_ATTEMPTS,
    already_processed_event,
    dispatch_notification,
    get_current_oncall,
    record_processed_event,
    retry_notification,
)


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_weekly_rotation_selects_expected_member():
    session = make_session()
    schedule = Schedule(
        name="Backend On-Call",
        timezone="UTC",
        rotation_type=RotationType.weekly,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        members=[
            {"user_id": "u1", "name": "Asha", "email": "asha@example.com"},
            {"user_id": "u2", "name": "Ben", "slack_id": "U123"},
        ],
    )
    session.add(schedule)
    session.commit()

    current = get_current_oncall(session, schedule, now=datetime(2026, 1, 8, tzinfo=UTC) + timedelta(hours=1))

    assert current["user_id"] == "u2"


def test_dispatch_prefers_slack_and_records_notification_payload():
    session = make_session()
    schedule = Schedule(
        name="Backend On-Call",
        timezone="UTC",
        rotation_type=RotationType.daily,
        members=[{"user_id": "u1", "name": "Asha", "email": "asha@example.com", "slack_id": "U123"}],
    )
    session.add(schedule)
    session.commit()

    notification = dispatch_notification(
        session,
        NotifyRequest(incident_id="incident-1", title="Checkout failure", severity="P1", service_name="checkout"),
    )

    assert notification.channel == NotificationChannel.slack
    assert notification.attempts == 1
    assert notification.status == NotificationStatus.sent
    assert notification.payload["service_name"] == "checkout"
    assert notification.payload["delivery"]["provider"] == "mock-slack"


def test_dispatch_reuses_existing_notification_for_source_event():
    session = make_session()
    schedule = Schedule(
        name="Backend On-Call",
        timezone="UTC",
        rotation_type=RotationType.daily,
        members=[{"user_id": "u1", "name": "Asha", "email": "asha@example.com"}],
    )
    session.add(schedule)
    session.commit()
    payload = NotifyRequest(
        incident_id="incident-1",
        title="Checkout failure",
        severity="P1",
        service_name="checkout",
    )

    first = dispatch_notification(session, payload, source_event_id="event-1")
    second = dispatch_notification(session, payload, source_event_id="event-1")

    notifications = session.query(Notification).all()
    assert first.id == second.id
    assert len(notifications) == 1
    assert notifications[0].source_event_id == "event-1"


def test_retry_failed_notification_stops_at_attempt_limit():
    session = make_session()
    notification = Notification(
        incident_id="incident-1",
        user_id="u1",
        channel=NotificationChannel.email,
        status=NotificationStatus.failed,
        attempts=MAX_CHANNEL_ATTEMPTS,
        payload={
            "incident_id": "incident-1",
            "target": {"user_id": "u1", "name": "Asha"},
            "message": "Incident incident-1 requires acknowledgement",
        },
    )
    session.add(notification)
    session.commit()

    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        retry_notification(session, notification)

    assert exc.value.status_code == 409


def test_processed_event_tracking_prevents_duplicate_consumption():
    session = make_session()
    event = {"event_id": "event-1", "event_type": "incident.created"}

    record = record_processed_event(session, event=event, stream_id="1-0", status_value="processed")
    duplicate = record_processed_event(session, event=event, stream_id="1-1", status_value="processed")

    assert record.event_id == duplicate.event_id
    assert duplicate.stream_id == "1-0"
    assert already_processed_event(session, "event-1") is True
