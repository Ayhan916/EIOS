"""M39 ESG Action Service — unified action inbox.

Ingests actions from any EIOS module:
  FINDING | RISK | RECOMMENDATION | SURVEILLANCE_SIGNAL
  | COMPLIANCE_GAP | DUE_DILIGENCE | NETWORK_EXPOSURE | MANUAL
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.operating_system.metrics import os_counters


async def _log_audit(
    session: AsyncSession, action: str, entity_id: str, organization_id: str, detail: str = ""
) -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel

    evt = AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        action=action,
        entity_type="ESGAction",
        entity_id=entity_id,
        actor_id=None,
        outcome="success",
        detail=detail,
        event_metadata={"organization_id": organization_id},
    )
    session.add(evt)


async def create_action(
    organization_id: str,
    title: str,
    session: AsyncSession,
    description: str = "",
    source_type: str = "MANUAL",
    source_id: str | None = None,
    owner_user_id: str | None = None,
    due_date: datetime | None = None,
    priority: str = "MEDIUM",
    linked_objectives: list[str] | None = None,
) -> dict:
    from infrastructure.persistence.models.operating_system import ESGActionModel

    now = datetime.now(UTC)
    action = ESGActionModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        title=title,
        description=description,
        source_type=source_type,
        source_id=source_id,
        owner_user_id=owner_user_id,
        due_date=due_date,
        action_status="OPEN",
        priority=priority,
        linked_objectives=linked_objectives or [],
    )
    session.add(action)
    await session.flush()
    os_counters.record_action_created()
    await _log_audit(
        session,
        "action.assigned",
        action.id,
        organization_id,
        detail=f"source={source_type} priority={priority}",
    )
    return _to_dict(action)


async def list_actions(
    organization_id: str,
    session: AsyncSession,
    action_status: str | None = None,
    priority: str | None = None,
    owner_user_id: str | None = None,
    source_type: str | None = None,
    overdue_only: bool = False,
    limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ESGActionModel

    stmt = select(ESGActionModel).where(ESGActionModel.organization_id == organization_id)
    if action_status:
        stmt = stmt.where(ESGActionModel.action_status == action_status)
    if priority:
        stmt = stmt.where(ESGActionModel.priority == priority)
    if owner_user_id:
        stmt = stmt.where(ESGActionModel.owner_user_id == owner_user_id)
    if source_type:
        stmt = stmt.where(ESGActionModel.source_type == source_type)
    if overdue_only:
        now = datetime.now(UTC)
        stmt = stmt.where(
            ESGActionModel.due_date < now,
            ESGActionModel.action_status.in_(["OPEN", "IN_PROGRESS", "BLOCKED"]),
        )
    stmt = stmt.order_by(ESGActionModel.due_date.asc().nulls_last()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def get_action(organization_id: str, action_id: str, session: AsyncSession) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGActionModel

    stmt = select(ESGActionModel).where(
        ESGActionModel.organization_id == organization_id,
        ESGActionModel.id == action_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def update_action(
    organization_id: str,
    action_id: str,
    session: AsyncSession,
    actor_id: str | None = None,
    **fields,
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGActionModel

    stmt = select(ESGActionModel).where(
        ESGActionModel.organization_id == organization_id,
        ESGActionModel.id == action_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    audit_action = "action.escalated" if fields.get("priority") == "CRITICAL" else "action.assigned"
    await _log_audit(session, audit_action, row.id, organization_id)
    if fields.get("priority") == "CRITICAL":
        os_counters.record_escalation()
    return _to_dict(row)


async def ingest_from_module(
    organization_id: str,
    source_type: str,
    source_id: str,
    title: str,
    priority: str,
    session: AsyncSession,
    due_date: datetime | None = None,
    description: str = "",
) -> dict:
    """Create an ESGAction from a cross-module event (finding, risk, signal, etc.)."""
    return await create_action(
        organization_id=organization_id,
        title=title,
        description=description,
        source_type=source_type,
        source_id=source_id,
        priority=priority,
        due_date=due_date,
        session=session,
    )


async def ingest_from_module_idempotent(
    organization_id: str,
    source_type: str,
    source_id: str,
    title: str,
    priority: str,
    session: AsyncSession,
    due_date: datetime | None = None,
    description: str = "",
) -> dict | None:
    """Create an ESGAction from a cross-module event, no-op if one already exists for this source."""
    from infrastructure.persistence.models.operating_system import ESGActionModel

    existing_stmt = (
        select(ESGActionModel)
        .where(
            ESGActionModel.organization_id == organization_id,
            ESGActionModel.source_type == source_type,
            ESGActionModel.source_id == source_id,
        )
        .limit(1)
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        return None
    return await create_action(
        organization_id=organization_id,
        title=title,
        description=description,
        source_type=source_type,
        source_id=source_id,
        priority=priority,
        due_date=due_date,
        session=session,
    )


def _to_dict(a) -> dict:
    return {
        "id": a.id,
        "organization_id": a.organization_id,
        "title": a.title,
        "description": a.description,
        "source_type": a.source_type,
        "source_id": a.source_id,
        "owner_user_id": a.owner_user_id,
        "due_date": a.due_date,
        "action_status": a.action_status,
        "priority": a.priority,
        "linked_objectives": a.linked_objectives,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }
