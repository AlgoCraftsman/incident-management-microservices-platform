from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Notification, NotificationStatus, Schedule
from app.schemas import (
    NotificationAckResult,
    NotificationRead,
    NotifyRequest,
    OverrideCreate,
    ScheduleCreate,
    ScheduleDetail,
    ScheduleRead,
    ScheduleUpdate,
)
from app.services import (
    acknowledge_notification,
    create_override,
    create_schedule,
    dispatch_notification,
    get_current_oncall,
    get_default_schedule,
    get_schedule_or_404,
    retry_notification,
    update_schedule,
)

router = APIRouter(tags=["on-call"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/schedules", response_model=ScheduleDetail, status_code=status.HTTP_201_CREATED)
def create(payload: ScheduleCreate, session: SessionDep) -> ScheduleDetail:
    schedule = create_schedule(session, payload)
    return schedule_detail(session, schedule)


@router.get("/schedules", response_model=list[ScheduleRead])
def list_schedules(session: SessionDep) -> list[Schedule]:
    return list(session.scalars(select(Schedule).order_by(Schedule.created_at.asc())).all())


@router.get("/schedules/{schedule_id}", response_model=ScheduleDetail)
def get(schedule_id: str, session: SessionDep) -> ScheduleDetail:
    schedule = get_schedule_or_404(session, schedule_id)
    return schedule_detail(session, schedule)


@router.patch("/schedules/{schedule_id}", response_model=ScheduleDetail)
def patch(schedule_id: str, payload: ScheduleUpdate, session: SessionDep) -> ScheduleDetail:
    schedule = update_schedule(session, get_schedule_or_404(session, schedule_id), payload)
    return schedule_detail(session, schedule)


@router.get("/schedules/{schedule_id}/current")
def current(schedule_id: str, session: SessionDep) -> dict:
    return get_current_oncall(session, get_schedule_or_404(session, schedule_id))


@router.post("/schedules/{schedule_id}/override", status_code=status.HTTP_201_CREATED)
def override(schedule_id: str, payload: OverrideCreate, session: SessionDep) -> dict:
    schedule = get_schedule_or_404(session, schedule_id)
    created = create_override(session, schedule, payload.user_id, payload.until)
    return {"id": created.id, "schedule_id": schedule.id, "user_id": created.user_id, "until": created.until}


@router.post("/notify", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def notify(payload: NotifyRequest, session: SessionDep) -> Notification:
    if payload.schedule_id is None:
        get_default_schedule(session)
    return dispatch_notification(session, payload)


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    session: SessionDep,
    incident_id: str | None = None,
    status_filter: NotificationStatus | None = Query(default=None, alias="status"),
) -> list[Notification]:
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if incident_id:
        stmt = stmt.where(Notification.incident_id == incident_id)
    if status_filter:
        stmt = stmt.where(Notification.status == status_filter)
    return list(session.scalars(stmt).all())


@router.get("/notifications/{notification_id}", response_model=NotificationRead)
def get_notification(notification_id: str, session: SessionDep) -> Notification:
    notification = session.get(Notification, notification_id)
    if notification is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/notifications/{notification_id}/acknowledge", response_model=NotificationAckResult)
async def acknowledge(notification_id: str, session: SessionDep) -> NotificationAckResult:
    notification = session.get(Notification, notification_id)
    if notification is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    updated, incident_acknowledged = await acknowledge_notification(session, notification)
    return NotificationAckResult(notification=updated, incident_acknowledged=incident_acknowledged)


@router.post("/notifications/{notification_id}/retry", response_model=NotificationRead)
def retry(notification_id: str, session: SessionDep) -> Notification:
    notification = session.get(Notification, notification_id)
    if notification is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return retry_notification(session, notification)


def schedule_detail(session: Session, schedule: Schedule) -> ScheduleDetail:
    return ScheduleDetail(
        id=schedule.id,
        name=schedule.name,
        timezone=schedule.timezone,
        rotation_type=schedule.rotation_type,
        members=schedule.members,
        created_at=schedule.created_at,
        current_oncall=get_current_oncall(session, schedule),
    )
