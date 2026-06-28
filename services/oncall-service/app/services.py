from __future__ import annotations

import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.delivery import deliver_notification
from app.models import Notification, NotificationChannel, NotificationStatus, RotationType, Schedule, ScheduleOverride
from app.schemas import NotifyRequest, ScheduleCreate, ScheduleUpdate
from app.settings import settings

MAX_CHANNEL_ATTEMPTS = 3


def create_schedule(session: Session, payload: ScheduleCreate) -> Schedule:
    schedule = Schedule(**payload.model_dump(mode="json"))
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


def update_schedule(session: Session, schedule: Schedule, payload: ScheduleUpdate) -> Schedule:
    changes = payload.model_dump(exclude_unset=True, mode="json")
    for field, value in changes.items():
        setattr(schedule, field, value)
    session.commit()
    session.refresh(schedule)
    return schedule


def get_schedule_or_404(session: Session, schedule_id: str) -> Schedule:
    schedule = session.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return schedule


def get_default_schedule(session: Session) -> Schedule:
    schedule = session.scalars(select(Schedule).order_by(Schedule.created_at.asc()).limit(1)).one_or_none()
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No on-call schedule exists")
    return schedule


def get_current_oncall(session: Session, schedule: Schedule, now: datetime | None = None) -> dict:
    members = schedule.members
    if not members:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Schedule has no members")

    current_time = now or datetime.now(UTC)
    active_override = session.scalars(
        select(ScheduleOverride)
        .where(ScheduleOverride.schedule_id == schedule.id, ScheduleOverride.until > current_time)
        .order_by(ScheduleOverride.created_at.desc())
        .limit(1)
    ).one_or_none()
    if active_override:
        return _member_by_user_id(members, active_override.user_id)

    tz = ZoneInfo(schedule.timezone)
    created = schedule.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    elapsed = current_time.astimezone(tz).timestamp() - created.astimezone(tz).timestamp()
    period_seconds = 7 * 24 * 3600 if schedule.rotation_type == RotationType.weekly else 24 * 3600
    index = int(max(elapsed, 0) / period_seconds) % len(members)
    return members[index]


def create_override(session: Session, schedule: Schedule, user_id: str, until: datetime) -> ScheduleOverride:
    _member_by_user_id(schedule.members, user_id)
    override = ScheduleOverride(schedule_id=schedule.id, user_id=user_id, until=until)
    session.add(override)
    session.commit()
    session.refresh(override)
    return override


def dispatch_notification(session: Session, payload: NotifyRequest) -> Notification:
    schedule = get_schedule_or_404(session, payload.schedule_id) if payload.schedule_id else get_default_schedule(session)
    member = get_current_oncall(session, schedule)
    channel = choose_channel(member)
    message_payload = build_message_payload(payload, member)
    delivery = deliver_notification(
        channel=channel,
        member=member,
        message_payload=message_payload,
        settings=settings,
    )
    notification = Notification(
        incident_id=payload.incident_id,
        schedule_id=schedule.id,
        user_id=member["user_id"],
        channel=channel,
        status=NotificationStatus.sent if delivery.success else NotificationStatus.failed,
        sent_at=datetime.now(UTC) if delivery.success else None,
        attempts=1,
        payload={**message_payload, "delivery": {"provider": delivery.provider, "detail": delivery.detail}},
        last_error=None if delivery.success else delivery.detail,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def retry_notification(session: Session, notification: Notification) -> Notification:
    if notification.status == NotificationStatus.acknowledged:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Acknowledged notifications cannot be retried")
    if notification.attempts >= MAX_CHANNEL_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notification retry limit reached")

    member = notification.payload.get("target") or {"user_id": notification.user_id}
    message_payload = {key: value for key, value in notification.payload.items() if key != "delivery"}
    delivery = deliver_notification(
        channel=notification.channel,
        member=member,
        message_payload=message_payload,
        settings=settings,
    )
    notification.attempts += 1
    notification.status = NotificationStatus.sent if delivery.success else NotificationStatus.failed
    notification.sent_at = datetime.now(UTC) if delivery.success else notification.sent_at
    notification.payload = {**message_payload, "delivery": {"provider": delivery.provider, "detail": delivery.detail}}
    notification.last_error = None if delivery.success else delivery.detail
    session.commit()
    session.refresh(notification)
    return notification


async def acknowledge_notification(session: Session, notification: Notification) -> tuple[Notification, bool]:
    notification.status = NotificationStatus.acknowledged
    notification.acknowledged_at = datetime.now(UTC)
    session.commit()
    session.refresh(notification)

    acknowledged = False
    headers = {
        "X-API-Key": settings.internal_api_key,
        "X-Actor": settings.service_name,
        "Idempotency-Key": f"notification:{notification.id}",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.incidents_service_url}/incidents/{notification.incident_id}/acknowledge",
                headers=headers,
            )
        acknowledged = response.status_code in {200, 201}
    except httpx.HTTPError:
        acknowledged = False
    return notification, acknowledged


def notification_from_incident_event(raw_event: str | bytes) -> NotifyRequest | None:
    event = json.loads(raw_event.decode("utf-8") if isinstance(raw_event, bytes) else raw_event)
    if event.get("event_type") != "incident.created":
        return None
    payload = event.get("payload") or {}
    return NotifyRequest(
        incident_id=payload["incident_id"],
        title=payload.get("title"),
        severity=payload.get("severity"),
        service_name=payload.get("service_name"),
    )


def choose_channel(member: dict) -> NotificationChannel:
    if member.get("slack_id"):
        return NotificationChannel.slack
    if member.get("email"):
        return NotificationChannel.email
    if member.get("phone"):
        return NotificationChannel.sms
    return NotificationChannel.webhook


def build_message_payload(payload: NotifyRequest, member: dict) -> dict:
    return {
        "incident_id": payload.incident_id,
        "title": payload.title,
        "severity": payload.severity,
        "service_name": payload.service_name,
        "target": member,
        "message": f"Incident {payload.incident_id} requires acknowledgement",
    }


def _member_by_user_id(members: list[dict], user_id: str) -> dict:
    for member in members:
        if member.get("user_id") == user_id:
            return member
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule member not found")
