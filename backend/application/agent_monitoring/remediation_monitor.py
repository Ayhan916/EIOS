"""M36 Remediation Monitoring Agent.

Monitors per-org:
  - Overdue remediation plans (due_date passed, status != completed/verified)
  - Long-overdue plans (90+ days) → HIGH escalation
  - Very long-overdue plans (180+ days) → CRITICAL escalation
  - High volume of open plans (> 10 open per supplier)

Integrates with M35 Supplier Portal (RemediationPlanModel).
Also generates recommendation drafts for high-severity overdue plans.
No destructive actions. All outputs are AgentFindings + optional drafts.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from application.agent_monitoring.finding_service import create_finding

logger = structlog.get_logger(__name__)

_OVERDUE_HIGH_DAYS = 30  # overdue 30-89 days = HIGH
_OVERDUE_CRITICAL_DAYS = 90  # overdue 90+ days = CRITICAL
_OPEN_PLANS_HIGH = 10  # supplier with 10+ open plans = concern


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    """Run remediation monitor for one organization. Returns findings created."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.supplier_portal import RemediationPlanModel

    findings_created = 0
    drafts_created = 0
    now = datetime.now(UTC)

    # Load all active suppliers
    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
    )
    suppliers = list((await session.execute(suppliers_stmt)).scalars().all())

    for supplier in suppliers:
        source_base = {"supplier_id": supplier.id, "supplier_name": supplier.name}

        # Load all non-terminal plans for this supplier
        plans_stmt = select(RemediationPlanModel).where(
            RemediationPlanModel.supplier_id == supplier.id,
            RemediationPlanModel.remediation_status.in_(["open", "in_progress"]),
        )
        plans = list((await session.execute(plans_stmt)).scalars().all())

        overdue_critical: list = []
        overdue_high: list = []

        for plan in plans:
            if plan.due_date is None:
                continue
            if plan.due_date >= now:
                continue

            days_overdue = (now - plan.due_date).days

            if days_overdue >= _OVERDUE_CRITICAL_DAYS:
                overdue_critical.append((plan, days_overdue))
            elif days_overdue >= _OVERDUE_HIGH_DAYS:
                overdue_high.append((plan, days_overdue))

        if overdue_critical:
            plan_names = ", ".join(p.title for p, _ in overdue_critical[:3])
            max_overdue = max(d for _, d in overdue_critical)

            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="remediation_critical_overdue",
                severity="CRITICAL",
                title=f"Critical overdue remediation: {supplier.name} ({len(overdue_critical)} plan(s))",
                description=(
                    f"Supplier {supplier.name} has {len(overdue_critical)} remediation plan(s) "
                    f"overdue by {_OVERDUE_CRITICAL_DAYS}+ days (worst: {max_overdue} days). "
                    f"Plans: {plan_names}{'...' if len(overdue_critical) > 3 else ''}. "
                    "Immediate escalation and intervention required."
                ),
                evidence=(
                    f"critical_overdue_plans={len(overdue_critical)}, "
                    f"max_days_overdue={max_overdue}"
                ),
                rule_triggered=f"remediation.due_date < now - {_OVERDUE_CRITICAL_DAYS}d",
                source_data={
                    **source_base,
                    "overdue_days": max_overdue,
                    "critical_overdue_count": len(overdue_critical),
                },
                confidence_score=1.0,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

            # Generate recommendation draft for critical overdue
            draft = await _create_draft(
                agent_id=agent_id,
                organization_id=organization_id,
                supplier=supplier,
                finding=finding,
                plan_count=len(overdue_critical),
                max_overdue=max_overdue,
                session=session,
            )
            if draft:
                drafts_created += 1

        if overdue_high:
            max_overdue = max(d for _, d in overdue_high)
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="remediation_overdue",
                severity="HIGH",
                title=f"Overdue remediation plan(s): {supplier.name} ({len(overdue_high)} plan(s))",
                description=(
                    f"Supplier {supplier.name} has {len(overdue_high)} remediation plan(s) "
                    f"overdue by {_OVERDUE_HIGH_DAYS}-{_OVERDUE_CRITICAL_DAYS - 1} days. "
                    "Prompt follow-up recommended to prevent escalation."
                ),
                evidence=f"overdue_plans={len(overdue_high)}, max_days={max_overdue}",
                rule_triggered=f"{_OVERDUE_HIGH_DAYS}d <= remediation.due_date < now",
                source_data={
                    **source_base,
                    "overdue_days": max_overdue,
                    "high_overdue_count": len(overdue_high),
                },
                confidence_score=1.0,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

        # High volume of open plans
        if len(plans) >= _OPEN_PLANS_HIGH:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="remediation_volume",
                severity="MEDIUM",
                title=f"High remediation plan volume: {supplier.name} ({len(plans)} open)",
                description=(
                    f"Supplier {supplier.name} has {len(plans)} open/in-progress remediation "
                    f"plans, exceeding the threshold of {_OPEN_PLANS_HIGH}. "
                    "Prioritisation review recommended."
                ),
                evidence=f"open_plans={len(plans)}",
                rule_triggered=f"open_plans >= {_OPEN_PLANS_HIGH}",
                source_data={**source_base, "open_plan_count": len(plans)},
                confidence_score=0.85,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

    logger.info(
        "remediation_monitor_completed",
        organization_id=organization_id,
        suppliers_checked=len(suppliers),
        findings_created=findings_created,
        drafts_created=drafts_created,
    )
    return findings_created


async def _create_draft(
    agent_id: str,
    organization_id: str,
    supplier,
    finding,
    plan_count: int,
    max_overdue: int,
    session,
) -> object | None:
    """Generate a recommendation draft for critically overdue remediation."""
    try:
        from application.agent_monitoring.alert_service import create_recommendation_draft

        return await create_recommendation_draft(
            organization_id=organization_id,
            agent_id=agent_id,
            recommendation_text=(
                f"Schedule an urgent remediation review call with {supplier.name}. "
                f"The supplier has {plan_count} remediation plan(s) overdue by {max_overdue}+ days. "
                "Consider: (1) escalating to senior supplier relationship manager, "
                "(2) issuing formal notice, (3) reviewing supplier contract obligations."
            ),
            rationale=(
                f"Critical overdue threshold ({max_overdue} days > 90-day limit) exceeded. "
                "Automated detection based on remediation plan due dates and status."
            ),
            confidence_score=0.9,
            supplier_id=supplier.id,
            agent_finding_id=finding.id,
            session=session,
        )
    except Exception as exc:
        logger.warning("remediation_draft_creation_failed", error=str(exc))
        return None


async def _maybe_escalate(finding, organization_id: str, session) -> None:
    try:
        from application.agent_monitoring.alert_service import evaluate_finding

        await evaluate_finding(finding, organization_id, session, agent_type="REMEDIATION_MONITOR")
    except Exception as exc:
        logger.warning("remediation_monitor_escalation_failed", error=str(exc))
