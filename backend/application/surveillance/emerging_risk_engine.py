"""M37 Emerging Risk Detection Engine.

Detects sudden increases in findings, repeated remediation failures,
repeated compliance gaps, increasing sanctions exposure, and deteriorating
country indicators. Integrates with M36 (agent findings), M34 (external intelligence).
"""

from __future__ import annotations

import structlog

from application.surveillance.signal_service import create_signal
from application.surveillance.watchlist_service import auto_watchlist_from_alerts

logger = structlog.get_logger(__name__)

_FINDING_SURGE_THRESHOLD = 5        # new agent findings in 7 days
_REMEDIATION_FAIL_THRESHOLD = 3     # consecutive remediation failures
_SANCTIONS_EXPOSURE_THRESHOLD = 1   # any sanctions hit triggers


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    from infrastructure.persistence.models.supplier import SupplierModel
    from sqlalchemy import select

    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
    )
    suppliers = list((await session.execute(suppliers_stmt)).scalars().all())

    signals_created = 0
    for supplier in suppliers:
        signals_created += await _check_finding_surge(supplier, organization_id, session)
        signals_created += await _check_remediation_failures(supplier, organization_id, session)
        signals_created += await _check_sanctions_exposure(supplier, organization_id, session)
        signals_created += await _check_country_risk(supplier, organization_id, session)
        # Auto-watchlist from repeated alerts
        await auto_watchlist_from_alerts(organization_id, supplier.id, session)

    return signals_created


async def _check_finding_surge(supplier, organization_id: str, session) -> int:
    """Detect sudden increase in agent findings (M36 integration)."""
    from infrastructure.persistence.models.agent_monitoring import AgentFindingModel
    from sqlalchemy import func, select
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=7)
    stmt = select(func.count()).select_from(AgentFindingModel).where(
        AgentFindingModel.organization_id == organization_id,
        AgentFindingModel.supplier_id == supplier.id,
        AgentFindingModel.finding_status == "OPEN",
        AgentFindingModel.created_at >= cutoff,
    )
    count = (await session.execute(stmt)).scalar_one()
    if count < _FINDING_SURGE_THRESHOLD:
        return 0

    from datetime import UTC, datetime
    week = datetime.now(UTC).strftime("%Y-W%V")
    dedupe = f"emerging:finding_surge:{supplier.id}:{week}"
    await create_signal(
        organization_id=organization_id,
        signal_type="EMERGING_RISK",
        source_type="agent_finding",
        severity="HIGH",
        title=f"Finding surge detected: {supplier.name}",
        description=f"{count} new OPEN findings in the last 7 days",
        confidence=0.90,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "agent_finding_surge_7d",
            "source_data": {"findings_7d": count},
            "thresholds": {"min_findings_7d": _FINDING_SURGE_THRESHOLD},
        },
        session=session,
    )
    return 1


async def _check_remediation_failures(supplier, organization_id: str, session) -> int:
    """Detect repeated remediation overdue plans (M35 integration)."""
    try:
        from infrastructure.persistence.models.risk import RemediationPlanModel
        from sqlalchemy import func, select
        from datetime import UTC, datetime

        stmt = select(func.count()).select_from(RemediationPlanModel).where(
            RemediationPlanModel.organization_id == organization_id,
            RemediationPlanModel.supplier_id == supplier.id,
            RemediationPlanModel.plan_status == "OVERDUE",
        )
        count = (await session.execute(stmt)).scalar_one()
    except Exception:
        return 0

    if count < _REMEDIATION_FAIL_THRESHOLD:
        return 0

    from datetime import UTC, datetime
    month = datetime.now(UTC).strftime("%Y-%m")
    dedupe = f"emerging:remediation_fail:{supplier.id}:{month}"
    await create_signal(
        organization_id=organization_id,
        signal_type="EMERGING_RISK",
        source_type="remediation",
        severity="HIGH",
        title=f"Repeated remediation failures: {supplier.name}",
        description=f"{count} overdue remediation plans",
        confidence=0.85,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "remediation_overdue_count",
            "source_data": {"overdue_plans": count},
            "thresholds": {"min_overdue": _REMEDIATION_FAIL_THRESHOLD},
        },
        session=session,
    )
    return 1


async def _check_sanctions_exposure(supplier, organization_id: str, session) -> int:
    """Detect active sanctions exposure from M34 external intelligence."""
    try:
        from infrastructure.persistence.models.external_intelligence import ExternalIntelligenceModel
        from sqlalchemy import select

        stmt = (
            select(ExternalIntelligenceModel)
            .where(
                ExternalIntelligenceModel.organization_id == organization_id,
                ExternalIntelligenceModel.supplier_id == supplier.id,
                ExternalIntelligenceModel.dataset_type == "sanctions",
                ExternalIntelligenceModel.dataset_status == "active",
            )
            .limit(1)
        )
        hit = (await session.execute(stmt)).scalar_one_or_none()
    except Exception:
        return 0

    if hit is None:
        return 0

    dedupe = f"emerging:sanctions:{supplier.id}:{hit.id}"
    await create_signal(
        organization_id=organization_id,
        signal_type="EMERGING_RISK",
        source_type="external_intelligence",
        source_id=hit.id,
        severity="CRITICAL",
        title=f"Sanctions exposure detected: {supplier.name}",
        description="Active sanctions dataset match for this supplier",
        confidence=1.0,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "sanctions_exposure_active",
            "source_data": {"dataset_id": hit.id, "dataset_type": "sanctions"},
            "thresholds": {"match_required": True},
        },
        session=session,
    )
    return 1


async def _check_country_risk(supplier, organization_id: str, session) -> int:
    """Detect deteriorating country risk indicators from M34."""
    try:
        from infrastructure.persistence.models.external_intelligence import ExternalIntelligenceModel
        from sqlalchemy import select

        if not getattr(supplier, "country", None):
            return 0

        stmt = (
            select(ExternalIntelligenceModel)
            .where(
                ExternalIntelligenceModel.organization_id == organization_id,
                ExternalIntelligenceModel.dataset_type == "country_risk",
                ExternalIntelligenceModel.dataset_status == "active",
                ExternalIntelligenceModel.country_code == supplier.country,
            )
            .order_by(ExternalIntelligenceModel.imported_at.desc())
            .limit(1)
        )
        record = (await session.execute(stmt)).scalar_one_or_none()
    except Exception:
        return 0

    if record is None:
        return 0

    try:
        risk_level = (record.raw_data or {}).get("risk_level", "LOW")
    except Exception:
        return 0

    if risk_level not in ("HIGH", "VERY_HIGH", "CRITICAL"):
        return 0

    from datetime import UTC, datetime
    month = datetime.now(UTC).strftime("%Y-%m")
    dedupe = f"emerging:country_risk:{supplier.id}:{supplier.country}:{month}"
    await create_signal(
        organization_id=organization_id,
        signal_type="EMERGING_RISK",
        source_type="external_intelligence",
        source_id=record.id,
        severity="HIGH" if risk_level == "HIGH" else "CRITICAL",
        title=f"High country risk ({supplier.country}): {supplier.name}",
        description=f"Country risk level: {risk_level}",
        confidence=0.80,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "country_risk_level_elevated",
            "source_data": {"country": supplier.country, "risk_level": risk_level},
            "thresholds": {"trigger_levels": ["HIGH", "VERY_HIGH", "CRITICAL"]},
        },
        session=session,
    )
    return 1
