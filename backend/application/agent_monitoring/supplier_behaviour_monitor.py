"""M36 Supplier Behaviour Agent.

Monitors:
  - Questionnaire overdue (due_date passed, status not submitted)
  - Evidence request overdue (due_date passed, status not in_progress/accepted)
  - Remediation plan stalled (no progress update in 30 days)
  - Supplier inactivity (no activity events in 30 days)

Integrates with M35 Supplier Portal (questionnaire, evidence, remediation, activity models).
No destructive actions. All outputs are AgentFindings.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

from application.agent_monitoring.finding_service import create_finding

logger = structlog.get_logger(__name__)

_QUESTIONNAIRE_OVERDUE_DAYS = 0    # flag as soon as due_date passes
_EVIDENCE_OVERDUE_DAYS = 0         # flag as soon as due_date passes
_INACTIVITY_DAYS = 30              # no activity in 30 days = disengagement risk
_STALL_DAYS = 30                   # no progress update in 30 days


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    """Run supplier behaviour monitor. Returns findings created."""
    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.supplier_portal import (
        EvidenceRequestModel,
        QuestionnaireAssignmentModel,
        RemediationPlanModel,
        SupplierActivityEventModel,
    )
    from sqlalchemy import func, select

    findings_created = 0
    now = datetime.now(UTC)
    inactivity_cutoff = now - timedelta(days=_INACTIVITY_DAYS)
    stall_cutoff = now - timedelta(days=_STALL_DAYS)

    # Load all active suppliers for this org
    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
    )
    suppliers = list((await session.execute(suppliers_stmt)).scalars().all())

    for supplier in suppliers:
        source_base = {"supplier_id": supplier.id, "supplier_name": supplier.name}

        # --- Overdue questionnaires ---
        overdue_q_stmt = select(func.count()).select_from(QuestionnaireAssignmentModel).where(
            QuestionnaireAssignmentModel.supplier_id == supplier.id,
            QuestionnaireAssignmentModel.questionnaire_status.in_(["assigned", "in_progress"]),
            QuestionnaireAssignmentModel.due_date < now,
        )
        overdue_q_count = (await session.execute(overdue_q_stmt)).scalar_one()

        if overdue_q_count > 0:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="questionnaire_overdue",
                severity="HIGH" if overdue_q_count >= 2 else "MEDIUM",
                title=f"Overdue questionnaire(s): {supplier.name}",
                description=(
                    f"Supplier {supplier.name} has {overdue_q_count} overdue "
                    f"questionnaire assignment(s). Prompt response required."
                ),
                evidence=f"overdue_questionnaires={overdue_q_count}",
                rule_triggered="questionnaire due_date < now AND status in [assigned, in_progress]",
                source_data={"overdue_questionnaires": overdue_q_count, **source_base},
                confidence_score=1.0,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

        # --- Overdue evidence requests ---
        overdue_ev_stmt = select(func.count()).select_from(EvidenceRequestModel).where(
            EvidenceRequestModel.supplier_id == supplier.id,
            EvidenceRequestModel.organization_id == organization_id,
            EvidenceRequestModel.evidence_status.in_(["open"]),
            EvidenceRequestModel.due_date < now,
        )
        overdue_ev_count = (await session.execute(overdue_ev_stmt)).scalar_one()

        if overdue_ev_count > 0:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="evidence_overdue",
                severity="MEDIUM",
                title=f"Overdue evidence request(s): {supplier.name}",
                description=(
                    f"Supplier {supplier.name} has {overdue_ev_count} unanswered evidence "
                    f"request(s) past their due date. Follow up required."
                ),
                evidence=f"overdue_evidence_requests={overdue_ev_count}",
                rule_triggered="evidence_request.due_date < now AND status=open",
                source_data={"overdue_evidence": overdue_ev_count, **source_base},
                confidence_score=1.0,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

        # --- Stalled remediation plans ---
        stalled_rem_stmt = select(func.count()).select_from(RemediationPlanModel).where(
            RemediationPlanModel.supplier_id == supplier.id,
            RemediationPlanModel.remediation_status.in_(["open", "in_progress"]),
            RemediationPlanModel.updated_at < stall_cutoff,
        )
        stalled_rem_count = (await session.execute(stalled_rem_stmt)).scalar_one()

        if stalled_rem_count > 0:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="remediation_stalled",
                severity="HIGH",
                title=f"Stalled remediation plan(s): {supplier.name}",
                description=(
                    f"Supplier {supplier.name} has {stalled_rem_count} remediation plan(s) "
                    f"with no progress update in the last {_STALL_DAYS} days. "
                    "Engagement and escalation recommended."
                ),
                evidence=f"stalled_plans={stalled_rem_count}",
                rule_triggered=f"remediation.updated_at < now - {_STALL_DAYS}d AND status in [open, in_progress]",
                source_data={"stalled_remediation_plans": stalled_rem_count, **source_base},
                confidence_score=0.9,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

        # --- Supplier inactivity ---
        last_activity_stmt = (
            select(SupplierActivityEventModel.created_at)
            .where(SupplierActivityEventModel.supplier_id == supplier.id)
            .order_by(SupplierActivityEventModel.created_at.desc())
            .limit(1)
        )
        last_activity_row = (await session.execute(last_activity_stmt)).scalar_one_or_none()

        if last_activity_row is None or last_activity_row < inactivity_cutoff:
            days_inactive = (
                (now - last_activity_row).days if last_activity_row else _INACTIVITY_DAYS
            )
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="supplier_inactivity",
                severity="MEDIUM",
                title=f"Supplier inactivity: {supplier.name}",
                description=(
                    f"Supplier {supplier.name} has had no portal activity for "
                    f"{days_inactive} days. This may indicate disengagement risk."
                ),
                evidence=f"days_inactive={days_inactive}",
                rule_triggered=f"last_activity_at < now - {_INACTIVITY_DAYS}d",
                source_data={
                    "days_inactive": days_inactive,
                    "last_activity": str(last_activity_row) if last_activity_row else None,
                    **source_base,
                },
                confidence_score=0.75,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

    logger.info(
        "supplier_behaviour_monitor_completed",
        organization_id=organization_id,
        suppliers_checked=len(suppliers),
        findings_created=findings_created,
    )
    return findings_created


async def _maybe_escalate(finding, organization_id: str, session) -> None:
    try:
        from application.agent_monitoring.alert_service import evaluate_finding

        await evaluate_finding(finding, organization_id, session, agent_type="SUPPLIER_MONITOR")
    except Exception as exc:
        logger.warning("supplier_behaviour_escalation_failed", error=str(exc))
