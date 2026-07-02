from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, AlertStatus, OutboxEvent
from app.schemas import AlertmanagerAlert, SuppressAlertRequest
from app.settings import settings


@dataclass(frozen=True)
class EventContext:
    producer: str
    correlation_id: str
    idempotency_key: str | None = None


def compute_fingerprint(alert_name: str, labels: dict[str, str]) -> str:
    label_pairs = ",".join(f"{key}={labels[key]}" for key in sorted(labels))
    raw = f"{alert_name}|{label_pairs}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upsert_alert(
    session: Session,
    payload: AlertmanagerAlert,
    receiver: str | None,
    event_context: EventContext | None = None,
) -> tuple[Alert, bool]:
    alert_name = payload.labels.get("alertname", "unknown")
    source = payload.labels.get("source") or receiver or "unknown"
    severity = payload.labels.get("severity", "info")
    fingerprint = compute_fingerprint(alert_name, payload.labels)

    existing = session.scalars(select(Alert).where(Alert.fingerprint == fingerprint)).one_or_none()
    if existing:
        existing.received_at = datetime.now(UTC)
        existing.status = payload.status
        existing.ends_at = payload.ends_at
        existing.annotations = payload.annotations
        if event_context:
            enqueue_alert_event(session, "alert.received", existing, event_context, extra={"deduplicated": True})
        session.commit()
        session.refresh(existing)
        return existing, True

    alert = Alert(
        source=source,
        alert_name=alert_name,
        fingerprint=fingerprint,
        labels=payload.labels,
        annotations=payload.annotations,
        severity=severity,
        status=payload.status,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    session.add(alert)
    session.flush()
    if event_context:
        enqueue_alert_event(session, "alert.received", alert, event_context, extra={"deduplicated": False})
    session.commit()
    session.refresh(alert)
    return alert, False


def should_promote(alert: Alert) -> bool:
    return (
        alert.status == AlertStatus.firing
        and alert.severity == "critical"
        and alert.source == "prometheus"
        and not alert.incident_id
    )


async def promote_to_incident(alert: Alert, correlation_id: str) -> str:
    service_name = alert.labels.get("service") or alert.labels.get("job") or "unknown-service"
    summary = alert.annotations.get("summary") or alert.alert_name
    description = alert.annotations.get("description") or summary
    payload = {
        "title": f"{alert.alert_name} on {service_name}",
        "description": description,
        "severity": "P1",
        "service_name": service_name,
        "alert_ids": [alert.id],
    }
    headers = {
        "X-API-Key": settings.internal_api_key,
        "X-Correlation-ID": correlation_id,
        "X-Actor": settings.service_name,
        "Idempotency-Key": f"alert:{alert.fingerprint}",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{settings.incidents_service_url}/incidents", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["id"]


def link_incident(
    session: Session,
    alert: Alert,
    incident_id: str,
    event_context: EventContext | None = None,
) -> Alert:
    alert.incident_id = incident_id
    if event_context:
        enqueue_alert_event(
            session,
            "alert.promoted_to_incident",
            alert,
            event_context,
            extra={"incident_id": incident_id},
        )
    session.commit()
    session.refresh(alert)
    return alert


def get_alert_or_404(session: Session, alert_id: str) -> Alert:
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


def suppress_alert(
    session: Session,
    alert: Alert,
    payload: SuppressAlertRequest,
    event_context: EventContext | None = None,
) -> Alert:
    alert.status = AlertStatus.suppressed
    alert.suppression_until = datetime.now(UTC) + timedelta(minutes=payload.duration_minutes)
    alert.suppression_reason = payload.reason
    if event_context:
        enqueue_alert_event(
            session,
            "alert.suppressed",
            alert,
            event_context,
            extra={"duration_minutes": payload.duration_minutes, "reason": payload.reason},
        )
    session.commit()
    session.refresh(alert)
    return alert


def enqueue_alert_event(
    session: Session,
    event_type: str,
    alert: Alert,
    event_context: EventContext,
    *,
    extra: dict | None = None,
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        producer=event_context.producer,
        correlation_id=event_context.correlation_id,
        idempotency_key=event_context.idempotency_key,
        payload=alert_event_payload(alert, extra=extra),
    )
    session.add(event)
    return event


def alert_event_payload(alert: Alert, *, extra: dict | None = None) -> dict:
    payload = {
        "alert_id": alert.id,
        "source": alert.source,
        "alert_name": alert.alert_name,
        "fingerprint": alert.fingerprint,
        "severity": alert.severity,
        "status": alert.status.value,
        "incident_id": alert.incident_id,
        "labels": alert.labels,
    }
    if extra:
        payload.update(extra)
    return payload
