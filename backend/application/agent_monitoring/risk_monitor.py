"""M36 Risk Monitoring Agent.

Runs daily. Monitors per-org:
  - supplier risk score deterioration (trend = Deteriorating OR trend_delta < -10)
  - ESG score < 40 (critical threshold)
  - Benchmark percentile < 10th (bottom decile)
  - Rising findings count (> 5 open findings per supplier)

Integrates with M28 (SupplierScoreModel) and M4 (FindingModel).
No destructive actions. All outputs are AgentFindings + optional alerts.
"""

from __future__ import annotations

import structlog

from application.agent_monitoring.finding_service import create_finding

logger = structlog.get_logger(__name__)

# Thresholds — calibrated conservatively to avoid noise
_RISK_SCORE_HIGH_THRESHOLD = 70.0  # risk_score above this is HIGH
_RISK_SCORE_CRITICAL_THRESHOLD = 85.0  # risk_score above this is CRITICAL
_ESG_SCORE_LOW_THRESHOLD = 40.0  # ESG score below this is concerning
_PERCENTILE_BOTTOM_DECILE = 10.0  # below 10th percentile = underperformer
_TREND_DELTA_THRESHOLD = -10.0  # esg_score declined by 10+ points
_OPEN_FINDINGS_HIGH = 5  # more than 5 open findings = concern


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    """Run the risk monitor for one organization. Returns number of findings generated."""
    from sqlalchemy import func, select

    from infrastructure.persistence.models.finding import FindingModel
    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.supplier_score import SupplierScoreModel

    findings_created = 0

    # Load all active suppliers for this org
    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
    )
    suppliers = list((await session.execute(suppliers_stmt)).scalars().all())

    for supplier in suppliers:
        # Latest score for this supplier
        score_stmt = (
            select(SupplierScoreModel)
            .where(
                SupplierScoreModel.supplier_id == supplier.id,
                SupplierScoreModel.organization_id == organization_id,
            )
            .order_by(SupplierScoreModel.created_at.desc())
            .limit(1)
        )
        score = (await session.execute(score_stmt)).scalar_one_or_none()
        if score is None:
            continue

        # Open findings count
        findings_count_stmt = (
            select(func.count())
            .select_from(FindingModel)
            .where(
                FindingModel.assessment_id.in_(
                    select(
                        __import__("sqlalchemy", fromlist=["literal_column"]).literal_column("id")
                    )
                )
            )
        )
        # Simplified — count findings linked to any assessment for this supplier
        from infrastructure.persistence.models.assessment import AssessmentModel

        assessment_ids_subq = (
            select(AssessmentModel.id)
            .where(AssessmentModel.supplier_id == supplier.id)
            .scalar_subquery()
        )
        findings_count_stmt = (
            select(func.count())
            .select_from(FindingModel)
            .where(FindingModel.assessment_id.in_(assessment_ids_subq))
        )
        open_findings_count = (await session.execute(findings_count_stmt)).scalar_one()

        source_data = {
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "risk_score": score.risk_score,
            "risk_band": score.risk_band,
            "esg_score": score.esg_score,
            "trend": score.trend,
            "trend_delta": score.trend_delta,
            "sector_percentile": score.sector_percentile,
            "open_findings": open_findings_count,
        }

        # Rule 1: High / Critical risk score
        if score.risk_score >= _RISK_SCORE_CRITICAL_THRESHOLD:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="risk_score",
                severity="CRITICAL",
                title=f"Critical risk score for {supplier.name}",
                description=(
                    f"Supplier {supplier.name} has a risk score of {score.risk_score:.1f} "
                    f"(band: {score.risk_band}), which exceeds the critical threshold of "
                    f"{_RISK_SCORE_CRITICAL_THRESHOLD}. Immediate review required."
                ),
                evidence=f"risk_score={score.risk_score:.1f}, band={score.risk_band}",
                rule_triggered=f"risk_score >= {_RISK_SCORE_CRITICAL_THRESHOLD}",
                source_data=source_data,
                confidence_score=0.95,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

        elif score.risk_score >= _RISK_SCORE_HIGH_THRESHOLD:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="risk_score",
                severity="HIGH",
                title=f"High risk score for {supplier.name}",
                description=(
                    f"Supplier {supplier.name} has a risk score of {score.risk_score:.1f} "
                    f"(band: {score.risk_band}), indicating elevated risk."
                ),
                evidence=f"risk_score={score.risk_score:.1f}, band={score.risk_band}",
                rule_triggered=f"risk_score >= {_RISK_SCORE_HIGH_THRESHOLD}",
                source_data=source_data,
                confidence_score=0.9,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

        # Rule 2: ESG score deterioration
        if score.trend == "Deteriorating" and score.trend_delta <= _TREND_DELTA_THRESHOLD:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="esg_deterioration",
                severity="HIGH",
                title=f"ESG score deteriorating for {supplier.name}",
                description=(
                    f"Supplier {supplier.name}'s ESG score has declined by "
                    f"{abs(score.trend_delta):.1f} points (trend: {score.trend}). "
                    f"Current ESG score: {score.esg_score:.1f}."
                ),
                evidence=(
                    f"esg_score={score.esg_score:.1f}, "
                    f"trend_delta={score.trend_delta:.1f}, trend={score.trend}"
                ),
                rule_triggered=f"trend=Deteriorating AND trend_delta <= {_TREND_DELTA_THRESHOLD}",
                source_data={"risk_score_delta": score.trend_delta, **source_data},
                confidence_score=0.85,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

        # Rule 3: Below 10th percentile benchmark
        if (
            score.sector_percentile is not None
            and score.sector_percentile < _PERCENTILE_BOTTOM_DECILE
        ):
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="benchmark_underperformance",
                severity="MEDIUM",
                title=f"Benchmark underperformance for {supplier.name}",
                description=(
                    f"Supplier {supplier.name} ranks at the "
                    f"{score.sector_percentile:.0f}th percentile in their sector, "
                    f"placing them in the bottom 10%."
                ),
                evidence=f"sector_percentile={score.sector_percentile:.1f}",
                rule_triggered=f"sector_percentile < {_PERCENTILE_BOTTOM_DECILE}",
                source_data=source_data,
                confidence_score=0.8,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

        # Rule 4: High open findings count
        if open_findings_count > _OPEN_FINDINGS_HIGH:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="findings_accumulation",
                severity="MEDIUM",
                title=f"Elevated open findings for {supplier.name}",
                description=(
                    f"Supplier {supplier.name} has {open_findings_count} open findings, "
                    f"exceeding the threshold of {_OPEN_FINDINGS_HIGH}. "
                    "Consider prioritising remediation."
                ),
                evidence=f"open_findings={open_findings_count}",
                rule_triggered=f"open_findings > {_OPEN_FINDINGS_HIGH}",
                source_data=source_data,
                confidence_score=0.85,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

    logger.info(
        "risk_monitor_completed",
        organization_id=organization_id,
        suppliers_checked=len(suppliers),
        findings_created=findings_created,
    )
    return findings_created


async def _maybe_escalate(finding, organization_id: str, session) -> None:
    try:
        from application.agent_monitoring.alert_service import evaluate_finding

        await evaluate_finding(finding, organization_id, session, agent_type="RISK_MONITOR")
    except Exception as exc:
        logger.warning("risk_monitor_escalation_failed", error=str(exc))
