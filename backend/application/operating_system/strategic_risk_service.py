"""M39 Strategic Risk Service — organization-wide ESG risk register."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_strategic_risk(
    organization_id: str,
    title: str,
    category: str,
    session: AsyncSession,
    description: str = "",
    risk_level: str = "MEDIUM",
    probability: str = "MEDIUM",
    impact: str = "MEDIUM",
    owner_user_id: str | None = None,
    linked_suppliers: list | None = None,
    linked_objectives: list | None = None,
    linked_initiatives: list | None = None,
    linked_compliance_programs: list | None = None,
) -> dict:
    from infrastructure.persistence.models.operating_system import StrategicRiskModel

    now = datetime.now(UTC)
    risk = StrategicRiskModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        title=title,
        description=description,
        category=category,
        risk_level=risk_level,
        probability=probability,
        impact=impact,
        risk_status="IDENTIFIED",
        owner_user_id=owner_user_id,
        linked_suppliers=linked_suppliers or [],
        linked_objectives=linked_objectives or [],
        linked_initiatives=linked_initiatives or [],
        linked_compliance_programs=linked_compliance_programs or [],
    )
    session.add(risk)
    await session.flush()
    return _to_dict(risk)


async def list_strategic_risks(
    organization_id: str,
    session: AsyncSession,
    risk_level: str | None = None,
    risk_status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import StrategicRiskModel

    stmt = select(StrategicRiskModel).where(StrategicRiskModel.organization_id == organization_id)
    if risk_level:
        stmt = stmt.where(StrategicRiskModel.risk_level == risk_level)
    if risk_status:
        stmt = stmt.where(StrategicRiskModel.risk_status == risk_status)
    stmt = stmt.order_by(StrategicRiskModel.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def get_strategic_risk(
    organization_id: str, risk_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import StrategicRiskModel

    stmt = select(StrategicRiskModel).where(
        StrategicRiskModel.organization_id == organization_id,
        StrategicRiskModel.id == risk_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def update_strategic_risk(
    organization_id: str, risk_id: str, session: AsyncSession, **fields
) -> dict | None:
    from infrastructure.persistence.models.operating_system import StrategicRiskModel

    stmt = select(StrategicRiskModel).where(
        StrategicRiskModel.organization_id == organization_id,
        StrategicRiskModel.id == risk_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    return _to_dict(row)


def _to_dict(r) -> dict:
    return {
        "id": r.id,
        "organization_id": r.organization_id,
        "title": r.title,
        "description": r.description,
        "category": r.category,
        "risk_level": r.risk_level,
        "probability": r.probability,
        "impact": r.impact,
        "risk_status": r.risk_status,
        "owner_user_id": r.owner_user_id,
        "linked_suppliers": r.linked_suppliers,
        "linked_objectives": r.linked_objectives,
        "linked_initiatives": r.linked_initiatives,
        "linked_compliance_programs": r.linked_compliance_programs,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }
