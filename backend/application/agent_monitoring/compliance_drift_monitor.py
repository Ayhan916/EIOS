"""M36 Compliance Drift Agent.

Monitors per-org:
  - Unresolved compliance gaps (is_resolved = False, severity = Critical/High)
  - Critical gap accumulation (count of unresolved critical gaps increasing)
  - Coverage decline (compliance reports with low scores)

Integrates with M31 (ComplianceGapModel, ComplianceReportModel).
No destructive actions. All outputs are AgentFindings.
"""

from __future__ import annotations

import structlog

from application.agent_monitoring.finding_service import create_finding

logger = structlog.get_logger(__name__)

_CRITICAL_GAPS_THRESHOLD = 3    # 3+ critical unresolved gaps = CRITICAL finding
_HIGH_GAPS_THRESHOLD = 10       # 10+ high unresolved gaps = HIGH finding
_LOW_COVERAGE_THRESHOLD = 60.0  # below 60% coverage = concern


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    """Run compliance drift monitor for one organization. Returns findings created."""
    from infrastructure.persistence.models.regulatory import (
        ComplianceGapModel,
        ComplianceReportModel,
    )
    from sqlalchemy import func, select

    findings_created = 0

    # Count unresolved gaps by severity
    critical_gaps_stmt = select(func.count()).select_from(ComplianceGapModel).where(
        ComplianceGapModel.organization_id == organization_id,
        ComplianceGapModel.is_resolved.is_(False),
        ComplianceGapModel.severity == "Critical",
    )
    critical_gaps = (await session.execute(critical_gaps_stmt)).scalar_one()

    high_gaps_stmt = select(func.count()).select_from(ComplianceGapModel).where(
        ComplianceGapModel.organization_id == organization_id,
        ComplianceGapModel.is_resolved.is_(False),
        ComplianceGapModel.severity == "High",
    )
    high_gaps = (await session.execute(high_gaps_stmt)).scalar_one()

    total_gaps_stmt = select(func.count()).select_from(ComplianceGapModel).where(
        ComplianceGapModel.organization_id == organization_id,
        ComplianceGapModel.is_resolved.is_(False),
    )
    total_gaps = (await session.execute(total_gaps_stmt)).scalar_one()

    source_data = {
        "organization_id": organization_id,
        "critical_gaps": critical_gaps,
        "high_gaps": high_gaps,
        "total_unresolved_gaps": total_gaps,
    }

    # Rule 1: Critical gaps accumulated
    if critical_gaps >= _CRITICAL_GAPS_THRESHOLD:
        finding = await create_finding(
            organization_id=organization_id,
            agent_id=agent_id,
            category="compliance_critical_gaps",
            severity="CRITICAL",
            title=f"Critical compliance gap accumulation: {critical_gaps} unresolved",
            description=(
                f"Organisation has {critical_gaps} unresolved critical compliance gaps, "
                f"exceeding the threshold of {_CRITICAL_GAPS_THRESHOLD}. "
                "Immediate attention required to avoid regulatory exposure."
            ),
            evidence=f"critical_gaps={critical_gaps}",
            rule_triggered=f"critical_gaps >= {_CRITICAL_GAPS_THRESHOLD}",
            source_data=source_data,
            confidence_score=0.95,
            supplier_id=None,
            agent_run_id=agent_run_id,
            session=session,
        )
        await _maybe_escalate(finding, organization_id, session)
        findings_created += 1

    elif critical_gaps > 0:
        finding = await create_finding(
            organization_id=organization_id,
            agent_id=agent_id,
            category="compliance_critical_gaps",
            severity="HIGH",
            title=f"Unresolved critical compliance gap(s): {critical_gaps}",
            description=(
                f"Organisation has {critical_gaps} unresolved critical compliance gap(s). "
                "Review and resolve before regulatory deadlines."
            ),
            evidence=f"critical_gaps={critical_gaps}",
            rule_triggered="critical_gaps > 0",
            source_data=source_data,
            confidence_score=0.9,
            supplier_id=None,
            agent_run_id=agent_run_id,
            session=session,
        )
        await _maybe_escalate(finding, organization_id, session)
        findings_created += 1

    # Rule 2: High severity gap volume
    if high_gaps >= _HIGH_GAPS_THRESHOLD:
        finding = await create_finding(
            organization_id=organization_id,
            agent_id=agent_id,
            category="compliance_gap_volume",
            severity="HIGH",
            title=f"High compliance gap volume: {high_gaps} high-severity unresolved",
            description=(
                f"Organisation has {high_gaps} unresolved high-severity compliance gaps, "
                f"exceeding the threshold of {_HIGH_GAPS_THRESHOLD}. "
                "Systematic remediation programme recommended."
            ),
            evidence=f"high_gaps={high_gaps}",
            rule_triggered=f"high_gaps >= {_HIGH_GAPS_THRESHOLD}",
            source_data=source_data,
            confidence_score=0.85,
            supplier_id=None,
            agent_run_id=agent_run_id,
            session=session,
        )
        await _maybe_escalate(finding, organization_id, session)
        findings_created += 1

    # Rule 3: Compliance report coverage check
    latest_report_stmt = (
        select(ComplianceReportModel)
        .where(ComplianceReportModel.organization_id == organization_id)
        .order_by(ComplianceReportModel.generated_at.desc())
        .limit(1)
    )
    report = (await session.execute(latest_report_stmt)).scalar_one_or_none()
    if report and isinstance(report.report_data, dict):
        coverage = report.report_data.get("coverage_percentage")
        if coverage is not None and float(coverage) < _LOW_COVERAGE_THRESHOLD:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="compliance_coverage_low",
                severity="HIGH",
                title=f"Low compliance coverage: {coverage:.1f}%",
                description=(
                    f"Latest compliance report ({report.framework_code}) shows "
                    f"{coverage:.1f}% coverage, below the threshold of {_LOW_COVERAGE_THRESHOLD}%. "
                    "Gap analysis and remediation planning required."
                ),
                evidence=f"coverage={coverage:.1f}%, framework={report.framework_code}",
                rule_triggered=f"coverage < {_LOW_COVERAGE_THRESHOLD}%",
                source_data={
                    **source_data,
                    "coverage_percentage": float(coverage),
                    "framework": report.framework_code,
                },
                confidence_score=0.9,
                supplier_id=None,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

    logger.info(
        "compliance_drift_monitor_completed",
        organization_id=organization_id,
        critical_gaps=critical_gaps,
        high_gaps=high_gaps,
        findings_created=findings_created,
    )
    return findings_created


async def _maybe_escalate(finding, organization_id: str, session) -> None:
    try:
        from application.agent_monitoring.alert_service import evaluate_finding

        await evaluate_finding(finding, organization_id, session, agent_type="COMPLIANCE_MONITOR")
    except Exception as exc:
        logger.warning("compliance_drift_escalation_failed", error=str(exc))
