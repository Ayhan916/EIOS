"""M39 ESG Initiative Service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.operating_system.metrics import os_counters


async def _log_audit(session, action, entity_id, organization_id, detail=""):
    from infrastructure.persistence.models.audit_event import AuditEventModel
    session.add(AuditEventModel(
        id=str(uuid.uuid4()), status="Active", version=1,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        action=action, entity_type="ESGInitiative", entity_id=entity_id,
        actor_id=None, outcome="success", detail=detail,
        event_metadata={"organization_id": organization_id},
    ))


async def create_initiative(
    organization_id: str,
    title: str,
    session: AsyncSession,
    description: str = "",
    owner_user_id: str | None = None,
    due_date: datetime | None = None,
    linked_objectives: list | None = None,
    linked_suppliers: list | None = None,
    linked_findings: list | None = None,
    linked_risks: list | None = None,
) -> dict:
    from infrastructure.persistence.models.operating_system import ESGInitiativeModel
    now = datetime.now(UTC)
    init = ESGInitiativeModel(
        id=str(uuid.uuid4()), status="Active", version=1, created_at=now, updated_at=now,
        organization_id=organization_id, title=title, description=description,
        owner_user_id=owner_user_id, initiative_status="PLANNED", due_date=due_date,
        linked_objectives=linked_objectives or [], linked_suppliers=linked_suppliers or [],
        linked_findings=linked_findings or [], linked_risks=linked_risks or [],
    )
    session.add(init)
    await session.flush()
    os_counters.record_initiative_created()
    await _log_audit(session, "initiative.started", init.id, organization_id)
    return _to_dict(init)


async def list_initiatives(
    organization_id: str, session: AsyncSession,
    initiative_status: str | None = None, limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ESGInitiativeModel
    stmt = select(ESGInitiativeModel).where(
        ESGInitiativeModel.organization_id == organization_id
    )
    if initiative_status:
        stmt = stmt.where(ESGInitiativeModel.initiative_status == initiative_status)
    stmt = stmt.order_by(ESGInitiativeModel.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def get_initiative(
    organization_id: str, initiative_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGInitiativeModel
    stmt = select(ESGInitiativeModel).where(
        ESGInitiativeModel.organization_id == organization_id,
        ESGInitiativeModel.id == initiative_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def update_initiative(
    organization_id: str, initiative_id: str, session: AsyncSession, **fields
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGInitiativeModel
    stmt = select(ESGInitiativeModel).where(
        ESGInitiativeModel.organization_id == organization_id,
        ESGInitiativeModel.id == initiative_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    action = "initiative.completed" if fields.get("initiative_status") == "COMPLETED" \
        else "initiative.updated"
    await _log_audit(session, action, row.id, organization_id)
    return _to_dict(row)


def _to_dict(i) -> dict:
    return {
        "id": i.id, "organization_id": i.organization_id, "title": i.title,
        "description": i.description, "owner_user_id": i.owner_user_id,
        "initiative_status": i.initiative_status, "due_date": i.due_date,
        "linked_objectives": i.linked_objectives, "linked_suppliers": i.linked_suppliers,
        "linked_findings": i.linked_findings, "linked_risks": i.linked_risks,
        "created_at": i.created_at, "updated_at": i.updated_at,
    }
