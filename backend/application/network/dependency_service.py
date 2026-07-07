"""M38 Supplier Dependency Analysis Service.

Computes:
  dependency_score     — fraction of suppliers classified CRITICAL or HIGH
  concentration_score  — 1 - (distinct_countries / total_active_suppliers)
  diversification_score — 1 - concentration_score (higher = more diversified)
  critical_supplier_count
  single_point_of_failure_count — suppliers with no active alternatives (only child in their component)

Stores results in DependencyAnalysisModel.
supplier_id = None → org-level aggregate.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


async def _log_audit_event(
    session,
    action: str,
    entity_id: str,
    detail: str = "",
    actor_id: str = "network_engine",
) -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel

    now = datetime.now(UTC)
    try:
        event = AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action=action,
            actor_id=actor_id,
            entity_type="dependency_analysis",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("network_dependency_audit_failed", action=action, error=str(exc))


async def compute_dependency_analysis(
    organization_id: str,
    supplier_id: str | None = None,
    session=None,
) -> object:
    from sqlalchemy import func, select

    from infrastructure.persistence.models.network import (
        SupplierCriticalityModel,
    )
    from infrastructure.persistence.models.supplier import SupplierModel

    now = datetime.now(UTC)

    if supplier_id:
        return await _compute_supplier_dependency(organization_id, supplier_id, session, now)

    # Org-level
    total_stmt = (
        select(func.count())
        .select_from(SupplierModel)
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.supplier_status == "Active",
        )
    )
    total = (await session.execute(total_stmt)).scalar_one() or 1

    country_stmt = select(func.count(SupplierModel.country.distinct())).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
        SupplierModel.country != "",
        SupplierModel.country.is_not(None),
    )
    distinct_countries = (await session.execute(country_stmt)).scalar_one() or 1

    crit_stmt = (
        select(func.count())
        .select_from(SupplierCriticalityModel)
        .where(
            SupplierCriticalityModel.organization_id == organization_id,
            SupplierCriticalityModel.criticality.in_(["CRITICAL", "HIGH"]),
        )
    )
    critical_count = (await session.execute(crit_stmt)).scalar_one()

    spof_stmt = (
        select(func.count())
        .select_from(SupplierCriticalityModel)
        .where(
            SupplierCriticalityModel.organization_id == organization_id,
            SupplierCriticalityModel.connected_component_size == 1,
            SupplierCriticalityModel.criticality.in_(["CRITICAL", "HIGH"]),
        )
    )
    spof_count = (await session.execute(spof_stmt)).scalar_one()

    dependency_score = round(critical_count / total, 4)
    concentration_score = round(1.0 - (distinct_countries / total), 4)
    concentration_score = max(0.0, min(1.0, concentration_score))
    diversification_score = round(1.0 - concentration_score, 4)

    inputs = {
        "total_suppliers": total,
        "distinct_countries": distinct_countries,
        "critical_supplier_count": critical_count,
        "spof_count": spof_count,
    }

    result = await _upsert_dependency(
        organization_id=organization_id,
        supplier_id=None,
        dependency_score=dependency_score,
        concentration_score=concentration_score,
        diversification_score=diversification_score,
        critical_supplier_count=critical_count,
        spof_count=spof_count,
        inputs=inputs,
        now=now,
        session=session,
    )
    await _log_audit_event(
        session,
        "network.dependency.refreshed",
        result.id,
        detail=f"org={organization_id} dependency_score={dependency_score}",
    )
    return result


async def _compute_supplier_dependency(
    organization_id: str,
    supplier_id: str,
    session,
    now: datetime,
) -> object:
    """Per-supplier dependency: how central is this supplier to the org?"""
    from sqlalchemy import func, or_, select

    from infrastructure.persistence.models.network import (
        SupplierRelationshipModel,
    )

    # How many suppliers depend on this one (inbound edges)
    in_stmt = (
        select(func.count())
        .select_from(SupplierRelationshipModel)
        .where(
            SupplierRelationshipModel.organization_id == organization_id,
            SupplierRelationshipModel.related_supplier_id == supplier_id,
            SupplierRelationshipModel.relationship_status == "ACTIVE",
        )
    )
    inbound = (await session.execute(in_stmt)).scalar_one()

    total_stmt = (
        select(func.count())
        .select_from(SupplierRelationshipModel)
        .where(
            SupplierRelationshipModel.organization_id == organization_id,
            or_(
                SupplierRelationshipModel.supplier_id == supplier_id,
                SupplierRelationshipModel.related_supplier_id == supplier_id,
            ),
            SupplierRelationshipModel.relationship_status == "ACTIVE",
        )
    )
    total_degree = (await session.execute(total_stmt)).scalar_one()

    dependency_score = round(min(inbound / max(total_degree, 1), 1.0), 4)
    concentration_score = round(min(inbound / 10.0, 1.0), 4)
    diversification_score = round(1.0 - concentration_score, 4)

    inputs = {
        "inbound_degree": inbound,
        "total_degree": total_degree,
        "supplier_id": supplier_id,
    }

    return await _upsert_dependency(
        organization_id=organization_id,
        supplier_id=supplier_id,
        dependency_score=dependency_score,
        concentration_score=concentration_score,
        diversification_score=diversification_score,
        critical_supplier_count=1 if dependency_score > 0.5 else 0,
        spof_count=1 if inbound > 0 and total_degree == inbound else 0,
        inputs=inputs,
        now=now,
        session=session,
    )


async def _upsert_dependency(
    organization_id: str,
    supplier_id: str | None,
    dependency_score: float,
    concentration_score: float,
    diversification_score: float,
    critical_supplier_count: int,
    spof_count: int,
    inputs: dict,
    now: datetime,
    session,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import DependencyAnalysisModel

    stmt = select(DependencyAnalysisModel).where(
        DependencyAnalysisModel.organization_id == organization_id,
        DependencyAnalysisModel.supplier_id == supplier_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.dependency_score = dependency_score
        existing.concentration_score = concentration_score
        existing.diversification_score = diversification_score
        existing.critical_supplier_count = critical_supplier_count
        existing.single_point_of_failure_count = spof_count
        existing.calculation_inputs = inputs
        existing.calculated_at = now
        existing.updated_at = now
        await session.flush()
        return existing

    record = DependencyAnalysisModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        supplier_id=supplier_id,
        dependency_score=dependency_score,
        concentration_score=concentration_score,
        diversification_score=diversification_score,
        critical_supplier_count=critical_supplier_count,
        single_point_of_failure_count=spof_count,
        calculation_inputs=inputs,
        calculated_at=now,
    )
    session.add(record)
    await session.flush()
    return record


async def get_dependency_analysis(
    organization_id: str,
    supplier_id: str | None = None,
    session=None,
) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import DependencyAnalysisModel

    stmt = select(DependencyAnalysisModel).where(
        DependencyAnalysisModel.organization_id == organization_id,
        DependencyAnalysisModel.supplier_id == supplier_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()
