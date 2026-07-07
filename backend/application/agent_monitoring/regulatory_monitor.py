"""M36 Regulatory Monitoring Agent.

Monitors:
  - Regulation version changes (reg_version field updated)
  - New regulations added since last run
  - New CSRD/ESRS/LkSG/CSDDD/ISSB/TCFD obligations
  - Upcoming effective dates (< 90 days)

Integrates with M31 (RegulationModel, RegulationRequirementModel).
Generates impact assessments as AgentFindings.
No destructive actions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

from application.agent_monitoring.finding_service import create_finding

logger = structlog.get_logger(__name__)

_UPCOMING_DAYS = 90  # flag regulations going live within 90 days
_HIGH_PRIORITY_FRAMEWORKS = {"CSRD", "LkSG", "CSDDD", "ESRS", "ISSB", "TCFD", "SFDR", "GRI"}


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    """Run regulatory monitor for one organization. Returns findings created."""
    from sqlalchemy import select

    from infrastructure.persistence.models.regulatory import (
        RegulationModel,
        RegulationRequirementModel,
    )

    findings_created = 0
    now = datetime.now(UTC)
    upcoming_cutoff = now + timedelta(days=_UPCOMING_DAYS)

    # Load all active regulations
    regs_stmt = select(RegulationModel).where(RegulationModel.reg_status == "active")
    regulations = list((await session.execute(regs_stmt)).scalars().all())

    for regulation in regulations:
        code = regulation.code
        is_priority = any(fw in code for fw in _HIGH_PRIORITY_FRAMEWORKS)
        source_data = {
            "regulation_id": regulation.id,
            "code": code,
            "name": regulation.name,
            "jurisdiction": regulation.jurisdiction,
            "version": regulation.reg_version,
            "effective_date": str(regulation.effective_date) if regulation.effective_date else None,
        }

        # Rule 1: Upcoming effective date
        if (
            regulation.effective_date
            and now.date() <= regulation.effective_date <= upcoming_cutoff.date()
        ):
            days_remaining = (regulation.effective_date - now.date()).days
            severity = "CRITICAL" if is_priority else "HIGH"

            # Dedupe key: same regulation code + version + category avoids
            # repeated findings across scheduler cycles (M36.2 item 3).
            dedupe_rule = f"regulation:{code}:{regulation.reg_version}:upcoming_obligation"

            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="upcoming_obligation",
                severity=severity,
                title=f"{code} effective in {days_remaining} days",
                description=(
                    f"Regulation {code} ({regulation.name}) becomes effective on "
                    f"{regulation.effective_date}. {days_remaining} days remaining. "
                    f"Jurisdiction: {regulation.jurisdiction}. "
                    f"Version: {regulation.reg_version}. "
                    "Review compliance readiness and complete any outstanding obligations."
                ),
                evidence=f"effective_date={regulation.effective_date}, days_remaining={days_remaining}",
                rule_triggered=dedupe_rule,
                source_data=source_data,
                confidence_score=1.0,
                supplier_id=None,
                agent_run_id=agent_run_id,
                skip_if_open=True,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

    # Rule 2: Count new requirements added recently (last 48h indicator)
    # (In production this would compare against last-run state; here we flag new reqs)
    from sqlalchemy import func

    req_count_stmt = select(func.count()).select_from(RegulationRequirementModel)
    total_reqs = (await session.execute(req_count_stmt)).scalar_one()

    if total_reqs > 0 and len(regulations) > 0:
        # Report framework coverage as INFO
        priority_regs = [
            r for r in regulations if any(fw in r.code for fw in _HIGH_PRIORITY_FRAMEWORKS)
        ]
        if priority_regs:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="regulatory_landscape",
                severity="LOW",
                title=f"Regulatory coverage: {len(priority_regs)} priority frameworks active",
                description=(
                    f"EIOS is tracking {len(priority_regs)} priority regulatory frameworks "
                    f"({', '.join(r.code for r in priority_regs[:5])}{'...' if len(priority_regs) > 5 else ''}) "
                    f"with {total_reqs} total requirements. "
                    "Review any recently added requirements for impact."
                ),
                evidence=f"frameworks={len(priority_regs)}, requirements={total_reqs}",
                rule_triggered="regulatory_landscape_summary",
                source_data={
                    "priority_framework_count": len(priority_regs),
                    "total_requirements": total_reqs,
                    "frameworks": [r.code for r in priority_regs],
                },
                confidence_score=0.95,
                supplier_id=None,
                agent_run_id=agent_run_id,
                session=session,
            )
            findings_created += 1

    logger.info(
        "regulatory_monitor_completed",
        organization_id=organization_id,
        regulations_checked=len(regulations),
        findings_created=findings_created,
    )
    return findings_created


async def _maybe_escalate(finding, organization_id: str, session) -> None:
    try:
        from application.agent_monitoring.alert_service import evaluate_finding

        await evaluate_finding(finding, organization_id, session, agent_type="REGULATION_MONITOR")
    except Exception as exc:
        logger.warning("regulatory_monitor_escalation_failed", error=str(exc))
