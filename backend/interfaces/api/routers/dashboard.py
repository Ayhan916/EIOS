from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.user import User
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from interfaces.api.deps import get_current_user, get_db
from interfaces.api.schemas.dashboard import (
    DashboardResponse,
    MonthlyCount,
    RecentAssessmentItem,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_CLOSED_STATUSES = ("resolved", "verified")
_ACTIVE_STATUSES = ("open", "in_progress", "resolved", "verified")


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    org_id = current_user.organization_id

    # ── 1. Assessment aggregate ─────────────────────────────────────────────
    assess_agg = await session.execute(
        select(
            func.count(AssessmentModel.id).label("total"),
            func.avg(AssessmentModel.quality_score).label("avg_quality"),
        ).where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.status != "Deleted",
        )
    )
    agg_row = assess_agg.one()
    total_assessments = agg_row.total or 0
    avg_quality_score = float(round(agg_row.avg_quality, 4)) if agg_row.avg_quality else None

    # ── 2. Action status breakdown ──────────────────────────────────────────
    action_rows = await session.execute(
        select(
            RecommendationModel.action_status,
            func.count(RecommendationModel.id).label("cnt"),
        )
        .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(RecommendationModel.action_status)
    )
    action_breakdown: dict[str, int] = {s: 0 for s in _ACTIVE_STATUSES}
    for row in action_rows:
        action_breakdown[row.action_status] = row.cnt

    open_actions = action_breakdown.get("open", 0) + action_breakdown.get("in_progress", 0)
    total_actions = sum(action_breakdown.values())
    closed_actions = action_breakdown.get("resolved", 0) + action_breakdown.get("verified", 0)
    closed_actions_pct = round(closed_actions / total_actions * 100, 1) if total_actions else 0.0

    # ── 3. Overdue actions ──────────────────────────────────────────────────
    now = datetime.now(UTC)
    overdue_row = await session.execute(
        select(func.count(RecommendationModel.id))
        .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.status != "Deleted",
            RecommendationModel.due_date < now,
            RecommendationModel.action_status.notin_(list(_CLOSED_STATUSES)),
        )
    )
    overdue_actions = overdue_row.scalar() or 0

    # ── 4. Findings by severity ─────────────────────────────────────────────
    severity_rows = await session.execute(
        select(
            FindingModel.severity,
            func.count(FindingModel.id).label("cnt"),
        )
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(FindingModel.severity)
    )
    findings_by_severity: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for row in severity_rows:
        findings_by_severity[row.severity] = row.cnt

    high_risk_finding_count = findings_by_severity.get("High", 0)
    critical_finding_count = findings_by_severity.get("Critical", 0)

    # ── 5. Findings by category (map to E / S / G buckets) ─────────────────
    category_rows = await session.execute(
        select(
            FindingModel.category,
            func.count(FindingModel.id).label("cnt"),
        )
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(FindingModel.category)
    )
    findings_by_category: dict[str, int] = {"E": 0, "S": 0, "G": 0, "Other": 0}
    for row in category_rows:
        cat = (row.category or "").strip().upper()
        if cat.startswith("E"):
            findings_by_category["E"] += row.cnt
        elif cat.startswith("S"):
            findings_by_category["S"] += row.cnt
        elif cat.startswith("G"):
            findings_by_category["G"] += row.cnt
        else:
            findings_by_category["Other"] += row.cnt

    # ── 6. Recent assessments (last 8) with finding/risk counts ────────────
    finding_count_sub = (
        select(
            FindingModel.assessment_id,
            func.count(FindingModel.id).label("cnt"),
        )
        .group_by(FindingModel.assessment_id)
        .subquery()
    )
    from infrastructure.persistence.models.risk import RiskModel  # noqa: PLC0415

    risk_count_sub = (
        select(
            RiskModel.assessment_id,
            func.count(RiskModel.id).label("cnt"),
        )
        .group_by(RiskModel.assessment_id)
        .subquery()
    )

    recent_rows = await session.execute(
        select(
            AssessmentModel,
            func.coalesce(finding_count_sub.c.cnt, 0).label("finding_count"),
            func.coalesce(risk_count_sub.c.cnt, 0).label("risk_count"),
        )
        .outerjoin(finding_count_sub, AssessmentModel.id == finding_count_sub.c.assessment_id)
        .outerjoin(risk_count_sub, AssessmentModel.id == risk_count_sub.c.assessment_id)
        .where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.status != "Deleted",
        )
        .order_by(AssessmentModel.created_at.desc())
        .limit(8)
    )
    recent_assessments = [
        RecentAssessmentItem(
            id=row.AssessmentModel.id,
            title=row.AssessmentModel.title,
            status=row.AssessmentModel.status,
            assessment_type=row.AssessmentModel.assessment_type,
            quality_score=row.AssessmentModel.quality_score,
            finding_count=row.finding_count,
            risk_count=row.risk_count,
            created_at=(
                row.AssessmentModel.created_at.isoformat()
                if row.AssessmentModel.created_at
                else ""
            ),
        )
        for row in recent_rows
    ]

    # ── 7. Assessments over time (last 6 months, monthly) ──────────────────
    monthly_rows = await session.execute(
        select(
            func.to_char(AssessmentModel.created_at, "YYYY-MM").label("month"),
            func.count(AssessmentModel.id).label("cnt"),
        )
        .where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by("month")
        .order_by("month")
        .limit(12)
    )
    assessments_over_time = [
        MonthlyCount(month=row.month, count=row.cnt)
        for row in monthly_rows
    ]

    return DashboardResponse(
        total_assessments=total_assessments,
        avg_quality_score=avg_quality_score,
        action_status_breakdown=action_breakdown,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
        closed_actions_pct=closed_actions_pct,
        findings_by_severity=findings_by_severity,
        findings_by_category=findings_by_category,
        high_risk_finding_count=high_risk_finding_count,
        critical_finding_count=critical_finding_count,
        recent_assessments=recent_assessments,
        assessments_over_time=assessments_over_time,
    )
