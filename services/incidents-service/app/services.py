from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import IdempotencyRecord, Incident, IncidentStatus, TimelineEvent
from app.schemas import CommentCreate, IncidentCreate, IncidentUpdate


ACTIVE_STATUSES = {IncidentStatus.open, IncidentStatus.acknowledged}


def get_incident_or_404(session: Session, incident_id: str, *, include_timeline: bool = False) -> Incident:
    stmt: Select[tuple[Incident]] = select(Incident).where(Incident.id == incident_id)
    if include_timeline:
        stmt = stmt.options(selectinload(Incident.timeline_events))
    incident = session.scalars(stmt).one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


def has_open_duplicate(session: Session, service_name: str | None, exclude_id: str | None = None) -> bool:
    if not service_name:
        return False
    stmt = select(Incident.id).where(
        Incident.service_name == service_name,
        Incident.status.in_(ACTIVE_STATUSES),
    )
    if exclude_id:
        stmt = stmt.where(Incident.id != exclude_id)
    return session.scalars(stmt.limit(1)).first() is not None


def get_incident_by_idempotency_key(session: Session, key: str | None) -> Incident | None:
    if not key:
        return None
    record = session.get(IdempotencyRecord, key)
    if record is None or record.resource_type != "incident":
        return None
    return session.get(Incident, record.resource_id)


def create_incident(
    session: Session,
    payload: IncidentCreate,
    actor: str | None = None,
    idempotency_key: str | None = None,
) -> Incident:
    incident = Incident(**payload.model_dump())
    session.add(incident)
    session.flush()
    if idempotency_key:
        session.add(IdempotencyRecord(key=idempotency_key, resource_type="incident", resource_id=incident.id))
    append_timeline(
        session,
        incident,
        event_type="incident.created",
        previous_status=None,
        new_status=incident.status.value,
        actor=actor,
        message=f"Incident created with severity {incident.severity.value}",
        metadata={"severity": incident.severity.value, "service_name": incident.service_name},
    )
    session.commit()
    session.refresh(incident)
    return incident


def update_incident(session: Session, incident: Incident, payload: IncidentUpdate, actor: str | None = None) -> Incident:
    changes = payload.model_dump(exclude_unset=True)
    requested_status = changes.pop("status", None)
    previous_status = incident.status

    for field, value in changes.items():
        setattr(incident, field, value)

    if requested_status is not None:
        transition_status(incident, requested_status)

    event_type = "incident.updated"
    if incident.status != previous_status:
        event_type = f"incident.{incident.status.value}"
    changed_fields = sorted([*changes.keys(), *(("status",) if requested_status else ())])
    append_timeline(
        session,
        incident,
        event_type=event_type,
        previous_status=previous_status.value,
        new_status=incident.status.value,
        actor=actor,
        message="Incident updated",
        metadata={"changed_fields": changed_fields},
    )
    session.commit()
    session.refresh(incident)
    return incident


def acknowledge_incident(session: Session, incident: Incident, actor: str | None = None) -> Incident:
    return update_incident(session, incident, IncidentUpdate(status=IncidentStatus.acknowledged), actor)


def resolve_incident(session: Session, incident: Incident, actor: str | None = None) -> Incident:
    return update_incident(session, incident, IncidentUpdate(status=IncidentStatus.resolved), actor)


def add_comment(session: Session, incident: Incident, payload: CommentCreate) -> TimelineEvent:
    event = append_timeline(
        session,
        incident,
        event_type="incident.comment_added",
        previous_status=incident.status.value,
        new_status=incident.status.value,
        actor=payload.actor,
        message=payload.message,
        metadata={},
    )
    session.commit()
    session.refresh(event)
    return event


def transition_status(incident: Incident, target: IncidentStatus) -> None:
    if incident.status == target:
        return
    if target == IncidentStatus.closed and incident.status != IncidentStatus.resolved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An incident cannot be closed before it is resolved",
        )
    if incident.status == IncidentStatus.closed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A closed incident cannot transition to another state",
        )
    incident.status = target
    if target == IncidentStatus.resolved:
        incident.resolved_at = datetime.now(UTC)


def append_timeline(
    session: Session,
    incident: Incident,
    *,
    event_type: str,
    previous_status: str | None,
    new_status: str | None,
    actor: str | None,
    message: str | None,
    metadata: dict,
) -> TimelineEvent:
    event = TimelineEvent(
        incident_id=incident.id,
        event_type=event_type,
        previous_status=previous_status,
        new_status=new_status,
        actor=actor,
        message=message,
        event_metadata=metadata,
    )
    session.add(event)
    return event
