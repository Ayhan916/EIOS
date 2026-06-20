"""M39 Governance Calendar Event Service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _log_audit(session, action: str, entity_id: str, organization_id: str, detail: str = "") -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel
    session.add(AuditEventModel(
        id=str(uuid.uuid4()), status="Active", version=1,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        action=action, entity_type="GovernanceCalendarEvent", entity_id=entity_id,
        actor_id=None, outcome="success", detail=detail,
        event_metadata={"organization_id": organization_id},
    ))


async def create_event(
    organization_id: str,
    title: str,
    event_type: str,
    scheduled_at: datetime,
    session: AsyncSession,
    recurrence_rule: str | None = None,
    reminder_days: int = 7,
    linked_entity_type: str | None = None,
    linked_entity_id: str | None = None,
    notes: str = "",
) -> dict:
    from infrastructure.persistence.models.operating_system import GovernanceCalendarEventModel
    now = datetime.now(UTC)
    evt = GovernanceCalendarEventModel(
        id=str(uuid.uuid4()), status="Active", version=1, created_at=now, updated_at=now,
        organization_id=organization_id, title=title, event_type=event_type,
        scheduled_at=scheduled_at, recurrence_rule=recurrence_rule,
        reminder_days=reminder_days, event_status="SCHEDULED",
        linked_entity_type=linked_entity_type, linked_entity_id=linked_entity_id,
        notes=notes,
    )
    session.add(evt)
    await session.flush()
    await _log_audit(session, "calendar.event_created", evt.id, organization_id,
                     detail=f"type={event_type} scheduled_at={scheduled_at.isoformat()}")
    from application.operating_system.metrics import os_counters
    os_counters.record_calendar_event_created()
    return _to_dict(evt)


async def list_events(
    organization_id: str, session: AsyncSession,
    event_type: str | None = None, event_status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import GovernanceCalendarEventModel
    stmt = select(GovernanceCalendarEventModel).where(
        GovernanceCalendarEventModel.organization_id == organization_id
    )
    if event_type:
        stmt = stmt.where(GovernanceCalendarEventModel.event_type == event_type)
    if event_status:
        stmt = stmt.where(GovernanceCalendarEventModel.event_status == event_status)
    stmt = stmt.order_by(GovernanceCalendarEventModel.scheduled_at.asc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def get_event(
    organization_id: str, event_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import GovernanceCalendarEventModel
    stmt = select(GovernanceCalendarEventModel).where(
        GovernanceCalendarEventModel.organization_id == organization_id,
        GovernanceCalendarEventModel.id == event_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def update_event(
    organization_id: str, event_id: str, session: AsyncSession, **fields
) -> dict | None:
    from infrastructure.persistence.models.operating_system import GovernanceCalendarEventModel
    stmt = select(GovernanceCalendarEventModel).where(
        GovernanceCalendarEventModel.organization_id == organization_id,
        GovernanceCalendarEventModel.id == event_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    await _log_audit(session, "calendar.event_updated", row.id, organization_id)
    return _to_dict(row)


async def delete_event(
    organization_id: str, event_id: str, session: AsyncSession
) -> bool:
    from infrastructure.persistence.models.operating_system import GovernanceCalendarEventModel
    stmt = select(GovernanceCalendarEventModel).where(
        GovernanceCalendarEventModel.organization_id == organization_id,
        GovernanceCalendarEventModel.id == event_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return False
    await _log_audit(session, "calendar.event_deleted", row.id, organization_id)
    await session.delete(row)
    await session.flush()
    return True


def _to_dict(e) -> dict:
    return {
        "id": e.id,
        "organization_id": e.organization_id,
        "title": e.title,
        "event_type": e.event_type,
        "scheduled_at": e.scheduled_at,
        "recurrence_rule": e.recurrence_rule,
        "reminder_days": e.reminder_days,
        "event_status": e.event_status,
        "linked_entity_type": e.linked_entity_type,
        "linked_entity_id": e.linked_entity_id,
        "notes": e.notes,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }
