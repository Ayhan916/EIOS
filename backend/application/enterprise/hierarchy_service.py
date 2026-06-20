"""Enterprise hierarchy management — Enterprise, BusinessUnit, LegalEntity, Region."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.enterprise import (
    BusinessUnitModel,
    EnterpriseModel,
    LegalEntityModel,
    RegionModel,
)
from infrastructure.persistence.models.organization import OrganizationModel


async def _log_audit(
    session,
    action: str,
    actor_id: str | None,
    entity_type: str,
    entity_id: str,
    outcome: str = "success",
    detail: str = "",
    metadata: dict | None = None,
) -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel
    session.add(AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        outcome=outcome,
        detail=detail,
        event_metadata=metadata or {},
    ))


async def create_enterprise(
    name: str,
    description: str | None,
    hq_country: str | None,
    industry: str | None,
    default_data_residency: str,
    default_data_classification: str,
    settings: dict,
    actor_id: str,
    session: AsyncSession,
) -> EnterpriseModel:
    now = datetime.now(UTC)
    enterprise = EnterpriseModel(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        hq_country=hq_country,
        industry=industry,
        default_data_residency=default_data_residency,
        default_data_classification=default_data_classification,
        settings=settings,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(enterprise)
    await session.flush()
    await _log_audit(
        session=session,
        action="enterprise.created",
        actor_id=actor_id,
        entity_type="Enterprise",
        entity_id=enterprise.id,
        outcome="success",
        detail=f"Enterprise '{name}' created",
    )
    return enterprise


async def get_enterprise(enterprise_id: str, session: AsyncSession) -> EnterpriseModel | None:
    result = await session.execute(
        select(EnterpriseModel).where(EnterpriseModel.id == enterprise_id)
    )
    return result.scalar_one_or_none()


async def list_enterprises(session: AsyncSession) -> list[EnterpriseModel]:
    result = await session.execute(
        select(EnterpriseModel).where(EnterpriseModel.is_active.is_(True))
    )
    return list(result.scalars().all())


async def update_enterprise(
    enterprise_id: str,
    updates: dict,
    actor_id: str,
    session: AsyncSession,
) -> EnterpriseModel | None:
    enterprise = await get_enterprise(enterprise_id, session)
    if not enterprise:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(enterprise, key):
            setattr(enterprise, key, value)
    enterprise.updated_at = datetime.now(UTC)
    enterprise.version += 1
    await _log_audit(
        session=session,
        action="enterprise.updated",
        actor_id=actor_id,
        entity_type="Enterprise",
        entity_id=enterprise_id,
        outcome="success",
    )
    return enterprise


async def create_business_unit(
    enterprise_id: str,
    name: str,
    description: str | None,
    region_scope: str | None,
    admin_user_id: str | None,
    actor_id: str,
    session: AsyncSession,
) -> BusinessUnitModel:
    now = datetime.now(UTC)
    bu = BusinessUnitModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        name=name,
        description=description,
        region_scope=region_scope,
        admin_user_id=admin_user_id,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(bu)
    await session.flush()
    await _log_audit(
        session=session,
        action="business_unit.created",
        actor_id=actor_id,
        entity_type="BusinessUnit",
        entity_id=bu.id,
        outcome="success",
        detail=f"Business unit '{name}' created under enterprise {enterprise_id}",
    )
    return bu


async def list_business_units(
    enterprise_id: str, session: AsyncSession
) -> list[BusinessUnitModel]:
    result = await session.execute(
        select(BusinessUnitModel).where(
            BusinessUnitModel.enterprise_id == enterprise_id,
            BusinessUnitModel.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def create_legal_entity(
    enterprise_id: str,
    name: str,
    description: str | None,
    country: str | None,
    registration_number: str | None,
    legal_form: str | None,
    actor_id: str,
    session: AsyncSession,
) -> LegalEntityModel:
    now = datetime.now(UTC)
    le = LegalEntityModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        name=name,
        description=description,
        country=country,
        registration_number=registration_number,
        legal_form=legal_form,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(le)
    await session.flush()
    await _log_audit(
        session=session,
        action="legal_entity.created",
        actor_id=actor_id,
        entity_type="LegalEntity",
        entity_id=le.id,
        outcome="success",
        detail=f"Legal entity '{name}' created",
    )
    return le


async def list_legal_entities(
    enterprise_id: str, session: AsyncSession
) -> list[LegalEntityModel]:
    result = await session.execute(
        select(LegalEntityModel).where(
            LegalEntityModel.enterprise_id == enterprise_id,
            LegalEntityModel.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def create_region(
    enterprise_id: str,
    name: str,
    code: str,
    description: str | None,
    data_residency: str,
    admin_user_id: str | None,
    actor_id: str,
    session: AsyncSession,
) -> RegionModel:
    now = datetime.now(UTC)
    region = RegionModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        name=name,
        code=code,
        description=description,
        data_residency=data_residency,
        admin_user_id=admin_user_id,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(region)
    await session.flush()
    await _log_audit(
        session=session,
        action="region.created",
        actor_id=actor_id,
        entity_type="Region",
        entity_id=region.id,
        outcome="success",
        detail=f"Region '{name}' ({code}) created",
    )
    return region


async def list_regions(enterprise_id: str, session: AsyncSession) -> list[RegionModel]:
    result = await session.execute(
        select(RegionModel).where(
            RegionModel.enterprise_id == enterprise_id,
            RegionModel.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def link_organization(
    enterprise_id: str,
    organization_id: str,
    business_unit_id: str | None,
    legal_entity_id: str | None,
    region_id: str | None,
    data_residency: str | None,
    data_classification: str | None,
    actor_id: str,
    session: AsyncSession,
) -> OrganizationModel | None:
    result = await session.execute(
        select(OrganizationModel).where(OrganizationModel.id == organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        return None
    org.enterprise_id = enterprise_id
    if business_unit_id:
        org.business_unit_id = business_unit_id
    if legal_entity_id:
        org.legal_entity_id = legal_entity_id
    if region_id:
        org.region_id = region_id
    if data_residency:
        org.data_residency = data_residency
    if data_classification:
        org.data_classification = data_classification
    org.updated_at = datetime.now(UTC)
    await _log_audit(
        session=session,
        action="enterprise.org_linked",
        actor_id=actor_id,
        entity_type="Organization",
        entity_id=organization_id,
        outcome="success",
        detail=f"Organization linked to enterprise {enterprise_id}",
        metadata={"enterprise_id": enterprise_id, "business_unit_id": business_unit_id},
    )
    return org
