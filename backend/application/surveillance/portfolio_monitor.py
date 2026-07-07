"""M37 Portfolio Risk Monitor.

Continuously computes organization-wide portfolio surveillance state:
  - suppliers at risk
  - suppliers improving
  - suppliers deteriorating
  - critical suppliers
  - suppliers needing review

Also computes and stores RiskTrend records per supplier per month.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


async def compute_portfolio_stats(organization_id: str, session) -> dict:
    """Compute org-wide portfolio risk stats. Used by dashboard."""
    from sqlalchemy import func, select

    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.supplier_score import SupplierScoreModel
    from infrastructure.persistence.models.surveillance import (
        RiskEpisodeModel,
        SupplierWatchlistModel,
        SurveillanceSignalModel,
    )

    # Active suppliers
    total_stmt = (
        select(func.count())
        .select_from(SupplierModel)
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.supplier_status == "Active",
        )
    )
    total_suppliers = (await session.execute(total_stmt)).scalar_one()

    # Suppliers with active CRITICAL/HIGH signals
    at_risk_stmt = select(func.count(SurveillanceSignalModel.supplier_id.distinct())).where(
        SurveillanceSignalModel.organization_id == organization_id,
        SurveillanceSignalModel.signal_status == "ACTIVE",
        SurveillanceSignalModel.severity.in_(["CRITICAL", "HIGH"]),
        SurveillanceSignalModel.supplier_id.is_not(None),
    )
    suppliers_at_risk = (await session.execute(at_risk_stmt)).scalar_one()

    # Watchlist count
    watchlist_stmt = (
        select(func.count())
        .select_from(SupplierWatchlistModel)
        .where(
            SupplierWatchlistModel.organization_id == organization_id,
            SupplierWatchlistModel.watchlist_status == "ACTIVE",
        )
    )
    watchlist_count = (await session.execute(watchlist_stmt)).scalar_one()

    # Active signals total
    active_signals_stmt = (
        select(func.count())
        .select_from(SurveillanceSignalModel)
        .where(
            SurveillanceSignalModel.organization_id == organization_id,
            SurveillanceSignalModel.signal_status == "ACTIVE",
        )
    )
    active_signals = (await session.execute(active_signals_stmt)).scalar_one()

    # Critical signals
    critical_signals_stmt = (
        select(func.count())
        .select_from(SurveillanceSignalModel)
        .where(
            SurveillanceSignalModel.organization_id == organization_id,
            SurveillanceSignalModel.signal_status == "ACTIVE",
            SurveillanceSignalModel.severity == "CRITICAL",
        )
    )
    critical_signals = (await session.execute(critical_signals_stmt)).scalar_one()

    # Open episodes
    open_episodes_stmt = (
        select(func.count())
        .select_from(RiskEpisodeModel)
        .where(
            RiskEpisodeModel.organization_id == organization_id,
            RiskEpisodeModel.episode_status.in_(["OPEN", "MONITORING"]),
        )
    )
    open_episodes = (await session.execute(open_episodes_stmt)).scalar_one()

    # Improving vs deteriorating — single query via ROW_NUMBER to avoid N+1.
    # Left-join suppliers with their latest score; NULL trend → needing_review.
    from sqlalchemy import and_

    latest_score_subq = (
        select(
            SupplierScoreModel.supplier_id,
            SupplierScoreModel.trend,
            func.row_number()
            .over(
                partition_by=SupplierScoreModel.supplier_id,
                order_by=SupplierScoreModel.created_at.desc(),
            )
            .label("rn"),
        )
        .where(SupplierScoreModel.organization_id == organization_id)
        .subquery()
    )

    trend_stmt = (
        select(SupplierModel.id, latest_score_subq.c.trend)
        .outerjoin(
            latest_score_subq,
            and_(
                latest_score_subq.c.supplier_id == SupplierModel.id,
                latest_score_subq.c.rn == 1,
            ),
        )
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.supplier_status == "Active",
        )
    )
    trend_rows = (await session.execute(trend_stmt)).all()

    improving, deteriorating, stable, needing_review = 0, 0, 0, 0
    for row in trend_rows:
        trend = row.trend
        if trend is None:
            needing_review += 1
        elif trend == "Improving":
            improving += 1
        elif trend == "Deteriorating":
            deteriorating += 1
        else:
            stable += 1

    return {
        "total_suppliers": total_suppliers,
        "suppliers_at_risk": suppliers_at_risk,
        "suppliers_improving": improving,
        "suppliers_deteriorating": deteriorating,
        "suppliers_stable": stable,
        "suppliers_needing_review": needing_review,
        "watchlist_count": watchlist_count,
        "active_signals": active_signals,
        "critical_signals": critical_signals,
        "open_episodes": open_episodes,
    }


async def compute_heatmap(organization_id: str, dimension: str, session) -> list[dict]:
    """Compute risk heatmap by dimension: geography | sector | severity | esg_pillar."""

    allowed = {"geography", "sector", "severity", "esg_pillar"}
    if dimension not in allowed:
        raise ValueError(f"Invalid heatmap dimension: {dimension}")

    if dimension == "geography":
        return await _heatmap_by_geography(organization_id, session)
    elif dimension == "sector":
        return await _heatmap_by_sector(organization_id, session)
    elif dimension == "severity":
        return await _heatmap_by_severity(organization_id, session)
    else:
        return await _heatmap_by_esg_pillar(organization_id, session)


_RANK_TO_SEVERITY = {4: "CRITICAL", 3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "NONE"}


async def _heatmap_by_geography(organization_id: str, session) -> list[dict]:
    """Geography heatmap.

    P3 fixes applied:
    - signal_status == ACTIVE filter moved into JOIN ON (preserves LEFT JOIN semantics).
    - func.max(severity string) replaced with numeric rank CASE expression so that
      CRITICAL > HIGH > MEDIUM > LOW rather than alphabetical C < H < L < M.
    """
    from sqlalchemy import and_, case, func, select

    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    severity_rank = case(
        (SurveillanceSignalModel.severity == "CRITICAL", 4),
        (SurveillanceSignalModel.severity == "HIGH", 3),
        (SurveillanceSignalModel.severity == "MEDIUM", 2),
        (SurveillanceSignalModel.severity == "LOW", 1),
        else_=0,
    )

    stmt = (
        select(
            SupplierModel.country,
            func.count(SurveillanceSignalModel.id.distinct()).label("signal_count"),
            func.max(severity_rank).label("max_rank"),
        )
        .join(
            SurveillanceSignalModel,
            and_(
                SurveillanceSignalModel.supplier_id == SupplierModel.id,
                SurveillanceSignalModel.signal_status == "ACTIVE",
            ),
            isouter=True,
        )
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.supplier_status == "Active",
        )
        .group_by(SupplierModel.country)
        .order_by(func.count(SurveillanceSignalModel.id.distinct()).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "dimension": "geography",
            "key": r.country or "Unknown",
            "signal_count": r.signal_count or 0,
            "max_severity": _RANK_TO_SEVERITY.get(r.max_rank or 0, "NONE"),
        }
        for r in rows
    ]


async def _heatmap_by_sector(organization_id: str, session) -> list[dict]:
    """Sector heatmap.

    P3 fix: signal_status == ACTIVE filter moved into JOIN ON to count only
    current active signals, consistent with the severity heatmap.
    """
    from sqlalchemy import and_, func, select

    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    stmt = (
        select(
            SupplierModel.industry,
            func.count(SurveillanceSignalModel.id.distinct()).label("signal_count"),
        )
        .join(
            SurveillanceSignalModel,
            and_(
                SurveillanceSignalModel.supplier_id == SupplierModel.id,
                SurveillanceSignalModel.signal_status == "ACTIVE",
            ),
            isouter=True,
        )
        .where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.supplier_status == "Active",
        )
        .group_by(SupplierModel.industry)
        .order_by(func.count(SurveillanceSignalModel.id.distinct()).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "dimension": "sector",
            "key": getattr(r, "industry", None) or "Unknown",
            "signal_count": r.signal_count or 0,
            "max_severity": "N/A",
        }
        for r in rows
    ]


async def _heatmap_by_severity(organization_id: str, session) -> list[dict]:
    from sqlalchemy import func, select

    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    stmt = (
        select(
            SurveillanceSignalModel.severity,
            func.count(SurveillanceSignalModel.id).label("signal_count"),
        )
        .where(
            SurveillanceSignalModel.organization_id == organization_id,
            SurveillanceSignalModel.signal_status == "ACTIVE",
        )
        .group_by(SurveillanceSignalModel.severity)
        .order_by(func.count(SurveillanceSignalModel.id).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "dimension": "severity",
            "key": r.severity,
            "signal_count": r.signal_count,
            "max_severity": r.severity,
        }
        for r in rows
    ]


async def _heatmap_by_esg_pillar(organization_id: str, session) -> list[dict]:
    from sqlalchemy import func, select

    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    # Map signal_type to pillar
    pillars = {
        "E": ["DRIFT", "EMERGING_RISK"],
        "S": ["EARLY_WARNING", "CORRELATED_RISK"],
        "G": ["PREDICTIVE_ESCALATION"],
    }
    results = []
    for pillar, types in pillars.items():
        stmt = (
            select(func.count())
            .select_from(SurveillanceSignalModel)
            .where(
                SurveillanceSignalModel.organization_id == organization_id,
                SurveillanceSignalModel.signal_status == "ACTIVE",
                SurveillanceSignalModel.signal_type.in_(types),
            )
        )
        count = (await session.execute(stmt)).scalar_one()
        results.append(
            {
                "dimension": "esg_pillar",
                "key": pillar,
                "signal_count": count,
                "max_severity": "N/A",
            }
        )
    return results


async def compute_supplier_risk_timeline(
    supplier_id: str,
    organization_id: str,
    session,
    limit: int = 100,
) -> list[dict]:
    """Chronological risk timeline for a supplier."""
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import (
        AgentFindingModel,
    )
    from infrastructure.persistence.models.supplier_score import SupplierScoreModel
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    events: list[dict] = []

    # Surveillance signals
    sig_stmt = (
        select(SurveillanceSignalModel)
        .where(
            SurveillanceSignalModel.organization_id == organization_id,
            SurveillanceSignalModel.supplier_id == supplier_id,
        )
        .order_by(SurveillanceSignalModel.detected_at.desc())
        .limit(limit)
    )
    for s in (await session.execute(sig_stmt)).scalars().all():
        events.append(
            {
                "event_type": "signal",
                "timestamp": s.detected_at,
                "title": s.title,
                "severity": s.severity,
                "entity_id": s.id,
                "signal_type": s.signal_type,
            }
        )

    # Agent findings
    finding_stmt = (
        select(AgentFindingModel)
        .where(
            AgentFindingModel.organization_id == organization_id,
            AgentFindingModel.supplier_id == supplier_id,
        )
        .order_by(AgentFindingModel.created_at.desc())
        .limit(limit)
    )
    for f in (await session.execute(finding_stmt)).scalars().all():
        events.append(
            {
                "event_type": "finding",
                "timestamp": f.created_at,
                "title": f.title,
                "severity": f.severity,
                "entity_id": f.id,
                "signal_type": None,
            }
        )

    # Score changes
    score_stmt = (
        select(SupplierScoreModel)
        .where(
            SupplierScoreModel.supplier_id == supplier_id,
            SupplierScoreModel.organization_id == organization_id,
        )
        .order_by(SupplierScoreModel.created_at.desc())
        .limit(12)
    )
    for sc in (await session.execute(score_stmt)).scalars().all():
        events.append(
            {
                "event_type": "score_change",
                "timestamp": sc.created_at,
                "title": f"ESG score: {sc.esg_score:.1f} (risk: {sc.risk_score:.1f})",
                "severity": "INFO",
                "entity_id": sc.id,
                "signal_type": None,
            }
        )

    # Sort chronologically descending
    events.sort(key=lambda e: e["timestamp"] or datetime.min.replace(tzinfo=UTC), reverse=True)
    return events[:limit]


async def update_risk_trends(organization_id: str, session) -> int:
    """Compute and upsert monthly RiskTrend records for all suppliers."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.supplier_score import SupplierScoreModel
    from infrastructure.persistence.models.surveillance import RiskTrendModel

    now = datetime.now(UTC)
    period = now.strftime("%Y-%m")

    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
    )
    suppliers = list((await session.execute(suppliers_stmt)).scalars().all())

    updated = 0
    for supplier in suppliers:
        # Two most recent scores
        scores_stmt = (
            select(SupplierScoreModel)
            .where(
                SupplierScoreModel.supplier_id == supplier.id,
                SupplierScoreModel.organization_id == organization_id,
            )
            .order_by(SupplierScoreModel.created_at.desc())
            .limit(2)
        )
        scores = list((await session.execute(scores_stmt)).scalars().all())
        if len(scores) < 1:
            continue

        current = scores[0]
        previous = scores[1] if len(scores) > 1 else current

        esg_delta = current.esg_score - previous.esg_score
        if esg_delta < -5:
            trend = "DETERIORATING"
        elif esg_delta > 5:
            trend = "IMPROVING"
        else:
            trend = "STABLE"

        # Check existing trend record
        existing_stmt = select(RiskTrendModel).where(
            RiskTrendModel.organization_id == organization_id,
            RiskTrendModel.supplier_id == supplier.id,
            RiskTrendModel.period == period,
        )
        existing = (await session.execute(existing_stmt)).scalar_one_or_none()

        if existing:
            existing.esg_score_end = current.esg_score
            existing.risk_score_end = current.risk_score
            existing.score_delta = esg_delta
            existing.trend = trend
            existing.computed_at = now
            existing.updated_at = now
        else:
            trend_record = RiskTrendModel(
                id=str(uuid.uuid4()),
                status="Active",
                version=1,
                created_at=now,
                updated_at=now,
                organization_id=organization_id,
                supplier_id=supplier.id,
                period=period,
                esg_score_start=previous.esg_score,
                esg_score_end=current.esg_score,
                risk_score_start=previous.risk_score,
                risk_score_end=current.risk_score,
                score_delta=esg_delta,
                trend=trend,
                confidence=0.90,
                computed_at=now,
            )
            session.add(trend_record)
        updated += 1

    await session.flush()
    return updated
