from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import AlertStatus


class AlertmanagerAlert(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: AlertStatus = AlertStatus.firing
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)
    starts_at: datetime | None = Field(default=None, alias="startsAt")
    ends_at: datetime | None = Field(default=None, alias="endsAt")


class AlertmanagerWebhook(BaseModel):
    receiver: str | None = None
    status: str | None = None
    alerts: list[AlertmanagerAlert] = Field(default_factory=list)


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    alert_name: str
    fingerprint: str
    labels: dict[str, Any]
    annotations: dict[str, Any]
    severity: str
    status: AlertStatus
    incident_id: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    received_at: datetime
    updated_at: datetime
    suppression_until: datetime | None
    suppression_reason: str | None


class WebhookResult(BaseModel):
    accepted: int
    deduplicated: int
    promoted: int
    alerts: list[AlertRead]


class SuppressAlertRequest(BaseModel):
    duration_minutes: int = Field(gt=0, le=1440)
    reason: str = Field(min_length=1)

