"""M39 ESG Control Service — preventive, detective, and corrective controls."""

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
        action=action, entity_type="ESGControl", entity_id=entity_id,
        actor_id=None, outcome="success", detail=detail,
        event_metadata={"organization_id": organization_id},
    ))


async def create_control(
    organization_id: str,
    control_name: str,
    control_type: str,
    session: AsyncSession,
    owner_user_id: str | None = None,
    frequency: str = "ANNUAL",
    evidence_required: bool = False,
) -> dict:
    from infrastructure.persistence.models.operating_system import ESGControlModel
    now = datetime.now(UTC)
    ctrl = ESGControlModel(
        id=str(uuid.uuid4()), status="Active", version=1, created_at=now, updated_at=now,
        organization_id=organization_id, control_name=control_name, control_type=control_type,
        owner_user_id=owner_user_id, frequency=frequency, evidence_required=evidence_required,
        effectiveness_status="NOT_TESTED",
    )
    session.add(ctrl)
    await session.flush()
    await _log_audit(session, "control.created", ctrl.id, organization_id,
                     detail=f"name={control_name} type={control_type}")
    from application.operating_system.metrics import os_counters
    os_counters.record_control_created()
    return _to_dict(ctrl)


async def list_controls(
    organization_id: str, session: AsyncSession,
    control_type: str | None = None, effectiveness_status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ESGControlModel
    stmt = select(ESGControlModel).where(ESGControlModel.organization_id == organization_id)
    if control_type:
        stmt = stmt.where(ESGControlModel.control_type == control_type)
    if effectiveness_status:
        stmt = stmt.where(ESGControlModel.effectiveness_status == effectiveness_status)
    stmt = stmt.order_by(ESGControlModel.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def get_control(
    organization_id: str, control_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGControlModel
    stmt = select(ESGControlModel).where(
        ESGControlModel.organization_id == organization_id,
        ESGControlModel.id == control_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def update_control(
    organization_id: str, control_id: str, session: AsyncSession, **fields
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGControlModel
    stmt = select(ESGControlModel).where(
        ESGControlModel.organization_id == organization_id,
        ESGControlModel.id == control_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    action = "control.deleted" if fields.get("status") == "Deleted" else "control.updated"
    await _log_audit(session, action, row.id, organization_id)
    return _to_dict(row)


def _to_dict(c) -> dict:
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "control_name": c.control_name,
        "control_type": c.control_type,
        "owner_user_id": c.owner_user_id,
        "frequency": c.frequency,
        "evidence_required": c.evidence_required,
        "effectiveness_status": c.effectiveness_status,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }
