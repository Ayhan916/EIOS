"""Supplier Digital Twin Service — CRUD and state management."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.supplier_digital_twin import SupplierDigitalTwin
from .health_engine import compute_overall_health, compute_trend

logger = structlog.get_logger(__name__)


async def get_or_create_twin(
    supplier_id: str,
    organization_id: str,
    session: AsyncSession,
) -> SupplierDigitalTwin:
    """Return the twin for this supplier, creating it if it does not exist."""
    from infrastructure.persistence.models.supplier_digital_twin import SupplierDigitalTwinModel

    stmt = select(SupplierDigitalTwinModel).where(
        SupplierDigitalTwinModel.supplier_id == supplier_id,
        SupplierDigitalTwinModel.organization_id == organization_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row:
        return _model_to_domain(row)

    twin = SupplierDigitalTwin(
        supplier_id=supplier_id,
        organization_id=organization_id,
        status=EntityStatus.ACTIVE,
        last_updated_at=datetime.now(UTC),
    )
    model = _domain_to_model(twin)
    session.add(model)
    await session.flush()
    return twin


async def get_twin(
    supplier_id: str,
    organization_id: str,
    session: AsyncSession,
) -> SupplierDigitalTwin | None:
    """Return the twin for this supplier, or None if not yet initialized."""
    from infrastructure.persistence.models.supplier_digital_twin import SupplierDigitalTwinModel

    stmt = select(SupplierDigitalTwinModel).where(
        SupplierDigitalTwinModel.supplier_id == supplier_id,
        SupplierDigitalTwinModel.organization_id == organization_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _model_to_domain(row) if row else None


async def update_twin_health(
    supplier_id: str,
    organization_id: str,
    dimension: str,
    delta: float,
    session: AsyncSession,
    severity: str = "",
) -> SupplierDigitalTwin:
    """Apply a health delta to one dimension and recompute overall health."""
    from infrastructure.persistence.models.supplier_digital_twin import SupplierDigitalTwinModel
    from .health_engine import apply_delta

    stmt = select(SupplierDigitalTwinModel).where(
        SupplierDigitalTwinModel.supplier_id == supplier_id,
        SupplierDigitalTwinModel.organization_id == organization_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if not row:
        twin = await get_or_create_twin(supplier_id, organization_id, session)
        stmt = select(SupplierDigitalTwinModel).where(
            SupplierDigitalTwinModel.supplier_id == supplier_id,
            SupplierDigitalTwinModel.organization_id == organization_id,
        )
        row = (await session.execute(stmt)).scalar_one_or_none()

    prev_overall = row.overall_health

    # Apply delta to the specified dimension
    if hasattr(row, dimension):
        current_val = getattr(row, dimension)
        setattr(row, dimension, apply_delta(current_val, delta))

    # Recompute overall
    dimension_values = {
        d: getattr(row, d)
        for d in [
            "esg_health", "compliance_health", "financial_health",
            "geopolitical_health", "cyber_health", "human_rights_health",
            "environmental_health", "operational_health",
        ]
    }
    row.overall_health = compute_overall_health(dimension_values)
    row.health_trend = compute_trend(prev_overall, row.overall_health)
    row.event_count = (row.event_count or 0) + 1
    if severity.upper() == "CRITICAL":
        row.critical_event_count = (row.critical_event_count or 0) + 1
    row.last_event_at = datetime.now(UTC)
    row.last_updated_at = datetime.now(UTC)
    row.twin_version = (row.twin_version or 1) + 1
    row.updated_at = datetime.now(UTC)

    await session.flush()
    return _model_to_domain(row)


async def list_at_risk_suppliers(
    organization_id: str,
    session: AsyncSession,
    max_overall_health: float = 60.0,
    limit: int = 50,
) -> list[SupplierDigitalTwin]:
    """Return suppliers with overall health below the threshold."""
    from infrastructure.persistence.models.supplier_digital_twin import SupplierDigitalTwinModel

    stmt = (
        select(SupplierDigitalTwinModel)
        .where(
            SupplierDigitalTwinModel.organization_id == organization_id,
            SupplierDigitalTwinModel.overall_health <= max_overall_health,
        )
        .order_by(SupplierDigitalTwinModel.overall_health.asc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


def _domain_to_model(t: SupplierDigitalTwin):
    from infrastructure.persistence.models.supplier_digital_twin import SupplierDigitalTwinModel
    return SupplierDigitalTwinModel(
        id=t.id,
        status=t.status.value if hasattr(t.status, "value") else t.status,
        version=t.version,
        owner=t.owner,
        created_by=t.created_by,
        updated_by=t.updated_by,
        created_at=t.created_at,
        updated_at=t.updated_at,
        supplier_id=t.supplier_id,
        organization_id=t.organization_id,
        esg_health=t.esg_health,
        compliance_health=t.compliance_health,
        financial_health=t.financial_health,
        geopolitical_health=t.geopolitical_health,
        cyber_health=t.cyber_health,
        human_rights_health=t.human_rights_health,
        environmental_health=t.environmental_health,
        operational_health=t.operational_health,
        overall_health=t.overall_health,
        health_trend=t.health_trend,
        ai_confidence=t.ai_confidence,
        open_recommendations=t.open_recommendations,
        open_actions=t.open_actions,
        event_count=t.event_count,
        critical_event_count=t.critical_event_count,
        last_event_at=t.last_event_at,
        last_updated_at=t.last_updated_at,
        twin_version=t.twin_version,
    )


def _model_to_domain(m) -> SupplierDigitalTwin:
    return SupplierDigitalTwin(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        supplier_id=m.supplier_id,
        organization_id=m.organization_id,
        esg_health=m.esg_health,
        compliance_health=m.compliance_health,
        financial_health=m.financial_health,
        geopolitical_health=m.geopolitical_health,
        cyber_health=m.cyber_health,
        human_rights_health=m.human_rights_health,
        environmental_health=m.environmental_health,
        operational_health=m.operational_health,
        overall_health=m.overall_health,
        health_trend=m.health_trend,
        ai_confidence=m.ai_confidence,
        open_recommendations=m.open_recommendations,
        open_actions=m.open_actions,
        event_count=m.event_count,
        critical_event_count=m.critical_event_count or 0,
        last_event_at=m.last_event_at,
        last_updated_at=m.last_updated_at,
        twin_version=m.twin_version,
    )
