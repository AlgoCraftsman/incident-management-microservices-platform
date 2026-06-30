from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import ComponentStatus
from app.schemas import AutoStatusUpdate
from app.services import (
    already_processed_event,
    apply_auto_update,
    auto_update_from_event,
    record_processed_event,
    status_from_severity,
)


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_severity_maps_to_public_component_status():
    assert status_from_severity("P1") == ComponentStatus.major_outage
    assert status_from_severity("P2") == ComponentStatus.partial_outage
    assert status_from_severity("P3") == ComponentStatus.degraded


def test_auto_update_creates_component_update_for_incident():
    session = make_session()

    updates = apply_auto_update(
        session,
        AutoStatusUpdate(
            incident_id="incident-1",
            title="Checkout outage",
            severity="P1",
            service_name="checkout",
            status="open",
        ),
    )

    assert updates[0].component_name == "checkout"
    assert updates[0].status == ComponentStatus.major_outage
    assert "incident-1" in updates[0].message


def test_auto_update_reuses_existing_update_for_source_event():
    session = make_session()
    payload = AutoStatusUpdate(
        incident_id="incident-1",
        title="Checkout outage",
        severity="P1",
        service_name="checkout",
        status="open",
    )

    first = apply_auto_update(session, payload, source_event_id="event-1")
    second = apply_auto_update(session, payload, source_event_id="event-1")

    assert first[0].id == second[0].id
    assert len(second) == 1
    assert second[0].source_event_id == "event-1"


def test_incident_event_is_parsed_into_auto_update_payload():
    event = {
        "event_type": "incident.created",
        "payload": {
            "incident_id": "incident-1",
            "title": "Checkout outage",
            "severity": "P1",
            "service_name": "checkout",
            "status": "open",
        },
    }

    payload = auto_update_from_event(json.dumps(event))

    assert payload is not None
    assert payload.service_name == "checkout"


def test_processed_event_tracking_prevents_duplicate_status_updates():
    session = make_session()
    event = {"event_id": "event-1", "event_type": "incident.created"}

    record = record_processed_event(session, event=event, stream_id="1-0", status_value="processed")
    duplicate = record_processed_event(session, event=event, stream_id="1-1", status_value="processed")

    assert record.event_id == duplicate.event_id
    assert duplicate.stream_id == "1-0"
    assert already_processed_event(session, "event-1") is True
