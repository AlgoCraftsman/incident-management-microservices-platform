from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import ComponentStatus


class ComponentCreate(BaseModel):
    component_name: str = Field(min_length=1, max_length=100)
    status: ComponentStatus = ComponentStatus.operational
    message: str | None = None
    is_public: bool = True


class ComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    component_name: str
    status: ComponentStatus
    incident_id: str | None
    message: str | None
    created_at: datetime
    updated_at: datetime


class StatusUpdateCreate(BaseModel):
    component_names: list[str] = Field(min_length=1)
    status: ComponentStatus
    incident_id: str | None = Field(default=None, max_length=36)
    message: str = Field(min_length=1)
    posted_by: str = Field(default="operator", max_length=100)
    is_public: bool = True


class AutoStatusUpdate(BaseModel):
    incident_id: str = Field(min_length=1, max_length=36)
    title: str | None = None
    severity: str
    service_name: str | None = None
    status: str


class StatusUpdateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    component_name: str
    status: ComponentStatus
    incident_id: str | None
    message: str
    posted_by: str
    created_at: datetime
    resolved_at: datetime | None
    is_public: bool


class PublicStatus(BaseModel):
    components: list[ComponentRead]
