from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import AlertStatus
from app.schemas import AlertmanagerAlert
from app.services import should_promote, upsert_alert


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_upsert_alert_deduplicates_by_fingerprint():
    session = make_session()
    payload = AlertmanagerAlert(
        status=AlertStatus.firing,
        labels={
            "alertname": "HighErrorRate",
            "severity": "critical",
            "source": "prometheus",
            "service": "checkout",
        },
        annotations={"summary": "High checkout error rate"},
    )

    alert, first_duplicate = upsert_alert(session, payload, receiver="platform")
    duplicate, second_duplicate = upsert_alert(session, payload, receiver="platform")

    assert first_duplicate is False
    assert second_duplicate is True
    assert duplicate.id == alert.id
    assert session.query(type(alert)).count() == 1


def test_should_promote_only_critical_prometheus_firing_alerts_without_incident():
    session = make_session()
    alert, _ = upsert_alert(
        session,
        AlertmanagerAlert(
            status=AlertStatus.firing,
            labels={"alertname": "HighErrorRate", "severity": "critical", "source": "prometheus"},
        ),
        receiver=None,
    )

    assert should_promote(alert) is True

    alert.incident_id = "incident-1"
    assert should_promote(alert) is False
