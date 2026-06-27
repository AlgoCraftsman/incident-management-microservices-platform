from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import ComponentStatus
from app.schemas import AutoStatusUpdate
from app.services import apply_auto_update, auto_update_from_event, status_from_severity


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
