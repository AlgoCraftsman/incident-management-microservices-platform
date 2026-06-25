from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import IncidentStatus, Severity


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    severity: Severity
    service_name: str | None = Field(default=None, max_length=100)
    assignee_id: str | None = Field(default=None, max_length=100)
    alert_ids: list[str] = Field(default_factory=list)


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    severity: Severity | None = None
    status: IncidentStatus | None = None
    assignee_id: str | None = Field(default=None, max_length=100)


class CommentCreate(BaseModel):
    message: str = Field(min_length=1)
    actor: str | None = Field(default=None, max_length=100)


class TimelineEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str
    event_type: str
    previous_status: str | None
    new_status: str | None
    actor: str | None
    message: str | None
    event_metadata: dict[str, Any]
    created_at: datetime


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None
    severity: Severity
    status: IncidentStatus
    service_name: str | None
    assignee_id: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    alert_ids: list[str]


class IncidentDetail(IncidentRead):
    timeline_events: list[TimelineEventRead] = Field(default_factory=list)
