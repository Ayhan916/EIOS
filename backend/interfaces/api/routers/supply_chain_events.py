"""Supply Chain Event Bus Router — M5

Endpoints:
  GET  /supply-chain/events             — paginated event log (consumed events)
  GET  /supply-chain/events/{id}        — single event log entry
  GET  /supply-chain/outbox             — transactional outbox queue status
  POST /supply-chain/outbox/{id}/retry  — manually reset FAILED entry to PENDING
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.supply_chain.event_log import EventLogService
from domain.user import User
from interfaces.api.deps import get_current_user, get_db, require_analyst, scope_gate
from interfaces.api.schemas.supply_chain_event import (
    EventLogListResponse,
    EventLogResponse,
    EventOutboxListResponse,
    EventOutboxResponse,
)

router = APIRouter(
    prefix="/supply-chain",
    tags=["Supply Chain Event Bus"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("supply_chain:read", "supply_chain:write")),
    ],
)


@router.get("/events", response_model=EventLogListResponse)
async def list_events(
    event_type: str | None = Query(default=None),
    aggregate_type: str | None = Query(default=None),
    aggregate_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventLogListResponse:
    svc = EventLogService(db)
    items, total = await svc.list_for_org(
        organization_id=current_user.organization_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        limit=limit,
        offset=offset,
    )
    return EventLogListResponse(
        items=[EventLogResponse.from_model(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/events/{log_id}", response_model=EventLogResponse)
async def get_event(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventLogResponse:
    svc = EventLogService(db)
    model = await svc.get(current_user.organization_id, log_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Event log entry not found")
    return EventLogResponse.from_model(model)


@router.get("/outbox", response_model=EventOutboxListResponse)
async def list_outbox(
    outbox_status: str | None = Query(default=None, description="PENDING | PUBLISHED | FAILED"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventOutboxListResponse:
    svc = EventLogService(db)
    items, total = await svc.list_outbox(
        organization_id=current_user.organization_id,
        outbox_status=outbox_status,
        limit=limit,
        offset=offset,
    )
    return EventOutboxListResponse(
        items=[EventOutboxResponse.from_model(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/outbox/{entry_id}/retry",
    response_model=EventOutboxResponse,
    dependencies=[Depends(require_analyst)],
)
async def retry_outbox_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventOutboxResponse:
    svc = EventLogService(db)
    entry = await svc.retry_outbox_entry(current_user.organization_id, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Outbox entry not found or not FAILED")
    return EventOutboxResponse.from_model(entry)
