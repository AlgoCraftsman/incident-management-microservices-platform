from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import NotificationChannel, NotificationStatus, RotationType


class ScheduleMember(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    slack_id: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=40)


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)
    rotation_type: RotationType = RotationType.weekly
    members: list[ScheduleMember] = Field(min_length=1)


class ScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)
    rotation_type: RotationType | None = None
    members: list[ScheduleMember] | None = Field(default=None, min_length=1)


class OverrideCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    until: datetime


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    timezone: str
    rotation_type: RotationType
    members: list[dict[str, Any]]
    created_at: datetime


class ScheduleDetail(ScheduleRead):
    current_oncall: dict[str, Any]


class NotifyRequest(BaseModel):
    incident_id: str = Field(min_length=1, max_length=36)
    schedule_id: str | None = Field(default=None, max_length=36)
    title: str | None = None
    severity: str | None = None
    service_name: str | None = None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str
    schedule_id: str | None
    user_id: str
    channel: NotificationChannel
    status: NotificationStatus
    sent_at: datetime | None
    acknowledged_at: datetime | None
    attempts: int
    payload: dict[str, Any]
    last_error: str | None
    created_at: datetime


class NotificationAckResult(BaseModel):
    notification: NotificationRead
    incident_acknowledged: bool
