"""
M28 Supplier Intelligence API

Provides ESG scoring, risk scoring, trend analysis, benchmarking,
watchlist, portfolio analytics, executive rankings, and risk heatmaps.

All endpoints enforce tenant isolation — users only see their own org.
No cross-tenant aggregation ever occurs.

URL structure:
  /suppliers/analytics/*        — org-level intelligence
  /suppliers/{id}/intelligence  — supplier-level score + explainability
  /suppliers/{id}/intelligence/history
  /suppliers/{id}/benchmark
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

import application.audit as audit_events
from application.scoring import (
    SCORE_VERSION,
    ScoreInputs,
    build_drivers,
    calculate_esg_scores,
    calculate_risk_score,
    calculate_trend,
    categorize_pillar,
)
from domain.enums import EntityStatus, RiskBand, SupplierStatus
from domain.supplier_score import SupplierScore
from domain.user import User
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel
from infrastructure.persistence.models.supplier_extensions import SupplierCertificationModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.repositories import (
    SQLAuditEventRepository,
    SQLSupplierRepository,
    SQLSupplierScoreRepository,
)
from interfaces.api.deps import (
    get_audit_event_repo,
    get_current_user,
    get_db,
    get_supplier_repo,
    get_supplier_score_repo,
)
from pydantic import BaseModel as _BaseModel
from interfaces.api.schemas.supplier_score import (
    ExecutiveRankingEntry,
    HeatmapCell,
    PortfolioAnalytics,
    RiskHeatmap,
    ScoreDriver,
    SupplierBenchmark,
    SupplierScoreHistoryEntry,
    SupplierScoreResponse,
    WatchlistEntry,
)


# ── GAP-22 Segmentation schemas ───────────────────────────────────────────────

class SegmentedSupplierEntry(_BaseModel):
    supplier_id: str
    name: str
    country: str
    industry: str
    supplier_tier: str
    risk_score: float
    risk_band: str
    esg_score: float
    trend: str
    trend_delta: float


class RiskSegment(_BaseModel):
    risk_band: str
    count: int
    avg_risk_score: float
    avg_esg_score: float
    improving: int
    deteriorating: int
    stable: int
    suppliers: list[SegmentedSupplierEntry]


class SegmentationResponse(_BaseModel):
    segments: list[RiskSegment]   # ordered Critical → Low
    unscored_count: int
    total_suppliers: int
    total_scored: int


# ── GAP-23 Geo-Heatmap schemas ────────────────────────────────────────────────

class GeoSupplierSummary(_BaseModel):
    supplier_id: str
    name: str
    industry: str
    supplier_tier: str
    risk_score: float
    risk_band: str
    esg_score: float
    trend: str


class GeoCountryEntry(_BaseModel):
    country: str
    supplier_count: int
    avg_risk_score: float
    avg_esg_score: float
    worst_band: str         # worst risk_band among suppliers in this country
    critical_count: int
    high_count: int
    improving: int
    deteriorating: int
    # External country risk profile (enrichment, best-effort)
    country_risk_score: float | None
    country_risk_level: str | None
    sanctions_status: str | None
    suppliers: list[GeoSupplierSummary]


class GeoHeatmapResponse(_BaseModel):
    countries: list[GeoCountryEntry]   # sorted by worst_band severity, then avg_risk_score desc
    total_suppliers: int
    countries_count: int


# ── GAP-24 Certificate Lifecycle schemas ──────────────────────────────────────

class CertificateAlertEntry(_BaseModel):
    cert_id: str
    supplier_id: str
    supplier_name: str
    cert_type: str
    custom_cert_name: str | None
    issuing_body: str | None
    valid_until: str | None      # ISO date string
    days_until_expiry: int | None  # negative = already expired
    lifecycle_status: str        # EXPIRED | EXPIRING_SOON | EXPIRING_60D | EXPIRING_90D | ACTIVE
    is_verified: bool


class CertTypeCount(_BaseModel):
    cert_type: str
    total: int
    expired: int
    expiring_soon: int


class CertificateLifecycleResponse(_BaseModel):
    total: int
    active: int
    expiring_soon: int       # ≤30 days
    expiring_60d: int        # 31–60 days
    expiring_90d: int        # 61–90 days
    expired: int
    verified: int
    alerts: list[CertificateAlertEntry]   # EXPIRED + EXPIRING_* sorted by days_until_expiry
    by_cert_type: list[CertTypeCount]

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/suppliers",
    tags=["supplier-intelligence"],
    dependencies=[Depends(get_current_user)],
)

_CLOSED_STATUSES = ("resolved", "verified")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _assert_org_access(supplier_org_id: str, user_org_id: str | None) -> None:
    if user_org_id is None or supplier_org_id != user_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")


async def _gather_inputs(
    session: AsyncSession,
    supplier_id: str,
    now: datetime,
) -> ScoreInputs:
    """Query all findings, risks, and actions for a supplier and build ScoreInputs."""

    # ── Findings (with ESG pillar classification) ─────────────────────────────
    finding_rows = (
        await session.execute(
            select(FindingModel.severity, FindingModel.category, FindingModel.title)
            .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
            .where(
                AssessmentModel.supplier_id == supplier_id,
                AssessmentModel.status != "Deleted",
                FindingModel.status != "Deleted",
            )
        )
    ).all()

    severity_counts: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    pillar_counts: dict[str, dict[str, int]] = {
        "Environmental": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
        "Social": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
        "Governance": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
    }
    for row in finding_rows:
        sev = row.severity if row.severity in severity_counts else "Low"
        severity_counts[sev] += 1
        pillar = categorize_pillar(row.category or "", row.title or "")
        pillar_counts[pillar][sev] += 1

    # ── Risks ─────────────────────────────────────────────────────────────────
    risk_rows = (
        await session.execute(
            select(RiskModel.risk_level)
            .join(AssessmentModel, RiskModel.assessment_id == AssessmentModel.id)
            .where(
                AssessmentModel.supplier_id == supplier_id,
                AssessmentModel.status != "Deleted",
                RiskModel.status != "Deleted",
            )
        )
    ).all()

    risk_counts: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for row in risk_rows:
        lvl = row.risk_level if row.risk_level in risk_counts else "Low"
        risk_counts[lvl] += 1

    # ── Recommendations / actions ─────────────────────────────────────────────
    rec_rows = (
        await session.execute(
            select(RecommendationModel.action_status, RecommendationModel.due_date)
            .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
            .where(
                AssessmentModel.supplier_id == supplier_id,
                AssessmentModel.status != "Deleted",
                RecommendationModel.status != "Deleted",
            )
        )
    ).all()

    open_actions = 0
    overdue_actions = 0
    for row in rec_rows:
        if row.action_status not in _CLOSED_STATUSES:
            open_actions += 1
            if row.due_date and row.due_date < now:
                overdue_actions += 1

    # ── Assessment counts ─────────────────────────────────────────────────────
    assess_row = (
        await session.execute(
            select(
                func.count(AssessmentModel.id).label("total"),
                func.sum(
                    case((AssessmentModel.review_status == "Approved", 1), else_=0)
                ).label("approved"),
            ).where(
                AssessmentModel.supplier_id == supplier_id,
                AssessmentModel.status != "Deleted",
            )
        )
    ).one()

    env = pillar_counts["Environmental"]
    soc = pillar_counts["Social"]
    gov = pillar_counts["Governance"]

    return ScoreInputs(
        total_assessments=assess_row.total or 0,
        approved_assessments=int(assess_row.approved or 0),
        critical_findings=severity_counts["Critical"],
        high_findings=severity_counts["High"],
        medium_findings=severity_counts["Medium"],
        low_findings=severity_counts["Low"],
        critical_risks=risk_counts["Critical"],
        high_risks=risk_counts["High"],
        medium_risks=risk_counts["Medium"],
        low_risks=risk_counts["Low"],
        open_actions=open_actions,
        overdue_actions=overdue_actions,
        env_critical=env["Critical"],
        env_high=env["High"],
        env_medium=env["Medium"],
        env_low=env["Low"],
        social_critical=soc["Critical"],
        social_high=soc["High"],
        social_medium=soc["Medium"],
        social_low=soc["Low"],
        gov_critical=gov["Critical"],
        gov_high=gov["High"],
        gov_medium=gov["Medium"],
        gov_low=gov["Low"],
    )


async def _compute_and_persist(
    session: AsyncSession,
    score_repo: SQLSupplierScoreRepository,
    supplier_id: str,
    organization_id: str,
    previous_esg: float | None,
    actor_id: str,
) -> SupplierScore:
    """Gather inputs, run calculation, persist score, return domain object."""
    now = datetime.now(UTC)
    inputs = await _gather_inputs(session, supplier_id, now)

    risk_score, risk_band = calculate_risk_score(inputs)
    esg_score, env_score, social_score, gov_score = calculate_esg_scores(inputs)
    trend, trend_delta = calculate_trend(esg_score, previous_esg)
    drivers = build_drivers(inputs)

    score = SupplierScore(
        supplier_id=supplier_id,
        organization_id=organization_id,
        score_version=SCORE_VERSION,
        esg_score=esg_score,
        environmental_score=env_score,
        social_score=social_score,
        governance_score=gov_score,
        risk_score=risk_score,
        risk_band=risk_band,
        trend=trend,
        trend_delta=trend_delta,
        sector_percentile=None,  # computed below after save
        inputs={
            "total_assessments": inputs.total_assessments,
            "approved_assessments": inputs.approved_assessments,
            "critical_findings": inputs.critical_findings,
            "high_findings": inputs.high_findings,
            "medium_findings": inputs.medium_findings,
            "low_findings": inputs.low_findings,
            "critical_risks": inputs.critical_risks,
            "high_risks": inputs.high_risks,
            "medium_risks": inputs.medium_risks,
            "low_risks": inputs.low_risks,
            "open_actions": inputs.open_actions,
            "overdue_actions": inputs.overdue_actions,
            "env_critical": inputs.env_critical,
            "env_high": inputs.env_high,
            "env_medium": inputs.env_medium,
            "env_low": inputs.env_low,
            "social_critical": inputs.social_critical,
            "social_high": inputs.social_high,
            "social_medium": inputs.social_medium,
            "social_low": inputs.social_low,
            "gov_critical": inputs.gov_critical,
            "gov_high": inputs.gov_high,
            "gov_medium": inputs.gov_medium,
            "gov_low": inputs.gov_low,
        },
        drivers=drivers,
        status=EntityStatus.ACTIVE,
        created_by=actor_id,
    )
    return await score_repo.save(score)


async def _compute_percentile(
    session: AsyncSession,
    supplier_id: str,
    risk_score: float,
    industry: str,
    organization_id: str,
) -> float | None:
    """
    Compute within-org peer percentile for a supplier.

    Percentile = % of peers (same industry) with HIGHER risk score.
    100th percentile = lowest risk among peers (best).
    0th percentile = highest risk among peers (worst).
    """
    # Get latest risk score for all org suppliers in the same industry
    from infrastructure.persistence.models.supplier_score import SupplierScoreModel  # noqa: PLC0415

    latest_subq = (
        select(
            SupplierScoreModel.supplier_id.label("sid"),
            func.max(SupplierScoreModel.created_at).label("max_created"),
        )
        .where(SupplierScoreModel.organization_id == organization_id)
        .group_by(SupplierScoreModel.supplier_id)
        .subquery()
    )

    peer_scores_stmt = (
        select(SupplierScoreModel.risk_score)
        .join(latest_subq,
              (SupplierScoreModel.supplier_id == latest_subq.c.sid) &
              (SupplierScoreModel.created_at == latest_subq.c.max_created))
        .join(SupplierModel, SupplierScoreModel.supplier_id == SupplierModel.id)
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.industry.ilike(f"%{industry[:20]}%") if industry else True,
            SupplierModel.status.notin_(["Deleted", "Archived"]),
        )
    )
    peer_scores = [r[0] for r in (await session.execute(peer_scores_stmt)).all()]

    if not peer_scores or len(peer_scores) < 2:
        return None

    peers_with_higher_risk = sum(1 for s in peer_scores if s > risk_score)
    return round((peers_with_higher_risk / len(peer_scores)) * 100.0, 1)


def _score_to_response(
    score: SupplierScore,
    supplier_name: str,
) -> SupplierScoreResponse:
    return SupplierScoreResponse(
        supplier_id=score.supplier_id,
        supplier_name=supplier_name,
        calculated_at=score.created_at.isoformat(),
        score_version=score.score_version,
        esg_score=score.esg_score,
        environmental_score=score.environmental_score,
        social_score=score.social_score,
        governance_score=score.governance_score,
        risk_score=score.risk_score,
        risk_band=score.risk_band.value,
        trend=score.trend.value,
        trend_delta=score.trend_delta,
        sector_percentile=score.sector_percentile,
        drivers=[ScoreDriver(**d) for d in score.drivers],
        inputs=score.inputs,
    )


# ── Supplier-level score endpoints ────────────────────────────────────────────


@router.get("/{supplier_id}/intelligence", response_model=SupplierScoreResponse)
async def get_supplier_intelligence(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    session: AsyncSession = Depends(get_db),
) -> SupplierScoreResponse:
    """
    Return latest intelligence score for a supplier.

    Auto-calculates on first request (no score record exists).
    Use POST /intelligence/recalculate to force a fresh calculation.
    """
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    latest = await score_repo.get_latest_for_supplier(supplier_id)
    if latest is None:
        # First-time calculation
        latest = await _compute_and_persist(
            session=session,
            score_repo=score_repo,
            supplier_id=supplier_id,
            organization_id=supplier.organization_id,
            previous_esg=None,
            actor_id=current_user.id,
        )
        percentile = await _compute_percentile(
            session, supplier_id, latest.risk_score, supplier.industry, supplier.organization_id
        )
        if percentile is not None:
            latest.sector_percentile = percentile
            latest = await score_repo.save(latest)

    return _score_to_response(latest, supplier.name)


@router.post(
    "/{supplier_id}/intelligence/recalculate",
    response_model=SupplierScoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def recalculate_supplier_intelligence(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    session: AsyncSession = Depends(get_db),
) -> SupplierScoreResponse:
    """Force a fresh score calculation and persist it as a new audit record."""
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    previous = await score_repo.get_latest_for_supplier(supplier_id)
    previous_esg = previous.esg_score if previous else None

    new_score = await _compute_and_persist(
        session=session,
        score_repo=score_repo,
        supplier_id=supplier_id,
        organization_id=supplier.organization_id,
        previous_esg=previous_esg,
        actor_id=current_user.id,
    )
    percentile = await _compute_percentile(
        session, supplier_id, new_score.risk_score, supplier.industry, supplier.organization_id
    )
    if percentile is not None:
        new_score.sector_percentile = percentile
        new_score = await score_repo.save(new_score)

    await audit_repo.save(
        audit_events.supplier_score_calculated(
            supplier_id=supplier_id,
            supplier_name=supplier.name,
            risk_score=new_score.risk_score,
            risk_band=new_score.risk_band.value,
            esg_score=new_score.esg_score,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    )
    logger.info(
        "supplier_score_recalculated",
        supplier_id=supplier_id,
        risk_score=new_score.risk_score,
        esg_score=new_score.esg_score,
    )
    return _score_to_response(new_score, supplier.name)


@router.get(
    "/{supplier_id}/intelligence/history",
    response_model=list[SupplierScoreHistoryEntry],
)
async def get_supplier_score_history(
    supplier_id: str,
    limit: int = Query(default=12, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
) -> list[SupplierScoreHistoryEntry]:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    history = await score_repo.get_history_for_supplier(supplier_id, limit=limit)
    return [
        SupplierScoreHistoryEntry(
            calculated_at=s.created_at.isoformat(),
            esg_score=s.esg_score,
            risk_score=s.risk_score,
            risk_band=s.risk_band.value,
            trend=s.trend.value,
        )
        for s in history
    ]


@router.get("/{supplier_id}/benchmark", response_model=SupplierBenchmark)
async def get_supplier_benchmark(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    session: AsyncSession = Depends(get_db),
) -> SupplierBenchmark:
    """
    Benchmark this supplier against same-industry peers in the same organization.

    Note: benchmarking is within-org only — cross-org aggregation would violate
    tenant isolation.  Inter-organization benchmarking is deferred to M31
    (Regulatory Intelligence), where anonymous sector-level data is used.
    """
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    latest = await score_repo.get_latest_for_supplier(supplier_id)
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score calculated yet. Call GET /intelligence first.",
        )

    from infrastructure.persistence.models.supplier_score import SupplierScoreModel  # noqa: PLC0415

    latest_subq = (
        select(
            SupplierScoreModel.supplier_id.label("sid"),
            func.max(SupplierScoreModel.created_at).label("max_created"),
        )
        .where(SupplierScoreModel.organization_id == supplier.organization_id)
        .group_by(SupplierScoreModel.supplier_id)
        .subquery()
    )
    peer_rows = (
        await session.execute(
            select(SupplierScoreModel.supplier_id, SupplierScoreModel.risk_score)
            .join(
                latest_subq,
                (SupplierScoreModel.supplier_id == latest_subq.c.sid) &
                (SupplierScoreModel.created_at == latest_subq.c.max_created),
            )
            .join(SupplierModel, SupplierScoreModel.supplier_id == SupplierModel.id)
            .where(
                SupplierModel.organization_id == supplier.organization_id,
                SupplierModel.industry.ilike(f"%{supplier.industry[:20]}%")
                if supplier.industry
                else True,
                SupplierModel.status.notin_(["Deleted", "Archived"]),
            )
        )
    ).all()

    peer_scores = [r.risk_score for r in peer_rows]
    peers_evaluated = len(peer_scores)
    percentile = latest.sector_percentile

    if peer_scores and peers_evaluated >= 2:
        peers_with_higher = sum(1 for s in peer_scores if s > latest.risk_score)
        percentile = round((peers_with_higher / peers_evaluated) * 100.0, 1)
        if percentile >= 66:
            comparison = "Better than peers"
        elif percentile >= 33:
            comparison = "Average"
        else:
            comparison = "Worse than peers"
    else:
        comparison = "Insufficient peer data"

    return SupplierBenchmark(
        supplier_id=supplier_id,
        supplier_name=supplier.name,
        risk_score=latest.risk_score,
        risk_band=latest.risk_band.value,
        sector_percentile=percentile,
        peer_comparison=comparison,
        peers_evaluated=peers_evaluated,
        industry=supplier.industry,
    )


# ── Organization-level analytics endpoints ────────────────────────────────────

_BAND_ORDER = ["Critical", "High", "Moderate", "Low"]


@router.get("/analytics/segmentation", response_model=SegmentationResponse)
async def get_supplier_segmentation(
    current_user: User = Depends(get_current_user),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
) -> SegmentationResponse:
    """Risk Tiering — groups suppliers by latest risk_band.

    Deterministic: uses persisted SupplierScore rows, no LLM.
    All queries are org-scoped via organization_id.
    """
    if not current_user.organization_id:
        return SegmentationResponse(
            segments=[], unscored_count=0, total_suppliers=0, total_scored=0
        )

    all_suppliers, total_count = await supplier_repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=1,
        page_size=10_000,
    )
    supplier_map = {s.id: s for s in all_suppliers}

    latest_scores = await score_repo.get_latest_for_org(current_user.organization_id)
    scored_ids = {s.supplier_id for s in latest_scores}
    unscored = total_count - len(scored_ids)

    # Group by band
    from collections import defaultdict
    bands: dict[str, list[SegmentedSupplierEntry]] = defaultdict(list)

    for score in latest_scores:
        sup = supplier_map.get(score.supplier_id)
        if sup is None:
            continue
        bands[score.risk_band.value].append(
            SegmentedSupplierEntry(
                supplier_id=score.supplier_id,
                name=sup.name,
                country=sup.country,
                industry=sup.industry,
                supplier_tier=sup.supplier_tier.value if hasattr(sup.supplier_tier, "value") else str(sup.supplier_tier),
                risk_score=round(score.risk_score, 1),
                risk_band=score.risk_band.value,
                esg_score=round(score.esg_score, 1),
                trend=score.trend.value,
                trend_delta=round(score.trend_delta, 2),
            )
        )

    segments: list[RiskSegment] = []
    for band in _BAND_ORDER:
        entries = bands.get(band, [])
        if not entries:
            # Always include all tiers even if empty
            segments.append(RiskSegment(
                risk_band=band, count=0, avg_risk_score=0.0, avg_esg_score=0.0,
                improving=0, deteriorating=0, stable=0, suppliers=[],
            ))
            continue
        entries.sort(key=lambda e: e.risk_score, reverse=True)
        avg_risk = round(sum(e.risk_score for e in entries) / len(entries), 1)
        avg_esg  = round(sum(e.esg_score  for e in entries) / len(entries), 1)
        improving    = sum(1 for e in entries if e.trend == "Improving")
        deteriorating = sum(1 for e in entries if e.trend == "Deteriorating")
        stable       = sum(1 for e in entries if e.trend == "Stable")
        segments.append(RiskSegment(
            risk_band=band,
            count=len(entries),
            avg_risk_score=avg_risk,
            avg_esg_score=avg_esg,
            improving=improving,
            deteriorating=deteriorating,
            stable=stable,
            suppliers=entries,
        ))

    return SegmentationResponse(
        segments=segments,
        unscored_count=unscored if unscored > 0 else 0,
        total_suppliers=total_count,
        total_scored=len(latest_scores),
    )


_BAND_SEVERITY = {"Critical": 4, "High": 3, "Moderate": 2, "Low": 1, "": 0}


@router.get("/analytics/geo-heatmap", response_model=GeoHeatmapResponse)
async def get_geo_heatmap(
    current_user: User = Depends(get_current_user),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    session: AsyncSession = Depends(get_db),
) -> GeoHeatmapResponse:
    """Geographic portfolio heatmap — aggregates supplier risk by country.

    Deterministic, org-scoped. Enriches with CountryRiskProfile where the
    supplier.country string matches a country_code (best-effort, case-insensitive).
    """
    if not current_user.organization_id:
        return GeoHeatmapResponse(countries=[], total_suppliers=0, countries_count=0)

    all_suppliers, total_count = await supplier_repo.list_org_paged(
        organization_id=current_user.organization_id, page=1, page_size=10_000,
    )
    supplier_map = {s.id: s for s in all_suppliers}

    latest_scores = await score_repo.get_latest_for_org(current_user.organization_id)
    scored_by_sid = {s.supplier_id: s for s in latest_scores}

    # Group by country
    from collections import defaultdict
    by_country: dict[str, list[GeoSupplierSummary]] = defaultdict(list)
    for sup in all_suppliers:
        country = sup.country.strip() or "Unknown"
        score = scored_by_sid.get(sup.id)
        if score is None:
            continue
        tier_val = sup.supplier_tier.value if hasattr(sup.supplier_tier, "value") else str(sup.supplier_tier)
        by_country[country].append(GeoSupplierSummary(
            supplier_id=sup.id,
            name=sup.name,
            industry=sup.industry,
            supplier_tier=tier_val,
            risk_score=round(score.risk_score, 1),
            risk_band=score.risk_band.value,
            esg_score=round(score.esg_score, 1),
            trend=score.trend.value,
        ))

    # Fetch all CountryRiskProfiles in one query (platform-global, no org filter)
    stmt = select(CountryRiskProfileModel)
    crp_rows = (await session.execute(stmt)).scalars().all()
    # Build lookup: uppercase country_code → latest profile (by id desc as proxy)
    crp_map: dict[str, CountryRiskProfileModel] = {}
    for row in crp_rows:
        key = row.country_code.upper()
        if key not in crp_map:
            crp_map[key] = row

    entries: list[GeoCountryEntry] = []
    for country, sups in by_country.items():
        bands = [s.risk_band for s in sups]
        worst = max(bands, key=lambda b: _BAND_SEVERITY.get(b, 0))
        avg_risk = round(sum(s.risk_score for s in sups) / len(sups), 1)
        avg_esg  = round(sum(s.esg_score  for s in sups) / len(sups), 1)
        critical = sum(1 for s in sups if s.risk_band == "Critical")
        high     = sum(1 for s in sups if s.risk_band == "High")
        improving    = sum(1 for s in sups if s.trend == "Improving")
        deteriorating = sum(1 for s in sups if s.trend == "Deteriorating")

        # Enrich: try country.upper() as ISO code lookup
        crp = crp_map.get(country.upper())
        entries.append(GeoCountryEntry(
            country=country,
            supplier_count=len(sups),
            avg_risk_score=avg_risk,
            avg_esg_score=avg_esg,
            worst_band=worst,
            critical_count=critical,
            high_count=high,
            improving=improving,
            deteriorating=deteriorating,
            country_risk_score=round(crp.overall_risk_score, 1) if crp else None,
            country_risk_level=crp.risk_level if crp else None,
            sanctions_status=crp.sanctions_status if crp else None,
            suppliers=sorted(sups, key=lambda s: s.risk_score, reverse=True),
        ))

    # Sort: worst band first, then avg_risk_score descending
    entries.sort(
        key=lambda e: (_BAND_SEVERITY.get(e.worst_band, 0) * -1, -e.avg_risk_score)
    )

    return GeoHeatmapResponse(
        countries=entries,
        total_suppliers=sum(e.supplier_count for e in entries),
        countries_count=len(entries),
    )


@router.get("/analytics/certificate-lifecycle", response_model=CertificateLifecycleResponse)
async def get_certificate_lifecycle(
    days_window: int = Query(default=90, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    session: AsyncSession = Depends(get_db),
) -> CertificateLifecycleResponse:
    """Org-wide certificate lifecycle dashboard (GAP-24).

    Computes lifecycle status deterministically from valid_until vs today.
    Lifecycle thresholds (default window=90d):
      EXPIRED      — valid_until < today
      EXPIRING_SOON — valid_until within 30 days
      EXPIRING_60D  — valid_until within 31–60 days
      EXPIRING_90D  — valid_until within 61–days_window days
      ACTIVE        — valid_until beyond window or None
    """
    from datetime import date as _date

    org_id = current_user.organization_id or ""
    if not org_id:
        return CertificateLifecycleResponse(
            total=0, active=0, expiring_soon=0, expiring_60d=0,
            expiring_90d=0, expired=0, verified=0, alerts=[], by_cert_type=[],
        )

    # Load suppliers for name lookup
    all_suppliers, _ = await supplier_repo.list_org_paged(org_id, page=1, page_size=10_000)
    supplier_map = {s.id: s.name for s in all_suppliers}

    # Load all certs for org
    stmt = (
        select(SupplierCertificationModel)
        .where(SupplierCertificationModel.organization_id == org_id)
        .order_by(SupplierCertificationModel.valid_until.asc().nullslast())
    )
    rows = (await session.execute(stmt)).scalars().all()

    today = _date.today()
    total = expired = active = expiring_soon = expiring_60d = expiring_90d = verified = 0
    alerts: list[CertificateAlertEntry] = []
    by_type: dict[str, dict] = {}

    for row in rows:
        total += 1
        if row.is_verified:
            verified += 1

        # Compute days_until_expiry
        if row.valid_until is None:
            lifecycle = "ACTIVE"
            days_left: int | None = None
        else:
            days_left = (row.valid_until - today).days
            if days_left < 0:
                lifecycle = "EXPIRED"
            elif days_left <= 30:
                lifecycle = "EXPIRING_SOON"
            elif days_left <= 60:
                lifecycle = "EXPIRING_60D"
            elif days_left <= days_window:
                lifecycle = "EXPIRING_90D"
            else:
                lifecycle = "ACTIVE"

        if lifecycle == "EXPIRED":
            expired += 1
        elif lifecycle == "EXPIRING_SOON":
            expiring_soon += 1
        elif lifecycle == "EXPIRING_60D":
            expiring_60d += 1
        elif lifecycle == "EXPIRING_90D":
            expiring_90d += 1
        else:
            active += 1

        # Build cert_type stats
        ct = by_type.setdefault(row.cert_type, {"total": 0, "expired": 0, "expiring_soon": 0})
        ct["total"] += 1
        if lifecycle == "EXPIRED":
            ct["expired"] += 1
        if lifecycle == "EXPIRING_SOON":
            ct["expiring_soon"] += 1

        # Build alert entry for non-ACTIVE certs
        if lifecycle != "ACTIVE":
            alerts.append(CertificateAlertEntry(
                cert_id=row.id,
                supplier_id=row.supplier_id,
                supplier_name=supplier_map.get(row.supplier_id, "Unknown"),
                cert_type=row.cert_type,
                custom_cert_name=row.custom_cert_name,
                issuing_body=row.issuing_body,
                valid_until=row.valid_until.isoformat() if row.valid_until else None,
                days_until_expiry=days_left,
                lifecycle_status=lifecycle,
                is_verified=row.is_verified,
            ))

    # Sort alerts: expired first (most negative days_left), then by days ascending
    alerts.sort(key=lambda a: (a.days_until_expiry if a.days_until_expiry is not None else -9999))

    by_cert_type = [
        CertTypeCount(cert_type=k, total=v["total"], expired=v["expired"], expiring_soon=v["expiring_soon"])
        for k, v in sorted(by_type.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

    return CertificateLifecycleResponse(
        total=total,
        active=active,
        expiring_soon=expiring_soon,
        expiring_60d=expiring_60d,
        expiring_90d=expiring_90d,
        expired=expired,
        verified=verified,
        alerts=alerts,
        by_cert_type=by_cert_type,
    )


@router.get("/analytics/portfolio", response_model=PortfolioAnalytics)
async def get_portfolio_analytics(
    current_user: User = Depends(get_current_user),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
) -> PortfolioAnalytics:
    if not current_user.organization_id:
        return PortfolioAnalytics(
            total_suppliers=0, scored_suppliers=0, critical_risk_suppliers=0,
            high_risk_suppliers=0, improving_suppliers=0, deteriorating_suppliers=0,
            avg_esg_score=None, avg_risk_score=None,
            risk_distribution={"Low": 0, "Moderate": 0, "High": 0, "Critical": 0},
        )

    all_suppliers, total_count = await supplier_repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=1,
        page_size=10000,
    )
    latest_scores = await score_repo.get_latest_for_org(current_user.organization_id)
    scored_by_supplier = {s.supplier_id: s for s in latest_scores}

    distribution: dict[str, int] = {"Low": 0, "Moderate": 0, "High": 0, "Critical": 0}
    improving = deteriorating = critical_risk = high_risk = 0
    total_esg = total_risk = scored_n = 0

    for score in latest_scores:
        band = score.risk_band.value
        distribution[band] = distribution.get(band, 0) + 1
        if band == "Critical":
            critical_risk += 1
        if band in ("High", "Critical"):
            high_risk += 1
        if score.trend.value == "Improving":
            improving += 1
        if score.trend.value == "Deteriorating":
            deteriorating += 1
        total_esg += score.esg_score
        total_risk += score.risk_score
        scored_n += 1

    return PortfolioAnalytics(
        total_suppliers=total_count,
        scored_suppliers=scored_n,
        critical_risk_suppliers=critical_risk,
        high_risk_suppliers=high_risk,
        improving_suppliers=improving,
        deteriorating_suppliers=deteriorating,
        avg_esg_score=round(total_esg / scored_n, 1) if scored_n else None,
        avg_risk_score=round(total_risk / scored_n, 1) if scored_n else None,
        risk_distribution=distribution,
    )


@router.get("/analytics/watchlist", response_model=list[WatchlistEntry])
async def get_intelligence_watchlist(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    session: AsyncSession = Depends(get_db),
) -> list[WatchlistEntry]:
    """
    Ranked watchlist of suppliers requiring attention.

    Criteria for inclusion:
      - Risk band is Critical or High, OR
      - Trend is Deteriorating, OR
      - Overdue actions > 0, OR
      - Critical findings > 0

    Sorted by risk_score descending.
    """
    if not current_user.organization_id:
        return []

    latest_scores = await score_repo.get_latest_for_org(current_user.organization_id)
    if not latest_scores:
        return []

    all_suppliers_raw, _ = await supplier_repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=1,
        page_size=10000,
    )
    supplier_map = {s.id: s for s in all_suppliers_raw}

    # Pull per-supplier counts for the watchlist display
    crit_finding_counts = await _get_critical_finding_counts(
        session, current_user.organization_id
    )
    overdue_counts = await _get_overdue_action_counts(
        session, current_user.organization_id
    )

    entries: list[WatchlistEntry] = []
    for score in latest_scores:
        sup = supplier_map.get(score.supplier_id)
        if sup is None:
            continue

        crit_findings = crit_finding_counts.get(score.supplier_id, 0)
        overdue = overdue_counts.get(score.supplier_id, 0)

        # Determine if supplier belongs on watchlist
        alert_reasons: list[str] = []
        if score.risk_band == RiskBand.CRITICAL:
            alert_reasons.append("Critical Risk")
        if score.risk_band == RiskBand.HIGH:
            alert_reasons.append("High Risk")
        if score.trend.value == "Deteriorating":
            alert_reasons.append("Deteriorating Trend")
        if overdue > 0:
            alert_reasons.append(f"{overdue} Overdue Action(s)")
        if crit_findings > 0:
            alert_reasons.append(f"{crit_findings} Critical Finding(s)")

        if not alert_reasons:
            continue

        entries.append(
            WatchlistEntry(
                supplier_id=score.supplier_id,
                supplier_name=sup.name,
                country=sup.country,
                industry=sup.industry,
                supplier_tier=sup.supplier_tier.value if hasattr(sup.supplier_tier, "value") else str(sup.supplier_tier),
                risk_score=score.risk_score,
                risk_band=score.risk_band.value,
                trend=score.trend.value,
                trend_delta=score.trend_delta,
                critical_findings=crit_findings,
                overdue_actions=overdue,
                alert_reasons=alert_reasons,
            )
        )

    entries.sort(key=lambda e: e.risk_score, reverse=True)
    return entries[:limit]


@router.get("/analytics/rankings", response_model=list[ExecutiveRankingEntry])
async def get_executive_rankings(
    sort_by: str = Query(
        default="risk_score",
        pattern="^(risk_score|esg_score|overdue_actions|critical_findings)$",
    ),
    limit: int = Query(default=25, ge=1, le=100),
    risk_band: str | None = Query(default=None),
    country: str | None = Query(default=None),
    supplier_tier: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    score_repo: SQLSupplierScoreRepository = Depends(get_supplier_score_repo),
    session: AsyncSession = Depends(get_db),
) -> list[ExecutiveRankingEntry]:
    """
    Executive ranked supplier table.

    Sorts by risk_score (default), esg_score (ascending), overdue_actions, or critical_findings.
    Designed for board and management reporting.
    """
    if not current_user.organization_id:
        return []

    latest_scores = await score_repo.get_latest_for_org(current_user.organization_id)
    if not latest_scores:
        return []

    all_suppliers_raw, _ = await supplier_repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=1,
        page_size=10000,
        country=country,
        supplier_tier=supplier_tier,
    )
    supplier_map = {s.id: s for s in all_suppliers_raw}

    crit_finding_counts = await _get_critical_finding_counts(
        session, current_user.organization_id
    )
    overdue_counts = await _get_overdue_action_counts(
        session, current_user.organization_id
    )

    entries: list[ExecutiveRankingEntry] = []
    for score in latest_scores:
        sup = supplier_map.get(score.supplier_id)
        if sup is None:
            continue
        if risk_band and score.risk_band.value != risk_band:
            continue

        entries.append(
            ExecutiveRankingEntry(
                rank=0,  # filled below
                supplier_id=score.supplier_id,
                supplier_name=sup.name,
                country=sup.country,
                industry=sup.industry,
                supplier_tier=sup.supplier_tier.value if hasattr(sup.supplier_tier, "value") else str(sup.supplier_tier),
                risk_score=score.risk_score,
                risk_band=score.risk_band.value,
                esg_score=score.esg_score,
                trend=score.trend.value,
                trend_delta=score.trend_delta,
                critical_findings=crit_finding_counts.get(score.supplier_id, 0),
                overdue_actions=overdue_counts.get(score.supplier_id, 0),
            )
        )

    if sort_by == "risk_score":
        entries.sort(key=lambda e: e.risk_score, reverse=True)
    elif sort_by == "esg_score":
        entries.sort(key=lambda e: e.esg_score)  # lowest ESG = worst = first
    elif sort_by == "overdue_actions":
        entries.sort(key=lambda e: e.overdue_actions, reverse=True)
    elif sort_by == "critical_findings":
        entries.sort(key=lambda e: e.critical_findings, reverse=True)

    for i, entry in enumerate(entries[:limit], start=1):
        entries[i - 1] = entry.model_copy(update={"rank": i})

    return entries[:limit]


@router.get("/analytics/heatmap", response_model=RiskHeatmap)
async def get_org_risk_heatmap(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RiskHeatmap:
    """
    Organization-wide ESG risk heatmap.

    Axes: ESG pillar × severity.  Each cell = finding count.
    """
    if not current_user.organization_id:
        return RiskHeatmap(cells=[], total_findings=0)

    return await _build_heatmap(session, current_user.organization_id, supplier_id=None)


@router.get("/{supplier_id}/heatmap", response_model=RiskHeatmap)
async def get_supplier_heatmap(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    session: AsyncSession = Depends(get_db),
) -> RiskHeatmap:
    """ESG risk heatmap for a single supplier."""
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=404, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    return await _build_heatmap(session, current_user.organization_id, supplier_id=supplier_id)


# ── Aggregate helper queries ──────────────────────────────────────────────────


async def _get_critical_finding_counts(
    session: AsyncSession, organization_id: str
) -> dict[str, int]:
    rows = (
        await session.execute(
            select(
                AssessmentModel.supplier_id,
                func.count(FindingModel.id).label("cnt"),
            )
            .join(FindingModel, FindingModel.assessment_id == AssessmentModel.id)
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                AssessmentModel.supplier_id.isnot(None),
                AssessmentModel.status != "Deleted",
                FindingModel.status != "Deleted",
                FindingModel.severity == "Critical",
                SupplierModel.organization_id == organization_id,
            )
            .group_by(AssessmentModel.supplier_id)
        )
    ).all()
    return {r.supplier_id: r.cnt for r in rows if r.supplier_id}


async def _get_overdue_action_counts(
    session: AsyncSession, organization_id: str
) -> dict[str, int]:
    now = datetime.now(UTC)
    rows = (
        await session.execute(
            select(
                AssessmentModel.supplier_id,
                func.count(RecommendationModel.id).label("cnt"),
            )
            .join(
                RecommendationModel,
                RecommendationModel.assessment_id == AssessmentModel.id,
            )
            .join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
            .where(
                AssessmentModel.supplier_id.isnot(None),
                AssessmentModel.status != "Deleted",
                RecommendationModel.status != "Deleted",
                RecommendationModel.due_date < now,
                RecommendationModel.action_status.notin_(list(_CLOSED_STATUSES)),
                SupplierModel.organization_id == organization_id,
            )
            .group_by(AssessmentModel.supplier_id)
        )
    ).all()
    return {r.supplier_id: r.cnt for r in rows if r.supplier_id}


async def _build_heatmap(
    session: AsyncSession,
    organization_id: str,
    supplier_id: str | None,
) -> RiskHeatmap:
    where_clauses = [
        AssessmentModel.status != "Deleted",
        FindingModel.status != "Deleted",
    ]
    if supplier_id:
        where_clauses.append(AssessmentModel.supplier_id == supplier_id)
    else:
        # org-wide: restrict to this tenant's suppliers only
        where_clauses.append(AssessmentModel.supplier_id.isnot(None))
        where_clauses.append(SupplierModel.organization_id == organization_id)

    stmt = (
        select(FindingModel.severity, FindingModel.category, FindingModel.title)
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
    )
    if not supplier_id:
        stmt = stmt.join(SupplierModel, AssessmentModel.supplier_id == SupplierModel.id)
    stmt = stmt.where(*where_clauses)

    rows = (await session.execute(stmt)).all()

    cell_counts: dict[tuple[str, str], int] = {}
    for row in rows:
        pillar = categorize_pillar(row.category or "", row.title or "")
        sev = row.severity if row.severity in ("Critical", "High", "Medium", "Low") else "Low"
        key = (pillar, sev)
        cell_counts[key] = cell_counts.get(key, 0) + 1

    pillars = ("Environmental", "Social", "Governance")
    severities = ("Critical", "High", "Medium", "Low")
    cells = [
        HeatmapCell(pillar=p, severity=s, count=cell_counts.get((p, s), 0))
        for p in pillars
        for s in severities
    ]

    return RiskHeatmap(
        cells=cells,
        total_findings=len(rows),
        supplier_id=supplier_id,
    )
