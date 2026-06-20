"""M39 ESG Program Service — portfolio-level grouping of objectives and initiatives."""

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
        action=action, entity_type="ESGProgram", entity_id=entity_id,
        actor_id=None, outcome="success", detail=detail,
        event_metadata={"organization_id": organization_id},
    ))


async def create_program(
    organization_id: str,
    title: str,
    session: AsyncSession,
    description: str = "",
    linked_objectives: list | None = None,
    linked_initiatives: list | None = None,
    linked_suppliers: list | None = None,
) -> dict:
    from infrastructure.persistence.models.operating_system import ESGProgramModel
    now = datetime.now(UTC)
    prog = ESGProgramModel(
        id=str(uuid.uuid4()), status="Active", version=1, created_at=now, updated_at=now,
        organization_id=organization_id, title=title, description=description,
        program_status="ACTIVE",
        linked_objectives=linked_objectives or [],
        linked_initiatives=linked_initiatives or [],
        linked_suppliers=linked_suppliers or [],
    )
    session.add(prog)
    await session.flush()
    await _log_audit(session, "program.created", prog.id, organization_id, detail=f"title={title}")
    from application.operating_system.metrics import os_counters
    os_counters.record_program_created()
    return _to_dict(prog)


async def list_programs(
    organization_id: str, session: AsyncSession,
    program_status: str | None = None, limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ESGProgramModel
    stmt = select(ESGProgramModel).where(ESGProgramModel.organization_id == organization_id)
    if program_status:
        stmt = stmt.where(ESGProgramModel.program_status == program_status)
    stmt = stmt.order_by(ESGProgramModel.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def get_program(
    organization_id: str, program_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGProgramModel
    stmt = select(ESGProgramModel).where(
        ESGProgramModel.organization_id == organization_id,
        ESGProgramModel.id == program_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def update_program(
    organization_id: str, program_id: str, session: AsyncSession, **fields
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGProgramModel
    stmt = select(ESGProgramModel).where(
        ESGProgramModel.organization_id == organization_id,
        ESGProgramModel.id == program_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    action = "program.deleted" if fields.get("program_status") == "ARCHIVED" else "program.updated"
    await _log_audit(session, action, row.id, organization_id)
    return _to_dict(row)


def _to_dict(p) -> dict:
    return {
        "id": p.id,
        "organization_id": p.organization_id,
        "title": p.title,
        "description": p.description,
        "program_status": p.program_status,
        "linked_objectives": p.linked_objectives,
        "linked_initiatives": p.linked_initiatives,
        "linked_suppliers": p.linked_suppliers,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }
