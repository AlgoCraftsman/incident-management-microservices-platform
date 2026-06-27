from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Component, StatusUpdate
from app.schemas import (
    AutoStatusUpdate,
    ComponentCreate,
    ComponentRead,
    PublicStatus,
    StatusUpdateCreate,
    StatusUpdateRead,
)
from app.services import apply_auto_update, create_component, post_status_update

router = APIRouter(tags=["status"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/status", response_model=PublicStatus)
def public_status(session: SessionDep) -> PublicStatus:
    components = list(session.scalars(select(Component).order_by(Component.component_name.asc())).all())
    return PublicStatus(components=components)


@router.get("/status/history", response_model=list[StatusUpdateRead])
def history(
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[StatusUpdate]:
    stmt = (
        select(StatusUpdate)
        .where(StatusUpdate.is_public.is_(True))
        .order_by(StatusUpdate.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt).all())


@router.get("/components", response_model=list[ComponentRead])
def list_components(session: SessionDep) -> list[Component]:
    return list(session.scalars(select(Component).order_by(Component.component_name.asc())).all())


@router.post("/components", response_model=ComponentRead, status_code=status.HTTP_201_CREATED)
def create(payload: ComponentCreate, session: SessionDep) -> Component:
    return create_component(session, payload)


@router.post("/updates", response_model=list[StatusUpdateRead], status_code=status.HTTP_201_CREATED)
def post_update(payload: StatusUpdateCreate, session: SessionDep) -> list[StatusUpdate]:
    return post_status_update(session, payload)


@router.get("/updates", response_model=list[StatusUpdateRead])
def list_updates(
    session: SessionDep,
    component: str | None = None,
    since: datetime | None = None,
) -> list[StatusUpdate]:
    stmt = select(StatusUpdate).order_by(StatusUpdate.created_at.desc())
    if component:
        stmt = stmt.where(StatusUpdate.component_name == component)
    if since:
        stmt = stmt.where(StatusUpdate.created_at >= since)
    return list(session.scalars(stmt).all())


@router.post("/updates/auto", response_model=list[StatusUpdateRead], status_code=status.HTTP_201_CREATED)
def auto_update(payload: AutoStatusUpdate, session: SessionDep) -> list[StatusUpdate]:
    return apply_auto_update(session, payload)
