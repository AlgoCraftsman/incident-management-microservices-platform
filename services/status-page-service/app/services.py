from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Component, ComponentStatus, ProcessedEvent, StatusUpdate
from app.schemas import AutoStatusUpdate, ComponentCreate, StatusUpdateCreate


def create_component(session: Session, payload: ComponentCreate) -> Component:
    existing = session.scalars(select(Component).where(Component.component_name == payload.component_name)).one_or_none()
    if existing:
        existing.status = payload.status
        existing.message = payload.message
        session.commit()
        session.refresh(existing)
        return existing
    component = Component(
        component_name=payload.component_name,
        status=payload.status,
        message=payload.message,
    )
    session.add(component)
    session.commit()
    session.refresh(component)
    return component


def post_status_update(
    session: Session,
    payload: StatusUpdateCreate,
    source_event_id: str | None = None,
) -> list[StatusUpdate]:
    updates: list[StatusUpdate] = []
    for component_name in payload.component_names:
        component = ensure_component(session, component_name)
        component.status = payload.status
        component.incident_id = payload.incident_id
        component.message = payload.message
        resolved_at = datetime.now(UTC) if payload.status == ComponentStatus.operational else None
        update = StatusUpdate(
            source_event_id=source_event_id,
            component_name=component_name,
            status=payload.status,
            incident_id=payload.incident_id,
            message=payload.message,
            posted_by=payload.posted_by,
            resolved_at=resolved_at,
            is_public=payload.is_public,
        )
        session.add(update)
        updates.append(update)
    session.commit()
    for update in updates:
        session.refresh(update)
    return updates


def apply_auto_update(
    session: Session,
    payload: AutoStatusUpdate,
    source_event_id: str | None = None,
) -> list[StatusUpdate]:
    if source_event_id is not None:
        existing = session.scalars(
            select(StatusUpdate).where(StatusUpdate.source_event_id == source_event_id)
        ).all()
        if existing:
            return existing

    component_name = payload.service_name or "platform"
    status_value = ComponentStatus.operational if payload.status == "resolved" else status_from_severity(payload.severity)
    message = (
        f"Incident {payload.incident_id} resolved; {component_name} is operational"
        if status_value == ComponentStatus.operational
        else f"{payload.title or 'Incident'} is affecting {component_name} (incident {payload.incident_id})"
    )
    return post_status_update(
        session,
        StatusUpdateCreate(
            component_names=[component_name],
            status=status_value,
            incident_id=payload.incident_id,
            message=message,
            posted_by="incident-automation",
            is_public=True,
        ),
        source_event_id=source_event_id,
    )


def auto_update_from_event(raw_event: str | bytes) -> AutoStatusUpdate | None:
    event = parse_event(raw_event)
    if event.get("event_type") not in {"incident.created", "incident.resolved"}:
        return None
    payload = event.get("payload") or {}
    return AutoStatusUpdate(
        incident_id=payload["incident_id"],
        title=payload.get("title"),
        severity=payload.get("severity", "P4"),
        service_name=payload.get("service_name"),
        status=payload.get("status", "open"),
    )


def parse_event(raw_event: str | bytes) -> dict[str, Any]:
    return json.loads(raw_event.decode("utf-8") if isinstance(raw_event, bytes) else raw_event)


def already_processed_event(session: Session, event_id: str) -> bool:
    return session.get(ProcessedEvent, event_id) is not None


def record_processed_event(
    session: Session,
    *,
    event: dict[str, Any],
    stream_id: str,
    status_value: str,
    error: str | None = None,
) -> ProcessedEvent:
    existing = session.get(ProcessedEvent, event["event_id"])
    if existing is not None:
        return existing
    processed = ProcessedEvent(
        event_id=event["event_id"],
        stream_id=stream_id,
        event_type=event.get("event_type", "unknown"),
        status=status_value,
        error=error[:1000] if error else None,
    )
    session.add(processed)
    session.commit()
    session.refresh(processed)
    return processed


def status_from_severity(severity: str) -> ComponentStatus:
    if severity == "P1":
        return ComponentStatus.major_outage
    if severity == "P2":
        return ComponentStatus.partial_outage
    return ComponentStatus.degraded


def ensure_component(session: Session, component_name: str) -> Component:
    component = session.scalars(select(Component).where(Component.component_name == component_name)).one_or_none()
    if component is not None:
        return component
    component = Component(component_name=component_name, status=ComponentStatus.operational)
    session.add(component)
    session.flush()
    return component
