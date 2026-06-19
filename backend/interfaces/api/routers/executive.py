"""
M29 Executive & Board Reporting API

All endpoints require EXECUTIVE role (admin or executive).
All endpoints enforce tenant isolation — users only see their own org.

Routes:
  GET  /executive/dashboard
  GET  /executive/kpi-trends?period=30|90|365
  GET  /executive/risk-register?limit=50&sort_by=...
  GET  /executive/heatmaps?view=country|sector|tier
  GET  /executive/action-effectiveness?period=30|90|365
  GET  /executive/governance-metrics?period=30|90|365
  POST /executive/reports              → 201
  GET  /executive/reports
  GET  /executive/reports/{id}
  GET  /executive/reports/{id}/pdf     → application/pdf
  DELETE /executive/reports/{id}       → 204 (admin only)
  POST /executive/schedules            → 201
  GET  /executive/schedules
  DELETE /executive/schedules/{id}     → 204
"""

from __future__ import annotations

from datetime import UTC, datetime, date, timedelta
from io import BytesIO
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

import application.audit as audit_factory
from application.executive import (
    ExecutiveSummaryInputs,
    compute_action_effectiveness,
    compute_governance_metrics,
    compute_kpi_trends,
    compute_portfolio_summary,
    generate_executive_summary,
)
from application.scoring import categorize_pillar
from domain.board_report import BoardReport, ReportSchedule
from domain.enums import EntityStatus, UserRole
from domain.user import User
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.organization import OrganizationModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.review_action import ReviewActionModel
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel
from infrastructure.persistence.repositories import (
    SQLAuditEventRepository,
    SQLBoardReportRepository,
    SQLReportScheduleRepository,
    SQLSupplierRepository,
    SQLSupplierScoreRepository,
)
from infrastructure.reporting.board_pdf_renderer import render_board_report_pdf
from interfaces.api.deps import (
    get_audit_event_repo,
    get_board_report_repo,
    get_current_user,
    get_db,
    get_report_schedule_repo,
    get_supplier_repo,
    get_supplier_score_repo,
    require_admin,
    require_executive,
    scope_gate,
)
from interfaces.api.routers.api_platform import dispatch_webhook_event
from interfaces.api.schemas.executive import (
    ActionEffectivenessResponse,
    BoardReportDetail,
    BoardReportRequest,
    BoardReportSummary,
    ExecutiveDashboard,
    ExecutiveHeatmapResponse,
    GovernanceMetricsResponse,
    GovernanceSummary,
    HeatmapBucket,
    KPITrendResponse,
    MonthlyDataPoint,
    PortfolioSummary,
    ActionSummary,
    ReportScheduleRequest,
    ReportScheduleResponse,
    RiskRegisterEntry,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/executive",
    tags=["executive"],
    dependencies=[Depends(require_executive), Depends(scope_gate("executive:read"))],
)

_CLOSED_STATUSES = ("resolved", "verified")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _assert_org(user: User) -> str:
    if not user.organization_id:
        raise HTTPException(status_code=403, detail="No organization context")
    return user.organization_id


async def _latest_scores_for_org(
    session: AsyncSession, org_id: str
) -> list[SupplierScoreModel]:
    """Latest score per supplier for the org (derived table approach)."""
    latest_subq = (
        select(
            SupplierScoreModel.supplier_id,
            func.max(SupplierScoreModel.created_at).label("max_created"),
        )
        .where(SupplierScoreModel.organization_id == org_id)
        .group_by(SupplierScoreModel.supplier_id)
        .subquery()
    )
    stmt = select(SupplierScoreModel).join(
        latest_subq,
        (SupplierScoreModel.supplier_id == latest_subq.c.supplier_id)
        & (SupplierScoreModel.created_at == latest_subq.c.max_created),
    )
    return list((await session.execute(stmt)).scalars().all())


async def _action_counts(
    session: AsyncSession, org_id: str, since: datetime | None = None
) -> tuple[int, int, int]:
    """Return (total, open, overdue) recommendation counts for the org."""
    now = datetime.now(UTC)
    base = (
        select(RecommendationModel.action_status, RecommendationModel.due_date)
        .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
        .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
        .where(
            SupplierModel.organization_id == org_id,
            AssessmentModel.status != "Deleted",
            RecommendationModel.status != "Deleted",
        )
    )
    if since:
        base = base.where(RecommendationModel.created_at >= since)
    rows = (await session.execute(base)).all()

    total = len(rows)
    open_count = sum(1 for r in rows if r.action_status not in _CLOSED_STATUSES)
    overdue = sum(
        1 for r in rows
        if r.action_status not in _CLOSED_STATUSES
        and r.due_date and r.due_date < now
    )
    return total, open_count, overdue


async def _critical_findings_count(session: AsyncSession, org_id: str) -> int:
    row = (
        await session.execute(
            select(func.count(FindingModel.id))
            .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                AssessmentModel.status != "Deleted",
                FindingModel.status != "Deleted",
                FindingModel.severity == "Critical",
            )
        )
    ).scalar_one()
    return row or 0


async def _assessment_review_counts(
    session: AsyncSession, org_id: str
) -> tuple[int, int]:
    """Return (awaiting_review, approved) counts for the org."""
    rows = (
        await session.execute(
            select(AssessmentModel.review_status)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                AssessmentModel.status != "Deleted",
                AssessmentModel.supplier_id.isnot(None),
            )
        )
    ).scalars().all()
    awaiting = sum(1 for s in rows if s in ("InReview", "ChangesRequested"))
    approved = sum(1 for s in rows if s == "Approved")
    return awaiting, approved


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=ExecutiveDashboard)
async def get_executive_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
) -> ExecutiveDashboard:
    """Portfolio KPI dashboard for executives and board members."""
    org_id = _assert_org(current_user)

    _, total_suppliers = await supplier_repo.list_org_paged(
        organization_id=org_id, page=1, page_size=1
    )

    score_models = await _latest_scores_for_org(session, org_id)
    scores_dicts = [
        {
            "esg_score": s.esg_score,
            "risk_score": s.risk_score,
            "risk_band": s.risk_band,
            "trend": s.trend,
        }
        for s in score_models
    ]

    total_actions, open_actions, overdue_actions = await _action_counts(session, org_id)
    awaiting_review, assessments_approved = await _assessment_review_counts(session, org_id)
    crit_findings = await _critical_findings_count(session, org_id)

    snapshot = compute_portfolio_summary(
        total_suppliers=total_suppliers,
        scores=scores_dicts,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
        total_actions=total_actions,
        assessments_awaiting_review=awaiting_review,
        assessments_approved=assessments_approved,
        critical_findings_total=crit_findings,
    )

    return ExecutiveDashboard(
        portfolio_summary=PortfolioSummary(
            total_suppliers=snapshot.total_suppliers,
            scored_suppliers=snapshot.scored_suppliers,
            critical_risk_suppliers=snapshot.critical_risk_suppliers,
            high_risk_suppliers=snapshot.high_risk_suppliers,
            moderate_risk_suppliers=snapshot.moderate_risk_suppliers,
            low_risk_suppliers=snapshot.low_risk_suppliers,
            improving_suppliers=snapshot.improving_suppliers,
            deteriorating_suppliers=snapshot.deteriorating_suppliers,
            avg_esg_score=snapshot.avg_esg_score,
            avg_risk_score=snapshot.avg_risk_score,
            risk_distribution=snapshot.risk_distribution,
        ),
        action_summary=ActionSummary(
            open_actions=snapshot.open_actions,
            overdue_actions=snapshot.overdue_actions,
            total_actions=snapshot.total_actions,
            resolution_rate=snapshot.resolution_rate,
        ),
        governance_summary=GovernanceSummary(
            assessments_awaiting_review=snapshot.assessments_awaiting_review,
            assessments_approved=snapshot.assessments_approved,
            critical_findings_total=snapshot.critical_findings_total,
        ),
    )


# ── KPI Trends ────────────────────────────────────────────────────────────────


@router.get("/kpi-trends", response_model=KPITrendResponse)
async def get_kpi_trends(
    period: int = Query(default=90, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> KPITrendResponse:
    """Monthly KPI trend data for the last `period` days."""
    org_id = _assert_org(current_user)
    since = datetime.now(UTC) - timedelta(days=period)

    # Use latest score per supplier per month to avoid double-counting suppliers
    # that have multiple score rows within the same calendar month.
    _month_fn = func.to_char(SupplierScoreModel.created_at, literal_column("'YYYY-MM'"))
    latest_per_month_subq = (
        select(
            SupplierScoreModel.supplier_id.label("supplier_id"),
            _month_fn.label("month"),
            func.max(SupplierScoreModel.created_at).label("max_created"),
        )
        .where(
            SupplierScoreModel.organization_id == org_id,
            SupplierScoreModel.created_at >= since,
        )
        .group_by(SupplierScoreModel.supplier_id, _month_fn)
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                latest_per_month_subq.c.month,
                func.avg(SupplierScoreModel.esg_score).label("avg_esg"),
                func.avg(SupplierScoreModel.risk_score).label("avg_risk"),
                func.count(SupplierScoreModel.supplier_id).label("count"),
                func.sum(case((SupplierScoreModel.risk_band == "Critical", 1), else_=0)).label("critical"),
                func.sum(case((SupplierScoreModel.risk_band == "High", 1), else_=0)).label("high"),
                func.sum(case((SupplierScoreModel.risk_band == "Moderate", 1), else_=0)).label("moderate"),
                func.sum(case((SupplierScoreModel.risk_band == "Low", 1), else_=0)).label("low"),
            )
            .join(
                latest_per_month_subq,
                (SupplierScoreModel.supplier_id == latest_per_month_subq.c.supplier_id)
                & (SupplierScoreModel.created_at == latest_per_month_subq.c.max_created),
            )
            .group_by(latest_per_month_subq.c.month)
            .order_by(latest_per_month_subq.c.month)
        )
    ).all()

    monthly_rows = [
        {
            "month": r.month,
            "avg_esg": float(r.avg_esg) if r.avg_esg is not None else None,
            "avg_risk": float(r.avg_risk) if r.avg_risk is not None else None,
            "count": int(r.count),
            "dist": {
                "Critical": int(r.critical or 0),
                "High": int(r.high or 0),
                "Moderate": int(r.moderate or 0),
                "Low": int(r.low or 0),
            },
        }
        for r in rows
    ]

    result = compute_kpi_trends(monthly_rows, period_days=period)

    return KPITrendResponse(
        period_days=result.period_days,
        data_points=[
            MonthlyDataPoint(
                month=p.month,
                avg_esg_score=p.avg_esg_score,
                avg_risk_score=p.avg_risk_score,
                supplier_count=p.supplier_count,
                high_risk_count=p.high_risk_count,
                critical_risk_count=p.critical_risk_count,
                risk_distribution=p.risk_distribution,
            )
            for p in result.data_points
        ],
        esg_delta=result.esg_delta,
        risk_delta=result.risk_delta,
    )


# ── Risk Register ─────────────────────────────────────────────────────────────


@router.get("/risk-register", response_model=list[RiskRegisterEntry])
async def get_risk_register(
    limit: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(
        default="risk_score",
        pattern="^(risk_score|esg_score|critical_findings|overdue_actions)$",
    ),
    risk_band: str | None = Query(default=None),
    country: str | None = Query(default=None),
    supplier_tier: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
) -> list[RiskRegisterEntry]:
    """Executive risk register — all suppliers ranked by risk."""
    org_id = _assert_org(current_user)

    score_models = await _latest_scores_for_org(session, org_id)
    all_suppliers, _ = await supplier_repo.list_org_paged(
        organization_id=org_id, page=1, page_size=10000,
        country=country, supplier_tier=supplier_tier,
    )
    supplier_map = {s.id: s for s in all_suppliers}

    # Per-supplier critical finding counts (org-scoped)
    crit_rows = (
        await session.execute(
            select(AssessmentModel.supplier_id, func.count(FindingModel.id).label("cnt"))
            .join(FindingModel, FindingModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                AssessmentModel.status != "Deleted",
                FindingModel.status != "Deleted",
                FindingModel.severity == "Critical",
            )
            .group_by(AssessmentModel.supplier_id)
        )
    ).all()
    crit_map = {r.supplier_id: r.cnt for r in crit_rows if r.supplier_id}

    now = datetime.now(UTC)
    overdue_rows = (
        await session.execute(
            select(AssessmentModel.supplier_id, func.count(RecommendationModel.id).label("cnt"))
            .join(RecommendationModel, RecommendationModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                AssessmentModel.status != "Deleted",
                RecommendationModel.status != "Deleted",
                RecommendationModel.due_date < now,
                RecommendationModel.action_status.notin_(list(_CLOSED_STATUSES)),
            )
            .group_by(AssessmentModel.supplier_id)
        )
    ).all()
    overdue_map = {r.supplier_id: r.cnt for r in overdue_rows if r.supplier_id}

    entries: list[RiskRegisterEntry] = []
    for score in score_models:
        sup = supplier_map.get(score.supplier_id)
        if sup is None:
            continue
        if risk_band and score.risk_band != risk_band:
            continue

        entries.append(
            RiskRegisterEntry(
                rank=0,
                supplier_id=score.supplier_id,
                supplier_name=sup.name,
                country=sup.country or "",
                industry=sup.industry or "",
                supplier_tier=sup.supplier_tier if isinstance(sup.supplier_tier, str) else sup.supplier_tier.value,
                risk_score=score.risk_score,
                risk_band=score.risk_band,
                esg_score=score.esg_score,
                trend=score.trend,
                trend_delta=score.trend_delta,
                critical_findings=crit_map.get(score.supplier_id, 0),
                overdue_actions=overdue_map.get(score.supplier_id, 0),
            )
        )

    if sort_by == "risk_score":
        entries.sort(key=lambda e: e.risk_score, reverse=True)
    elif sort_by == "esg_score":
        entries.sort(key=lambda e: e.esg_score)
    elif sort_by == "critical_findings":
        entries.sort(key=lambda e: e.critical_findings, reverse=True)
    elif sort_by == "overdue_actions":
        entries.sort(key=lambda e: e.overdue_actions, reverse=True)

    for i, entry in enumerate(entries[:limit], start=1):
        entries[i - 1] = entry.model_copy(update={"rank": i})

    return entries[:limit]


# ── Executive Heatmaps ────────────────────────────────────────────────────────


@router.get("/heatmaps", response_model=ExecutiveHeatmapResponse)
async def get_executive_heatmap(
    view: str = Query(default="country", pattern="^(country|sector|tier)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExecutiveHeatmapResponse:
    """Aggregate risk heatmap by country, sector (industry), or supplier tier."""
    org_id = _assert_org(current_user)

    score_models = await _latest_scores_for_org(session, org_id)
    score_by_supplier = {s.supplier_id: s for s in score_models}

    if not score_by_supplier:
        return ExecutiveHeatmapResponse(view=view, buckets=[])

    supplier_ids = list(score_by_supplier.keys())
    suppliers = (
        await session.execute(
            select(
                SupplierModel.id,
                SupplierModel.country,
                SupplierModel.industry,
                SupplierModel.supplier_tier,
            )
            .where(
                SupplierModel.id.in_(supplier_ids),
                SupplierModel.organization_id == org_id,
                SupplierModel.status.notin_(["Deleted", "Archived"]),
            )
        )
    ).all()

    # Aggregate per label
    bucket_data: dict[str, dict] = {}
    for sup in suppliers:
        if view == "country":
            label = sup.country or "Unknown"
        elif view == "sector":
            label = sup.industry or "Unknown"
        else:  # tier
            label = sup.supplier_tier if isinstance(sup.supplier_tier, str) else str(sup.supplier_tier)

        score = score_by_supplier.get(sup.id)
        if score is None:
            continue

        if label not in bucket_data:
            bucket_data[label] = {"count": 0, "total_risk": 0.0, "critical": 0, "high": 0}

        bucket_data[label]["count"] += 1
        bucket_data[label]["total_risk"] += score.risk_score
        if score.risk_band == "Critical":
            bucket_data[label]["critical"] += 1
        if score.risk_band in ("High", "Critical"):
            bucket_data[label]["high"] += 1

    buckets = [
        HeatmapBucket(
            label=label,
            supplier_count=d["count"],
            avg_risk_score=round(d["total_risk"] / d["count"], 1) if d["count"] else 0.0,
            critical_count=d["critical"],
            high_count=d["high"],
        )
        for label, d in bucket_data.items()
    ]
    buckets.sort(key=lambda b: b.avg_risk_score, reverse=True)

    return ExecutiveHeatmapResponse(view=view, buckets=buckets)


# ── Action Effectiveness ──────────────────────────────────────────────────────


@router.get("/action-effectiveness", response_model=ActionEffectivenessResponse)
async def get_action_effectiveness(
    period: int = Query(default=30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActionEffectivenessResponse:
    """Measure whether actions reduce risk — resolution metrics."""
    org_id = _assert_org(current_user)
    since = datetime.now(UTC) - timedelta(days=period)
    now = datetime.now(UTC)

    # Actions opened this period
    opened_rows = (
        await session.execute(
            select(
                RecommendationModel.action_status,
                RecommendationModel.created_at,
                RecommendationModel.updated_at,
                RecommendationModel.due_date,
            )
            .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                AssessmentModel.status != "Deleted",
                RecommendationModel.status != "Deleted",
                RecommendationModel.created_at >= since,
            )
        )
    ).all()

    opened_this_period = len(opened_rows)
    closed_this_period = sum(
        1 for r in opened_rows if r.action_status in _CLOSED_STATUSES
    )

    # Current open and overdue (all time)
    _, total_open, total_overdue = await _action_counts(session, org_id)

    # Avg resolution time for actions closed in this period
    resolution_times: list[float] = []
    for r in opened_rows:
        if r.action_status in _CLOSED_STATUSES and r.created_at and r.updated_at:
            delta_days = (r.updated_at - r.created_at).total_seconds() / 86400
            if delta_days >= 0:
                resolution_times.append(delta_days)

    avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None

    metrics = compute_action_effectiveness(
        opened_this_period=opened_this_period,
        closed_this_period=closed_this_period,
        total_open=total_open,
        total_overdue=total_overdue,
        avg_resolution_days=avg_resolution,
    )

    return ActionEffectivenessResponse(**metrics)


# ── Governance Metrics ────────────────────────────────────────────────────────


@router.get("/governance-metrics", response_model=GovernanceMetricsResponse)
async def get_governance_metrics(
    period: int = Query(default=30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GovernanceMetricsResponse:
    """Review governance effectiveness — turnaround, approval rates."""
    org_id = _assert_org(current_user)
    since = datetime.now(UTC) - timedelta(days=period)

    # Review action decisions in period
    decisions = (
        await session.execute(
            select(ReviewActionModel.action_type, ReviewActionModel.created_at)
            .join(AssessmentModel, ReviewActionModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                ReviewActionModel.created_at >= since,
            )
        )
    ).all()

    total = len(decisions)
    approved = sum(1 for d in decisions if d.action_type == "approve")
    rejected = sum(1 for d in decisions if d.action_type == "reject")
    changes = sum(1 for d in decisions if d.action_type == "request_changes")

    # Avg review turnaround: time from assessment.created_at to first review decision
    review_times_days: list[float] = []
    assess_review_rows = (
        await session.execute(
            select(
                AssessmentModel.created_at.label("created"),
                func.min(ReviewActionModel.created_at).label("first_decision"),
            )
            .join(ReviewActionModel, ReviewActionModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                ReviewActionModel.created_at >= since,
            )
            .group_by(AssessmentModel.id, AssessmentModel.created_at)
        )
    ).all()

    for row in assess_review_rows:
        if row.created and row.first_decision:
            delta = (row.first_decision - row.created).total_seconds() / 86400
            if delta >= 0:
                review_times_days.append(delta)

    avg_review = round(sum(review_times_days) / len(review_times_days), 1) if review_times_days else None

    awaiting, approved_total = await _assessment_review_counts(session, org_id)

    metrics = compute_governance_metrics(
        total_decisions=total,
        approved=approved,
        rejected=rejected,
        changes_requested=changes,
        avg_review_days=avg_review,
    )

    return GovernanceMetricsResponse(**metrics)


# ── Board Reports ─────────────────────────────────────────────────────────────


@router.post(
    "/reports",
    response_model=BoardReportDetail,
    status_code=status.HTTP_201_CREATED,
)
async def generate_board_report(
    body: BoardReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    report_repo: SQLBoardReportRepository = Depends(get_board_report_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> BoardReportDetail:
    """Generate and persist an immutable board report snapshot."""
    org_id = _assert_org(current_user)
    now = datetime.now(UTC)

    try:
        period_start = date.fromisoformat(body.period_start)
        period_end = date.fromisoformat(body.period_end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {exc}") from exc

    # Freeze organization name at generation time (L4 fix)
    org_name_row = (
        await session.execute(
            select(OrganizationModel.name).where(OrganizationModel.id == org_id)
        )
    ).scalar_one_or_none()
    org_name = org_name_row or "Organisation"

    # Gather all data needed for the report
    _, total_suppliers = await supplier_repo.list_org_paged(
        organization_id=org_id, page=1, page_size=1
    )
    score_models = await _latest_scores_for_org(session, org_id)
    scores_dicts = [
        {
            "esg_score": s.esg_score,
            "risk_score": s.risk_score,
            "risk_band": s.risk_band,
            "trend": s.trend,
            "trend_delta": s.trend_delta,
            "supplier_id": s.supplier_id,
        }
        for s in score_models
    ]

    total_actions, open_actions, overdue_actions = await _action_counts(session, org_id)
    awaiting_review, assessments_approved = await _assessment_review_counts(session, org_id)
    crit_findings_total = await _critical_findings_count(session, org_id)

    # Portfolio snapshot
    snapshot = compute_portfolio_summary(
        total_suppliers=total_suppliers,
        scores=scores_dicts,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
        total_actions=total_actions,
        assessments_awaiting_review=awaiting_review,
        assessments_approved=assessments_approved,
        critical_findings_total=crit_findings_total,
    )

    # KPI trends (last kpi_period_days) — latest score per supplier per month only
    trend_since = now - timedelta(days=body.kpi_period_days)
    _trend_month_fn = func.to_char(SupplierScoreModel.created_at, literal_column("'YYYY-MM'"))
    trend_latest_subq = (
        select(
            SupplierScoreModel.supplier_id.label("supplier_id"),
            _trend_month_fn.label("month"),
            func.max(SupplierScoreModel.created_at).label("max_created"),
        )
        .where(
            SupplierScoreModel.organization_id == org_id,
            SupplierScoreModel.created_at >= trend_since,
        )
        .group_by(SupplierScoreModel.supplier_id, _trend_month_fn)
        .subquery()
    )
    trend_rows = (
        await session.execute(
            select(
                trend_latest_subq.c.month,
                func.avg(SupplierScoreModel.esg_score).label("avg_esg"),
                func.avg(SupplierScoreModel.risk_score).label("avg_risk"),
                func.count(SupplierScoreModel.supplier_id).label("count"),
                func.sum(case((SupplierScoreModel.risk_band == "Critical", 1), else_=0)).label("critical"),
                func.sum(case((SupplierScoreModel.risk_band == "High", 1), else_=0)).label("high"),
                func.sum(case((SupplierScoreModel.risk_band == "Moderate", 1), else_=0)).label("moderate"),
                func.sum(case((SupplierScoreModel.risk_band == "Low", 1), else_=0)).label("low"),
            )
            .join(
                trend_latest_subq,
                (SupplierScoreModel.supplier_id == trend_latest_subq.c.supplier_id)
                & (SupplierScoreModel.created_at == trend_latest_subq.c.max_created),
            )
            .group_by(trend_latest_subq.c.month)
            .order_by(trend_latest_subq.c.month)
        )
    ).all()
    monthly_rows = [
        {
            "month": r.month,
            "avg_esg": float(r.avg_esg) if r.avg_esg is not None else None,
            "avg_risk": float(r.avg_risk) if r.avg_risk is not None else None,
            "count": int(r.count),
            "dist": {
                "Critical": int(r.critical or 0),
                "High": int(r.high or 0),
                "Moderate": int(r.moderate or 0),
                "Low": int(r.low or 0),
            },
        }
        for r in trend_rows
    ]
    kpi_result = compute_kpi_trends(monthly_rows, period_days=body.kpi_period_days)

    # Top high-risk suppliers (top 10)
    all_suppliers, _ = await supplier_repo.list_org_paged(
        organization_id=org_id, page=1, page_size=10000
    )
    supplier_map = {s.id: s for s in all_suppliers}

    sorted_by_risk = sorted(score_models, key=lambda s: s.risk_score, reverse=True)
    top_high_risk = [
        {
            "supplier_id": s.supplier_id,
            "supplier_name": supplier_map[s.supplier_id].name if s.supplier_id in supplier_map else "",
            "risk_score": s.risk_score,
            "risk_band": s.risk_band,
            "trend": s.trend,
            "trend_delta": s.trend_delta,
            "country": supplier_map[s.supplier_id].country if s.supplier_id in supplier_map else "",
            "esg_score": s.esg_score,
        }
        for s in sorted_by_risk[:10]
        if s.risk_band in ("High", "Critical")
    ]

    top_deteriorating = sorted(
        [
            {
                "supplier_id": s.supplier_id,
                "supplier_name": supplier_map[s.supplier_id].name if s.supplier_id in supplier_map else "",
                "risk_score": s.risk_score,
                "risk_band": s.risk_band,
                "trend": s.trend,
                "trend_delta": s.trend_delta,
            }
            for s in score_models
            if s.trend == "Deteriorating" and s.supplier_id in supplier_map
        ],
        key=lambda x: x["trend_delta"],
    )[:10]

    # Critical findings for report
    crit_finding_rows = (
        await session.execute(
            select(
                FindingModel.title,
                FindingModel.category,
                AssessmentModel.supplier_id,
            )
            .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                AssessmentModel.status != "Deleted",
                FindingModel.status != "Deleted",
                FindingModel.severity == "Critical",
            )
            .limit(20)
        )
    ).all()

    critical_findings_summary = [
        {
            "supplier_name": supplier_map[r.supplier_id].name if r.supplier_id in supplier_map else "",
            "title": r.title,
            "category": r.category,
            "pillar": categorize_pillar(r.category or "", r.title or ""),
        }
        for r in crit_finding_rows
    ]

    # Overdue actions for report
    overdue_rows = (
        await session.execute(
            select(
                RecommendationModel.title,
                RecommendationModel.due_date,
                AssessmentModel.supplier_id,
            )
            .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                AssessmentModel.status != "Deleted",
                RecommendationModel.status != "Deleted",
                RecommendationModel.due_date < now,
                RecommendationModel.action_status.notin_(list(_CLOSED_STATUSES)),
            )
            .order_by(RecommendationModel.due_date.asc())
            .limit(20)
        )
    ).all()

    overdue_actions_summary = [
        {
            "supplier_name": supplier_map[r.supplier_id].name if r.supplier_id in supplier_map else "",
            "title": r.title,
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "days_overdue": max(0, (now.date() - r.due_date).days) if r.due_date else 0,
        }
        for r in overdue_rows
    ]

    # Governance metrics — decisions and avg review turnaround (L3 fix)
    gov_since = now - timedelta(days=body.kpi_period_days)
    gov_decisions = (
        await session.execute(
            select(ReviewActionModel.action_type)
            .join(AssessmentModel, ReviewActionModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                ReviewActionModel.created_at >= gov_since,
            )
        )
    ).scalars().all()

    gov_approved = sum(1 for d in gov_decisions if d == "approve")
    gov_rejected = sum(1 for d in gov_decisions if d == "reject")
    gov_changes = sum(1 for d in gov_decisions if d == "request_changes")

    assess_review_rows = (
        await session.execute(
            select(
                AssessmentModel.created_at.label("created"),
                func.min(ReviewActionModel.created_at).label("first_decision"),
            )
            .join(ReviewActionModel, ReviewActionModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                ReviewActionModel.created_at >= gov_since,
            )
            .group_by(AssessmentModel.id, AssessmentModel.created_at)
        )
    ).all()
    review_times: list[float] = []
    for row in assess_review_rows:
        if row.created and row.first_decision:
            delta = (row.first_decision - row.created).total_seconds() / 86400
            if delta >= 0:
                review_times.append(delta)
    avg_review_days = round(sum(review_times) / len(review_times), 1) if review_times else None

    gov_metrics = compute_governance_metrics(
        total_decisions=len(gov_decisions),
        approved=gov_approved,
        rejected=gov_rejected,
        changes_requested=gov_changes,
        avg_review_days=avg_review_days,
    )

    # Action effectiveness — actions opened/closed during reporting period (L2 fix)
    period_start_dt = datetime(period_start.year, period_start.month, period_start.day, tzinfo=UTC)
    period_end_dt = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59, tzinfo=UTC)
    action_eff_rows = (
        await session.execute(
            select(
                RecommendationModel.action_status,
                RecommendationModel.created_at,
                RecommendationModel.updated_at,
            )
            .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == org_id,
                AssessmentModel.status != "Deleted",
                RecommendationModel.status != "Deleted",
                RecommendationModel.created_at >= period_start_dt,
                RecommendationModel.created_at <= period_end_dt,
            )
        )
    ).all()
    opened_this_period = len(action_eff_rows)
    closed_this_period = sum(1 for r in action_eff_rows if r.action_status in _CLOSED_STATUSES)
    resolution_times: list[float] = []
    for r in action_eff_rows:
        if r.action_status in _CLOSED_STATUSES and r.created_at and r.updated_at:
            delta_days = (r.updated_at - r.created_at).total_seconds() / 86400
            if delta_days >= 0:
                resolution_times.append(delta_days)
    avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None

    action_eff = compute_action_effectiveness(
        opened_this_period=opened_this_period,
        closed_this_period=closed_this_period,
        total_open=open_actions,
        total_overdue=overdue_actions,
        avg_resolution_days=avg_resolution,
    )

    # Determine top risk country and sector for narrative
    country_risk: dict[str, list[float]] = {}
    sector_risk: dict[str, list[float]] = {}
    for s in score_models:
        sup = supplier_map.get(s.supplier_id)
        if sup:
            if sup.country:
                country_risk.setdefault(sup.country, []).append(s.risk_score)
            if sup.industry:
                sector_risk.setdefault(sup.industry, []).append(s.risk_score)

    top_country = max(country_risk, key=lambda k: sum(country_risk[k]) / len(country_risk[k])) if country_risk else None
    top_sector = max(sector_risk, key=lambda k: sum(sector_risk[k]) / len(sector_risk[k])) if sector_risk else None

    # Generate executive summary
    summary_inputs = ExecutiveSummaryInputs(
        total_suppliers=total_suppliers,
        scored_suppliers=snapshot.scored_suppliers,
        critical_risk_count=snapshot.critical_risk_suppliers,
        high_risk_count=snapshot.high_risk_suppliers,
        moderate_risk_count=snapshot.moderate_risk_suppliers,
        low_risk_count=snapshot.low_risk_suppliers,
        improving_count=snapshot.improving_suppliers,
        deteriorating_count=snapshot.deteriorating_suppliers,
        avg_esg_score=snapshot.avg_esg_score,
        avg_risk_score=snapshot.avg_risk_score,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
        resolved_actions=total_actions - open_actions,
        assessments_awaiting_review=awaiting_review,
        assessments_approved=assessments_approved,
        critical_findings_total=crit_findings_total,
        top_risk_country=top_country,
        top_risk_sector=top_sector,
        period_label=f"for the period {body.period_start} to {body.period_end}",
    )
    executive_summary = generate_executive_summary(summary_inputs)

    # Pre-generate the report ID so report_data["meta"]["report_id"] is set before the
    # first (and only) save, making the trigger-protected report_data fully immutable.
    report_id = str(uuid4())

    # Assemble report_data (frozen snapshot)
    report_data = {
        "meta": {
            "title": body.title,
            "report_version": "1.0",
            "generated_at": now.isoformat(),
            "report_id": report_id,
            "period_start": body.period_start,
            "period_end": body.period_end,
            "organization_name": org_name,
        },
        "executive_summary": executive_summary,
        "portfolio_summary": {
            "total_suppliers": snapshot.total_suppliers,
            "scored_suppliers": snapshot.scored_suppliers,
            "critical_risk_suppliers": snapshot.critical_risk_suppliers,
            "high_risk_suppliers": snapshot.high_risk_suppliers,
            "moderate_risk_suppliers": snapshot.moderate_risk_suppliers,
            "low_risk_suppliers": snapshot.low_risk_suppliers,
            "improving_suppliers": snapshot.improving_suppliers,
            "deteriorating_suppliers": snapshot.deteriorating_suppliers,
            "avg_esg_score": snapshot.avg_esg_score,
            "avg_risk_score": snapshot.avg_risk_score,
            "risk_distribution": snapshot.risk_distribution,
        },
        "action_summary": {
            "open_actions": open_actions,
            "overdue_actions": overdue_actions,
            "total_actions": total_actions,
            "resolution_rate": snapshot.resolution_rate,
        },
        "governance_summary": {
            "assessments_awaiting_review": awaiting_review,
            "assessments_approved": assessments_approved,
            "critical_findings_total": crit_findings_total,
        },
        "top_high_risk_suppliers": top_high_risk,
        "top_deteriorating_suppliers": top_deteriorating,
        "critical_findings_summary": critical_findings_summary,
        "overdue_actions_summary": overdue_actions_summary,
        "governance_metrics": {
            **gov_metrics,
            "assessments_awaiting_review": awaiting_review,
            "assessments_approved": assessments_approved,
        },
        "action_effectiveness": action_eff,
        "kpi_trends": {
            "period_days": body.kpi_period_days,
            "data_points": [
                {
                    "month": p.month,
                    "avg_esg_score": p.avg_esg_score,
                    "avg_risk_score": p.avg_risk_score,
                    "supplier_count": p.supplier_count,
                    "high_risk_count": p.high_risk_count,
                    "critical_risk_count": p.critical_risk_count,
                    "risk_distribution": p.risk_distribution,
                }
                for p in kpi_result.data_points
            ],
            "esg_delta": kpi_result.esg_delta,
            "risk_delta": kpi_result.risk_delta,
        },
    }

    # Supplier snapshot for audit (top 50 by risk score)
    snapshot_entries = [
        {
            "supplier_id": s.supplier_id,
            "supplier_name": supplier_map[s.supplier_id].name if s.supplier_id in supplier_map else "",
            "esg_score": s.esg_score,
            "risk_score": s.risk_score,
            "risk_band": s.risk_band,
            "trend": s.trend,
            "calculated_at": s.created_at.isoformat(),
        }
        for s in sorted_by_risk[:50]
        if s.supplier_id in supplier_map
    ]
    supplier_snapshot = {
        "supplier_snapshot_metadata": {
            "total_supplier_count": total_suppliers,
            "snapshot_supplier_count": len(snapshot_entries),
        },
        "suppliers": snapshot_entries,
    }

    # Persist — immutable after this point (report_id already embedded in report_data)
    report = BoardReport(
        id=report_id,
        organization_id=org_id,
        title=body.title,
        report_version="1.0",
        period_start=period_start,
        period_end=period_end,
        executive_summary=executive_summary,
        report_data=report_data,
        supplier_snapshot=supplier_snapshot,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    saved = await report_repo.save(report)

    await audit_repo.save(
        audit_factory.board_report_generated(
            report_id=saved.id,
            actor_id=current_user.id,
            actor_email=current_user.email,
            organization_id=org_id,
            period_start=body.period_start,
            period_end=body.period_end,
        )
    )
    try:
        from interfaces.api.routers.metrics import counters as _m  # noqa: PLC0415
        _m.record_board_report_generated()
    except Exception:  # noqa: BLE001
        pass

    logger.info("board_report_generated", report_id=saved.id, org_id=org_id)
    background_tasks.add_task(
        dispatch_webhook_event,
        org_id,
        "board_report.generated",
        {"report_id": saved.id, "title": saved.title, "period_start": body.period_start, "period_end": body.period_end},
    )
    return _to_detail(saved)


@router.get("/reports", response_model=list[BoardReportSummary])
async def list_board_reports(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    report_repo: SQLBoardReportRepository = Depends(get_board_report_repo),
) -> list[BoardReportSummary]:
    org_id = _assert_org(current_user)
    reports = await report_repo.list_for_org(org_id, limit=limit)
    return [
        BoardReportSummary(
            id=r.id,
            title=r.title,
            report_version=r.report_version,
            period_start=r.period_start.isoformat(),
            period_end=r.period_end.isoformat(),
            generated_at=r.created_at.isoformat(),
            executive_summary=r.executive_summary[:500],
        )
        for r in reports
    ]


@router.get("/reports/{report_id}", response_model=BoardReportDetail)
async def get_board_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    report_repo: SQLBoardReportRepository = Depends(get_board_report_repo),
) -> BoardReportDetail:
    org_id = _assert_org(current_user)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_detail(report)


@router.get("/reports/{report_id}/pdf")
async def download_board_report_pdf(
    report_id: str,
    current_user: User = Depends(get_current_user),
    report_repo: SQLBoardReportRepository = Depends(get_board_report_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> StreamingResponse:
    """Download PDF generated from the stored report_data snapshot."""
    org_id = _assert_org(current_user)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Report not found")

    # Read organization name from the frozen snapshot — never from the live DB (L4 fix)
    org_name = report.report_data.get("meta", {}).get("organization_name", "Organisation")

    pdf_bytes = render_board_report_pdf(
        report_data=report.report_data,
        report_id=report.id,
        organization_name=org_name,
    )

    await audit_repo.save(
        audit_factory.board_report_downloaded(
            report_id=report.id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    )
    try:
        from interfaces.api.routers.metrics import counters as _m  # noqa: PLC0415
        _m.record_board_report_downloaded()
    except Exception:  # noqa: BLE001
        pass

    filename = f"board-report-{report.period_start.isoformat()}-{report.period_end.isoformat()}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board_report(
    report_id: str,
    current_user: User = Depends(require_admin),
    report_repo: SQLBoardReportRepository = Depends(get_board_report_repo),
) -> None:
    """Soft-delete a report (admin only)."""
    org_id = _assert_org(current_user)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = EntityStatus.DELETED
    await report_repo.save(report)


# ── Report Schedules ──────────────────────────────────────────────────────────


@router.post(
    "/schedules",
    response_model=ReportScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report_schedule(
    body: ReportScheduleRequest,
    current_user: User = Depends(get_current_user),
    schedule_repo: SQLReportScheduleRepository = Depends(get_report_schedule_repo),
) -> ReportScheduleResponse:
    org_id = _assert_org(current_user)
    try:
        next_run = datetime.fromisoformat(body.next_run_at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid datetime: {exc}") from exc

    schedule = ReportSchedule(
        organization_id=org_id,
        frequency=body.frequency,
        next_run_at=next_run,
        report_config=body.report_config,
        is_active=True,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    saved = await schedule_repo.save(schedule)
    return _schedule_to_response(saved)


@router.get("/schedules", response_model=list[ReportScheduleResponse])
async def list_report_schedules(
    current_user: User = Depends(get_current_user),
    schedule_repo: SQLReportScheduleRepository = Depends(get_report_schedule_repo),
) -> list[ReportScheduleResponse]:
    org_id = _assert_org(current_user)
    schedules = await schedule_repo.list_for_org(org_id)
    return [_schedule_to_response(s) for s in schedules]


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    schedule_repo: SQLReportScheduleRepository = Depends(get_report_schedule_repo),
) -> None:
    org_id = _assert_org(current_user)
    sched = await schedule_repo.get_by_id(schedule_id)
    if sched is None or sched.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if sched.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    sched.status = EntityStatus.DELETED
    await schedule_repo.save(sched)


# ── Serialization helpers ─────────────────────────────────────────────────────


def _to_detail(r: BoardReport) -> BoardReportDetail:
    return BoardReportDetail(
        id=r.id,
        title=r.title,
        report_version=r.report_version,
        period_start=r.period_start.isoformat(),
        period_end=r.period_end.isoformat(),
        generated_at=r.created_at.isoformat(),
        executive_summary=r.executive_summary,
        report_data=r.report_data,
        supplier_snapshot=r.supplier_snapshot,
    )


def _schedule_to_response(s: ReportSchedule) -> ReportScheduleResponse:
    return ReportScheduleResponse(
        id=s.id,
        frequency=s.frequency,
        next_run_at=s.next_run_at.isoformat(),
        last_run_at=s.last_run_at.isoformat() if s.last_run_at else None,
        is_active=s.is_active,
        created_at=s.created_at.isoformat(),
    )
