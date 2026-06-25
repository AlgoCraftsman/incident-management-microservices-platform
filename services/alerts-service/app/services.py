from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, AlertStatus
from app.schemas import AlertmanagerAlert, SuppressAlertRequest
from app.settings import settings


def compute_fingerprint(alert_name: str, labels: dict[str, str]) -> str:
    label_pairs = ",".join(f"{key}={labels[key]}" for key in sorted(labels))
    raw = f"{alert_name}|{label_pairs}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upsert_alert(session: Session, payload: AlertmanagerAlert, receiver: str | None) -> tuple[Alert, bool]:
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


def link_incident(session: Session, alert: Alert, incident_id: str) -> Alert:
    alert.incident_id = incident_id
    session.commit()
    session.refresh(alert)
    return alert


def get_alert_or_404(session: Session, alert_id: str) -> Alert:
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


def suppress_alert(session: Session, alert: Alert, payload: SuppressAlertRequest) -> Alert:
    alert.status = AlertStatus.suppressed
    alert.suppression_until = datetime.now(UTC) + timedelta(minutes=payload.duration_minutes)
    alert.suppression_reason = payload.reason
    session.commit()
    session.refresh(alert)
    return alert

