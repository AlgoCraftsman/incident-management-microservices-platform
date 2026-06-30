from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


def uuid_str() -> str:
    return str(uuid.uuid4())


class ComponentStatus(str, enum.Enum):
    operational = "operational"
    degraded = "degraded"
    partial_outage = "partial_outage"
    major_outage = "major_outage"


class Component(Base):
    __tablename__ = "components"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    component_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    status: Mapped[ComponentStatus] = mapped_column(
        Enum(ComponentStatus, name="component_status"),
        nullable=False,
        default=ComponentStatus.operational,
    )
    incident_id: Mapped[str | None] = mapped_column(String(36), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)


class StatusUpdate(Base):
    __tablename__ = "status_updates"
    __table_args__ = (UniqueConstraint("source_event_id", name="uq_status_updates_source_event_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_event_id: Mapped[str | None] = mapped_column(String(36), index=True)
    component_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[ComponentStatus] = mapped_column(Enum(ComponentStatus, name="component_status"), nullable=False)
    incident_id: Mapped[str | None] = mapped_column(String(36), index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    posted_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    stream_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
