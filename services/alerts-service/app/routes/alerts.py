from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Alert, AlertStatus
from app.schemas import AlertRead, AlertmanagerWebhook, SuppressAlertRequest, WebhookResult
from app.services import (
    EventContext,
    get_alert_or_404,
    link_incident,
    promote_to_incident,
    should_promote,
    suppress_alert,
    upsert_alert,
)
from platform_common.correlation import get_correlation_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])

SessionDep = Annotated[Session, Depends(get_session)]
IdempotencyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]


@router.post("/webhook", response_model=WebhookResult)
async def webhook(
    payload: AlertmanagerWebhook,
    request: Request,
    session: SessionDep,
    idempotency_key: IdempotencyHeader = None,
) -> WebhookResult:
    accepted = 0
    deduplicated = 0
    promoted = 0
    results: list[Alert] = []

    for incoming in payload.alerts:
        event_ctx = event_context(request, idempotency_key)
        alert, was_duplicate = upsert_alert(session, incoming, payload.receiver, event_context=event_ctx)
        accepted += 1
        deduplicated += int(was_duplicate)

        if should_promote(alert):
            try:
                incident_id = await promote_to_incident(alert, get_correlation_id())
            except httpx.HTTPStatusError as exc:
                logger.exception("incident_promotion_failed alert_id=%s status=%s", alert.id, exc.response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Incident promotion failed",
                ) from exc
            alert = link_incident(session, alert, incident_id, event_context=event_ctx)
            promoted += 1

        results.append(alert)

    return WebhookResult(accepted=accepted, deduplicated=deduplicated, promoted=promoted, alerts=results)


@router.get("", response_model=list[AlertRead])
def list_alerts(
    session: SessionDep,
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
    source: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.received_at.desc()).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    if source:
        stmt = stmt.where(Alert.source == source)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    return list(session.scalars(stmt).all())


@router.get("/firing", response_model=list[AlertRead])
def firing(session: SessionDep) -> list[Alert]:
    return list(
        session.scalars(
            select(Alert)
            .where(Alert.status == AlertStatus.firing)
            .order_by(Alert.severity.asc(), Alert.received_at.desc())
        ).all()
    )


@router.get("/{alert_id}", response_model=AlertRead)
def get(alert_id: str, session: SessionDep) -> Alert:
    return get_alert_or_404(session, alert_id)


@router.post("/{alert_id}/suppress", response_model=AlertRead)
async def suppress(
    alert_id: str,
    payload: SuppressAlertRequest,
    request: Request,
    session: SessionDep,
    idempotency_key: IdempotencyHeader = None,
) -> Alert:
    alert = get_alert_or_404(session, alert_id)
    return suppress_alert(session, alert, payload, event_context=event_context(request, idempotency_key))


def event_context(request: Request, idempotency_key: str | None) -> EventContext:
    return EventContext(
        producer=request.app.state.service_name,
        correlation_id=get_correlation_id(),
        idempotency_key=idempotency_key,
    )
