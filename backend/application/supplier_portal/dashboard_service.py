"""M35 Supplier Dashboard Service.

Aggregates counts and recent activity for the supplier portal dashboard.

get_supplier_dashboard() — single call returning all dashboard widgets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SupplierDashboard:
    supplier_id: str
    open_findings: int = 0
    open_recommendations: int = 0
    overdue_actions: int = 0
    pending_questionnaires: int = 0
    requested_evidence: int = 0
    open_remediation_plans: int = 0
    recent_activity: list = field(default_factory=list)


async def get_supplier_dashboard(
    supplier_id: str,
    session=None,
) -> SupplierDashboard:
    """Load all dashboard widget data for a supplier in parallel queries."""
    from sqlalchemy import func, select

    from infrastructure.persistence.models.assessment import AssessmentModel
    from infrastructure.persistence.models.finding import FindingModel
    from infrastructure.persistence.models.recommendation import RecommendationModel
    from infrastructure.persistence.models.supplier_portal import (
        EvidenceRequestModel,
        QuestionnaireAssignmentModel,
        RemediationPlanModel,
        SupplierActivityEventModel,
    )

    now = datetime.now(UTC)

    # Open evidence requests
    ev_stmt = (
        select(func.count())
        .select_from(EvidenceRequestModel)
        .where(
            EvidenceRequestModel.supplier_id == supplier_id,
            EvidenceRequestModel.evidence_status.in_(["open", "in_progress"]),
        )
    )
    ev_count = (await session.execute(ev_stmt)).scalar_one()

    # Pending questionnaires (not yet submitted)
    q_stmt = (
        select(func.count())
        .select_from(QuestionnaireAssignmentModel)
        .where(
            QuestionnaireAssignmentModel.supplier_id == supplier_id,
            QuestionnaireAssignmentModel.questionnaire_status.in_(["assigned", "in_progress"]),
        )
    )
    q_count = (await session.execute(q_stmt)).scalar_one()

    # Open remediation plans
    rem_stmt = (
        select(func.count())
        .select_from(RemediationPlanModel)
        .where(
            RemediationPlanModel.supplier_id == supplier_id,
            RemediationPlanModel.remediation_status.in_(["open", "in_progress"]),
        )
    )
    rem_count = (await session.execute(rem_stmt)).scalar_one()

    # Overdue actions: remediation plans past due_date and not completed/verified
    overdue_stmt = (
        select(func.count())
        .select_from(RemediationPlanModel)
        .where(
            RemediationPlanModel.supplier_id == supplier_id,
            RemediationPlanModel.due_date < now,
            RemediationPlanModel.remediation_status.in_(["open", "in_progress"]),
        )
    )
    overdue_count = (await session.execute(overdue_stmt)).scalar_one()

    # F6: open findings from assessments linked to this supplier
    findings_subq = (
        select(AssessmentModel.id)
        .where(AssessmentModel.supplier_id == supplier_id)
        .scalar_subquery()
    )
    findings_stmt = (
        select(func.count())
        .select_from(FindingModel)
        .where(
            FindingModel.assessment_id.in_(findings_subq),
        )
    )
    findings_count = (await session.execute(findings_stmt)).scalar_one()

    # F6: open recommendations from the same assessments
    recs_stmt = (
        select(func.count())
        .select_from(RecommendationModel)
        .where(
            RecommendationModel.assessment_id.in_(findings_subq),
            RecommendationModel.action_status != "closed",
        )
    )
    recs_count = (await session.execute(recs_stmt)).scalar_one()

    # Recent activity (last 10 events)
    activity_stmt = (
        select(SupplierActivityEventModel)
        .where(SupplierActivityEventModel.supplier_id == supplier_id)
        .order_by(SupplierActivityEventModel.created_at.desc())
        .limit(10)
    )
    recent_events = list((await session.execute(activity_stmt)).scalars().all())

    return SupplierDashboard(
        supplier_id=supplier_id,
        open_findings=findings_count,
        open_recommendations=recs_count,
        overdue_actions=overdue_count,
        pending_questionnaires=q_count,
        requested_evidence=ev_count,
        open_remediation_plans=rem_count,
        recent_activity=recent_events,
    )
