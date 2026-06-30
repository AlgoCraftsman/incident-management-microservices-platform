from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


def uuid_str() -> str:
    return str(uuid.uuid4())


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class RotationType(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"


class NotificationChannel(str, enum.Enum):
    slack = "slack"
    email = "email"
    sms = "sms"
    webhook = "webhook"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    acknowledged = "acknowledged"


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    rotation_type: Mapped[RotationType] = mapped_column(Enum(RotationType, name="rotation_type"), nullable=False)
    members: Mapped[list[dict]] = mapped_column(json_type(), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)

    overrides: Mapped[list["ScheduleOverride"]] = relationship(back_populates="schedule", cascade="all, delete-orphan")


class ScheduleOverride(Base):
    __tablename__ = "schedule_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("schedules.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)

    schedule: Mapped[Schedule] = relationship(back_populates="overrides")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("source_event_id", name="uq_notifications_source_event_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_event_id: Mapped[str | None] = mapped_column(String(36), index=True)
    incident_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    schedule_id: Mapped[str | None] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"),
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        nullable=False,
        default=NotificationStatus.pending,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    stream_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
