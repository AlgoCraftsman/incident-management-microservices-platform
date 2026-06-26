from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import IncidentStatus, Severity, TimelineEvent
from app.schemas import IncidentCreate
from app.services import create_incident, get_incident_by_idempotency_key, has_open_duplicate


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_create_incident_records_idempotency_and_timeline_event():
    session = make_session()
    payload = IncidentCreate(
        title="Checkout error budget burn",
        description="Critical error rate on checkout",
        severity=Severity.p1,
        service_name="checkout",
        alert_ids=["alert-1"],
    )

    incident = create_incident(session, payload, actor="alerts-service", idempotency_key="alert:fingerprint-1")

    assert get_incident_by_idempotency_key(session, "alert:fingerprint-1").id == incident.id
    timeline = session.query(TimelineEvent).filter_by(incident_id=incident.id).one()
    assert timeline.event_type == "incident.created"
    assert timeline.actor == "alerts-service"
    assert timeline.event_metadata["service_name"] == "checkout"


def test_open_duplicate_lookup_ignores_resolved_incidents():
    session = make_session()
    create_incident(
        session,
        IncidentCreate(title="Checkout outage", severity=Severity.p1, service_name="checkout"),
    )

    assert has_open_duplicate(session, "checkout") is True

    incident = get_incident_by_idempotency_key(session, None)
    stored = session.query(TimelineEvent).first().incident
    stored.status = IncidentStatus.resolved
    session.commit()

    assert incident is None
    assert has_open_duplicate(session, "checkout") is False
