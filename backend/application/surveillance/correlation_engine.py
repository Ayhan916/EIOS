"""M37 Cross-Supplier Correlation Engine.

Detects patterns across multiple suppliers:
  - Same country deterioration
  - Same sector deterioration
  - Same regulatory issue recurring
  - Same remediation failure pattern

Generates CORRELATED_RISK signals.
"""

from __future__ import annotations

import structlog

from application.surveillance.signal_service import create_signal

logger = structlog.get_logger(__name__)

_COUNTRY_DRIFT_MIN_SUPPLIERS = 2    # at least 2 suppliers in same country deteriorating
_SECTOR_DRIFT_MIN_SUPPLIERS = 2     # at least 2 suppliers in same sector
_REGULATION_REPEAT_THRESHOLD = 2    # same regulation gap in >= 2 suppliers


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    """Run correlation detection for one organization."""
    signals = 0
    signals += await _check_country_correlation(organization_id, session)
    signals += await _check_sector_correlation(organization_id, session)
    signals += await _check_regulation_correlation(organization_id, session)
    return signals


async def _check_country_correlation(organization_id: str, session) -> int:
    """Detect multiple suppliers in same country with drift signals."""
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from infrastructure.persistence.models.supplier import SupplierModel
    from sqlalchemy import func, select
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=30)

    # Find suppliers with recent DRIFT signals
    drift_stmt = (
        select(SurveillanceSignalModel.supplier_id)
        .where(
            SurveillanceSignalModel.organization_id == organization_id,
            SurveillanceSignalModel.signal_type == "DRIFT",
            SurveillanceSignalModel.signal_status == "ACTIVE",
            SurveillanceSignalModel.detected_at >= cutoff,
            SurveillanceSignalModel.supplier_id.is_not(None),
        )
        .distinct()
    )
    drifting_ids = [r[0] for r in (await session.execute(drift_stmt)).all()]
    if len(drifting_ids) < _COUNTRY_DRIFT_MIN_SUPPLIERS:
        return 0

    # Group by country
    country_stmt = (
        select(SupplierModel.country, func.count(SupplierModel.id).label("cnt"))
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.id.in_(drifting_ids),
            SupplierModel.country.is_not(None),
        )
        .group_by(SupplierModel.country)
        .having(func.count(SupplierModel.id) >= _COUNTRY_DRIFT_MIN_SUPPLIERS)
    )
    country_groups = (await session.execute(country_stmt)).all()
    if not country_groups:
        return 0

    signals = 0
    month = datetime.now(UTC).strftime("%Y-%m")
    for country, cnt in country_groups:
        dedupe = f"correlation:country:{organization_id}:{country}:{month}"
        await create_signal(
            organization_id=organization_id,
            signal_type="CORRELATED_RISK",
            source_type="correlation_engine",
            severity="HIGH",
            title=f"Country-level ESG deterioration: {country}",
            description=(
                f"{cnt} suppliers in {country} show simultaneous ESG/risk drift"
            ),
            confidence=0.80,
            supplier_id=None,
            dedupe_key=dedupe,
            explainability={
                "rule_triggered": "country_correlation_drift",
                "source_data": {
                    "country": country,
                    "affected_supplier_count": cnt,
                    "drifting_supplier_ids": drifting_ids,
                },
                "thresholds": {"min_suppliers": _COUNTRY_DRIFT_MIN_SUPPLIERS},
            },
            session=session,
        )
        signals += 1

    return signals


async def _check_sector_correlation(organization_id: str, session) -> int:
    """Detect multiple suppliers in same sector with emerging risk signals."""
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from infrastructure.persistence.models.supplier import SupplierModel
    from sqlalchemy import func, select
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=30)

    signal_stmt = (
        select(SurveillanceSignalModel.supplier_id)
        .where(
            SurveillanceSignalModel.organization_id == organization_id,
            SurveillanceSignalModel.signal_type == "EMERGING_RISK",
            SurveillanceSignalModel.signal_status == "ACTIVE",
            SurveillanceSignalModel.detected_at >= cutoff,
            SurveillanceSignalModel.supplier_id.is_not(None),
        )
        .distinct()
    )
    risky_ids = [r[0] for r in (await session.execute(signal_stmt)).all()]
    if len(risky_ids) < _SECTOR_DRIFT_MIN_SUPPLIERS:
        return 0

    sector_stmt = (
        select(SupplierModel.industry, func.count(SupplierModel.id).label("cnt"))
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.id.in_(risky_ids),
            SupplierModel.industry.is_not(None),
        )
        .group_by(SupplierModel.industry)
        .having(func.count(SupplierModel.id) >= _SECTOR_DRIFT_MIN_SUPPLIERS)
    )
    sector_groups = (await session.execute(sector_stmt)).all()
    if not sector_groups:
        return 0

    signals = 0
    month = datetime.now(UTC).strftime("%Y-%m")
    for industry, cnt in sector_groups:
        dedupe = f"correlation:sector:{organization_id}:{industry}:{month}"
        await create_signal(
            organization_id=organization_id,
            signal_type="CORRELATED_RISK",
            source_type="correlation_engine",
            severity="HIGH",
            title=f"Sector-level emerging risk pattern",
            description=(
                f"{cnt} suppliers in sector show simultaneous emerging risk signals"
            ),
            confidence=0.75,
            supplier_id=None,
            dedupe_key=dedupe,
            explainability={
                "rule_triggered": "sector_correlation_emerging_risk",
                "source_data": {
                    "industry": industry,
                    "affected_supplier_count": cnt,
                },
                "thresholds": {"min_suppliers": _SECTOR_DRIFT_MIN_SUPPLIERS},
            },
            session=session,
        )
        signals += 1

    return signals


async def _check_regulation_correlation(organization_id: str, session) -> int:
    """Detect the same regulation gap appearing across multiple suppliers."""
    try:
        from infrastructure.persistence.models.regulatory import (
            ComplianceGapModel,
            RegulationRequirementModel,
        )
        from sqlalchemy import func, select
        from datetime import UTC, datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(days=60)
        stmt = (
            select(
                ComplianceGapModel.regulation_requirement_id,
                func.count(ComplianceGapModel.entity_id.distinct()).label("supplier_cnt"),
            )
            .where(
                ComplianceGapModel.organization_id == organization_id,
                ComplianceGapModel.gap_status == "OPEN",
                ComplianceGapModel.created_at >= cutoff,
            )
            .group_by(ComplianceGapModel.regulation_requirement_id)
            .having(
                func.count(ComplianceGapModel.entity_id.distinct())
                >= _REGULATION_REPEAT_THRESHOLD
            )
        )
        repeating = (await session.execute(stmt)).all()
    except Exception:
        return 0

    signals = 0
    month = datetime.now(UTC).strftime("%Y-%m") if repeating else ""
    for req_id, cnt in repeating:
        dedupe = f"correlation:regulation:{organization_id}:{req_id}:{month}"
        await create_signal(
            organization_id=organization_id,
            signal_type="CORRELATED_RISK",
            source_type="compliance_gap",
            severity="HIGH",
            title=f"Recurring compliance gap across {cnt} suppliers",
            description=(
                f"The same regulatory requirement is open for {cnt} suppliers"
            ),
            confidence=0.85,
            supplier_id=None,
            dedupe_key=dedupe,
            explainability={
                "rule_triggered": "regulation_repeat_across_suppliers",
                "source_data": {
                    "regulation_requirement_id": req_id,
                    "affected_supplier_count": cnt,
                },
                "thresholds": {"min_suppliers": _REGULATION_REPEAT_THRESHOLD},
            },
            session=session,
        )
        signals += 1

    return signals
