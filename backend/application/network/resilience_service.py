"""M38 Supply Chain Resilience Service.

Computes resilience scores per org and per supplier:

  diversification_score — how spread across countries/sectors
  concentration_score   — inverse of diversification
  redundancy_score      — fraction of HIGH/CRITICAL suppliers with peer alternatives
  resilience_score      — weighted composite

Formula (org-level):
  resilience_score = 0.40 × diversification + 0.35 × redundancy + 0.25 × (1 - concentration)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from application.network.metrics import network_counters

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
            entity_type="resilience_assessment",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("network_resilience_audit_failed", action=action, error=str(exc))


async def compute_resilience(
    organization_id: str,
    supplier_id: str | None = None,
    session=None,
) -> object:
    from sqlalchemy import func, select

    from infrastructure.persistence.models.network import (
        SupplierCriticalityModel,
        SupplierRelationshipModel,
    )
    from infrastructure.persistence.models.supplier import SupplierModel

    now = datetime.now(UTC)

    total_stmt = (
        select(func.count())
        .select_from(SupplierModel)
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.supplier_status == "Active",
        )
    )
    total = max((await session.execute(total_stmt)).scalar_one(), 1)

    country_stmt = select(func.count(SupplierModel.country.distinct())).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
        SupplierModel.country != "",
        SupplierModel.country.is_not(None),
    )
    distinct_countries = (await session.execute(country_stmt)).scalar_one() or 1

    sector_stmt = select(func.count(SupplierModel.industry.distinct())).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
        SupplierModel.industry != "",
        SupplierModel.industry.is_not(None),
    )
    distinct_sectors = (await session.execute(sector_stmt)).scalar_one() or 1

    geo_div = min(distinct_countries / max(total / 3, 1), 1.0)
    sec_div = min(distinct_sectors / max(total / 5, 1), 1.0)
    diversification_score = round((geo_div + sec_div) / 2, 4)
    concentration_score = round(1.0 - diversification_score, 4)

    # Redundancy: fraction of CRITICAL/HIGH suppliers that have at least 1 peer
    crit_stmt = select(SupplierCriticalityModel.supplier_id).where(
        SupplierCriticalityModel.organization_id == organization_id,
        SupplierCriticalityModel.criticality.in_(["CRITICAL", "HIGH"]),
    )
    critical_ids = list((await session.execute(crit_stmt)).scalars().all())

    if not critical_ids:
        redundancy_score = 1.0
    else:
        with_peers = 0
        for sid in critical_ids:
            peer_stmt = (
                select(func.count())
                .select_from(SupplierRelationshipModel)
                .where(
                    SupplierRelationshipModel.organization_id == organization_id,
                    SupplierRelationshipModel.relationship_status == "ACTIVE",
                    SupplierRelationshipModel.supplier_id == sid,
                )
            )
            peer_count = (await session.execute(peer_stmt)).scalar_one()
            if peer_count > 0:
                with_peers += 1
        redundancy_score = round(with_peers / len(critical_ids), 4)

    resilience_score = round(
        0.40 * diversification_score + 0.35 * redundancy_score + 0.25 * (1.0 - concentration_score),
        4,
    )

    inputs = {
        "total_suppliers": total,
        "distinct_countries": distinct_countries,
        "distinct_sectors": distinct_sectors,
        "critical_supplier_count": len(critical_ids),
        "weights": {"diversification": 0.40, "redundancy": 0.35, "inverse_concentration": 0.25},
    }

    network_counters.record_resilience_calculated()
    result = await _upsert_resilience(
        organization_id=organization_id,
        supplier_id=supplier_id,
        resilience_score=resilience_score,
        diversification_score=diversification_score,
        concentration_score=concentration_score,
        redundancy_score=redundancy_score,
        inputs=inputs,
        now=now,
        session=session,
    )
    await _log_audit_event(
        session,
        "network.resilience.refreshed",
        result.id,
        detail=f"org={organization_id} resilience_score={resilience_score}",
    )
    return result


async def _upsert_resilience(
    organization_id: str,
    supplier_id: str | None,
    resilience_score: float,
    diversification_score: float,
    concentration_score: float,
    redundancy_score: float,
    inputs: dict,
    now: datetime,
    session,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import ResilienceAssessmentModel

    stmt = select(ResilienceAssessmentModel).where(
        ResilienceAssessmentModel.organization_id == organization_id,
        ResilienceAssessmentModel.supplier_id == supplier_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.resilience_score = resilience_score
        existing.diversification_score = diversification_score
        existing.concentration_score = concentration_score
        existing.redundancy_score = redundancy_score
        existing.calculation_inputs = inputs
        existing.calculated_at = now
        existing.updated_at = now
        await session.flush()
        return existing

    record = ResilienceAssessmentModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        supplier_id=supplier_id,
        resilience_score=resilience_score,
        diversification_score=diversification_score,
        concentration_score=concentration_score,
        redundancy_score=redundancy_score,
        calculation_inputs=inputs,
        calculated_at=now,
    )
    session.add(record)
    await session.flush()
    return record


async def get_resilience(
    organization_id: str,
    supplier_id: str | None = None,
    session=None,
) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import ResilienceAssessmentModel

    stmt = select(ResilienceAssessmentModel).where(
        ResilienceAssessmentModel.organization_id == organization_id,
        ResilienceAssessmentModel.supplier_id == supplier_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()
