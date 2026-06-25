from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Incident, IncidentStatus, Severity
from app.schemas import CommentCreate, IncidentCreate, IncidentDetail, IncidentRead, IncidentUpdate, TimelineEventRead
from app.services import (
    acknowledge_incident,
    add_comment,
    create_incident,
    get_incident_by_idempotency_key,
    get_incident_or_404,
    has_open_duplicate,
    resolve_incident,
    update_incident,
)
from platform_common.correlation import get_correlation_id
from platform_common.events import EventEnvelope
from platform_common.responses import set_duplicate_warning

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/incidents", tags=["incidents"])


SessionDep = Annotated[Session, Depends(get_session)]
ActorHeader = Annotated[str | None, Header(default=None, alias="X-Actor")]
IdempotencyHeader = Annotated[str | None, Header(default=None, alias="Idempotency-Key")]


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: IncidentCreate,
    request: Request,
    response: Response,
    session: SessionDep,
    actor: ActorHeader = None,
    idempotency_key: IdempotencyHeader = None,
) -> Incident:
    existing = get_incident_by_idempotency_key(session, idempotency_key)
    if existing:
        response.status_code = status.HTTP_200_OK
        return existing
    duplicate = has_open_duplicate(session, payload.service_name)
    incident = create_incident(session, payload, actor, idempotency_key)
    if duplicate:
        set_duplicate_warning(response, f"Another active incident already exists for service {payload.service_name}")
    await publish_incident_event(request, "incident.created", incident, idempotency_key)
    return incident


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    session: SessionDep,
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    return list(session.scalars(stmt).all())


@router.get("/{incident_id}", response_model=IncidentDetail)
def get(incident_id: str, session: SessionDep) -> Incident:
    return get_incident_or_404(session, incident_id, include_timeline=True)


@router.patch("/{incident_id}", response_model=IncidentRead)
async def patch(
    incident_id: str,
    payload: IncidentUpdate,
    request: Request,
    session: SessionDep,
    actor: ActorHeader = None,
    idempotency_key: IdempotencyHeader = None,
) -> Incident:
    incident = get_incident_or_404(session, incident_id)
    updated = update_incident(session, incident, payload, actor)
    event_type = "incident.updated"
    if payload.status is not None:
        event_type = f"incident.{payload.status.value}"
    await publish_incident_event(request, event_type, updated, idempotency_key)
    return updated


@router.post("/{incident_id}/acknowledge", response_model=IncidentRead)
async def acknowledge(
    incident_id: str,
    request: Request,
    session: SessionDep,
    actor: ActorHeader = None,
    idempotency_key: IdempotencyHeader = None,
) -> Incident:
    incident = get_incident_or_404(session, incident_id)
    updated = acknowledge_incident(session, incident, actor)
    await publish_incident_event(request, "incident.acknowledged", updated, idempotency_key)
    return updated


@router.post("/{incident_id}/resolve", response_model=IncidentRead)
async def resolve(
    incident_id: str,
    request: Request,
    session: SessionDep,
    actor: ActorHeader = None,
    idempotency_key: IdempotencyHeader = None,
) -> Incident:
    incident = get_incident_or_404(session, incident_id)
    updated = resolve_incident(session, incident, actor)
    await publish_incident_event(request, "incident.resolved", updated, idempotency_key)
    return updated


@router.get("/{incident_id}/timeline", response_model=list[TimelineEventRead])
def timeline(incident_id: str, session: SessionDep) -> list:
    incident = session.scalars(
        select(Incident)
        .where(Incident.id == incident_id)
        .options(selectinload(Incident.timeline_events))
    ).one_or_none()
    if incident is None:
        get_incident_or_404(session, incident_id)
    return list(incident.timeline_events)


@router.post("/{incident_id}/comments", response_model=TimelineEventRead, status_code=status.HTTP_201_CREATED)
def comment(incident_id: str, payload: CommentCreate, session: SessionDep) -> object:
    incident = get_incident_or_404(session, incident_id)
    return add_comment(session, incident, payload)


async def publish_incident_event(
    request: Request,
    event_type: str,
    incident: Incident,
    idempotency_key: str | None,
) -> None:
    envelope = EventEnvelope.create(
        event_type=event_type,
        producer=request.app.state.service_name,
        correlation_id=get_correlation_id(),
        idempotency_key=idempotency_key,
        payload={
            "incident_id": incident.id,
            "title": incident.title,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "service_name": incident.service_name,
            "assignee_id": incident.assignee_id,
            "alert_ids": incident.alert_ids,
        },
    )
    stream_id = await request.app.state.event_publisher.publish(envelope)
    logger.info("published_event event_type=%s stream_id=%s incident_id=%s", event_type, stream_id, incident.id)
