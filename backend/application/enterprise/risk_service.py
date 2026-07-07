"""Enterprise risk register — cross-organizational strategic risks."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.models.enterprise import EnterpriseRiskModel


async def create_enterprise_risk(
    enterprise_id: str,
    title: str,
    description: str | None,
    severity: str,
    esg_category: str | None,
    owner_user_id: str | None,
    mitigation_plan: str | None,
    linked_region_ids: list[str],
    linked_business_unit_ids: list[str],
    linked_organization_ids: list[str],
    linked_supplier_ids: list[str],
    actor_id: str,
    session: AsyncSession,
) -> EnterpriseRiskModel:
    now = datetime.now(UTC)
    risk = EnterpriseRiskModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        title=title,
        description=description,
        severity=severity,
        risk_status="open",
        esg_category=esg_category,
        owner_user_id=owner_user_id,
        mitigation_plan=mitigation_plan,
        linked_region_ids=linked_region_ids,
        linked_business_unit_ids=linked_business_unit_ids,
        linked_organization_ids=linked_organization_ids,
        linked_supplier_ids=linked_supplier_ids,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(risk)
    await session.flush()
    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action="enterprise_risk.created",
            entity_type="EnterpriseRisk",
            entity_id=risk.id,
            actor_id=actor_id,
            outcome="success",
            detail=f"Enterprise risk '{title}' ({severity}) created",
            event_metadata={"enterprise_id": enterprise_id, "esg_category": esg_category},
        )
    )
    return risk


async def list_enterprise_risks(
    enterprise_id: str,
    severity: str | None,
    status: str | None,
    session: AsyncSession,
) -> list[EnterpriseRiskModel]:
    stmt = select(EnterpriseRiskModel).where(EnterpriseRiskModel.enterprise_id == enterprise_id)
    if severity:
        stmt = stmt.where(EnterpriseRiskModel.severity == severity)
    if status:
        stmt = stmt.where(EnterpriseRiskModel.risk_status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_enterprise_risk(risk_id: str, session: AsyncSession) -> EnterpriseRiskModel | None:
    result = await session.execute(
        select(EnterpriseRiskModel).where(EnterpriseRiskModel.id == risk_id)
    )
    return result.scalar_one_or_none()


async def update_enterprise_risk_status(
    risk_id: str,
    new_status: str,
    actor_id: str,
    session: AsyncSession,
) -> EnterpriseRiskModel | None:
    risk = await get_enterprise_risk(risk_id, session)
    if not risk:
        return None
    risk.risk_status = new_status
    risk.updated_at = datetime.now(UTC)
    risk.version += 1
    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            action="enterprise_risk.status_changed",
            entity_type="EnterpriseRisk",
            entity_id=risk_id,
            actor_id=actor_id,
            outcome="success",
            detail=f"Status changed to '{new_status}'",
            event_metadata={"enterprise_id": risk.enterprise_id},
        )
    )
    return risk
