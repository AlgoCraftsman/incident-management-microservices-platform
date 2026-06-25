from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


def uuid_str() -> str:
    return str(uuid.uuid4())


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class AlertStatus(str, enum.Enum):
    firing = "firing"
    resolved = "resolved"
    suppressed = "suppressed"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    alert_name: Mapped[str] = mapped_column(String(255), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    labels: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    annotations: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"),
        nullable=False,
        default=AlertStatus.firing,
    )
    incident_id: Mapped[str | None] = mapped_column(String(36), index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
    )
    suppression_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suppression_reason: Mapped[str | None] = mapped_column(Text)


Index("ix_alerts_status_severity", Alert.status, Alert.severity)

