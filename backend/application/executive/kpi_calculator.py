"""
M29 KPI Calculator

Pure functions that transform raw query results into KPI structures.
No I/O.  All computation is deterministic and testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Data structures ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class KPISnapshot:
    total_suppliers: int = 0
    scored_suppliers: int = 0
    critical_risk_suppliers: int = 0
    high_risk_suppliers: int = 0
    moderate_risk_suppliers: int = 0
    low_risk_suppliers: int = 0
    improving_suppliers: int = 0
    deteriorating_suppliers: int = 0
    avg_esg_score: float | None = None
    avg_risk_score: float | None = None
    risk_distribution: dict[str, int] = field(default_factory=dict)
    open_actions: int = 0
    overdue_actions: int = 0
    total_actions: int = 0
    resolution_rate: float | None = None
    assessments_awaiting_review: int = 0
    assessments_approved: int = 0
    critical_findings_total: int = 0


@dataclass(frozen=True)
class MonthlyDataPoint:
    month: str  # "YYYY-MM"
    avg_esg_score: float | None = None
    avg_risk_score: float | None = None
    supplier_count: int = 0
    high_risk_count: int = 0
    critical_risk_count: int = 0
    risk_distribution: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class KPITrendResult:
    period_days: int
    data_points: list[MonthlyDataPoint] = field(default_factory=list)
    current_snapshot: KPISnapshot | None = None
    esg_delta: float | None = None
    risk_delta: float | None = None


# ── Portfolio summary ─────────────────────────────────────────────────────────


def compute_portfolio_summary(
    total_suppliers: int,
    scores: list[dict],
    open_actions: int,
    overdue_actions: int,
    total_actions: int,
    assessments_awaiting_review: int,
    assessments_approved: int,
    critical_findings_total: int,
) -> KPISnapshot:
    """
    Build a KPISnapshot from pre-fetched aggregate data.

    `scores` is a list of latest score records for the org:
      [{"esg_score": float, "risk_score": float, "risk_band": str, "trend": str}, ...]
    """
    n = len(scores)
    dist: dict[str, int] = {"Low": 0, "Moderate": 0, "High": 0, "Critical": 0}
    total_esg = total_risk = 0.0
    improving = deteriorating = 0

    for s in scores:
        band = s.get("risk_band", "Low")
        dist[band] = dist.get(band, 0) + 1
        total_esg += s.get("esg_score", 0.0)
        total_risk += s.get("risk_score", 0.0)
        trend = s.get("trend", "Stable")
        if trend == "Improving":
            improving += 1
        elif trend == "Deteriorating":
            deteriorating += 1

    closed_actions = total_actions - open_actions
    resolution_rate = round(closed_actions / total_actions, 3) if total_actions > 0 else None

    return KPISnapshot(
        total_suppliers=total_suppliers,
        scored_suppliers=n,
        critical_risk_suppliers=dist.get("Critical", 0),
        high_risk_suppliers=dist.get("High", 0),
        moderate_risk_suppliers=dist.get("Moderate", 0),
        low_risk_suppliers=dist.get("Low", 0),
        improving_suppliers=improving,
        deteriorating_suppliers=deteriorating,
        avg_esg_score=round(total_esg / n, 1) if n else None,
        avg_risk_score=round(total_risk / n, 1) if n else None,
        risk_distribution=dist,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
        total_actions=total_actions,
        resolution_rate=resolution_rate,
        assessments_awaiting_review=assessments_awaiting_review,
        assessments_approved=assessments_approved,
        critical_findings_total=critical_findings_total,
    )


# ── KPI trends ────────────────────────────────────────────────────────────────


def compute_kpi_trends(
    monthly_rows: list[dict],
    period_days: int,
    current_snapshot: KPISnapshot | None = None,
) -> KPITrendResult:
    """
    Build a KPI trend result from monthly aggregated score rows.

    Each row in `monthly_rows`:
      {"month": "YYYY-MM", "avg_esg": float, "avg_risk": float,
       "count": int, "dist": {"Low":n, "Moderate":n, "High":n, "Critical":n}}
    """
    points: list[MonthlyDataPoint] = []
    for row in sorted(monthly_rows, key=lambda r: r["month"]):
        dist = row.get("dist", {})
        points.append(
            MonthlyDataPoint(
                month=row["month"],
                avg_esg_score=row.get("avg_esg"),
                avg_risk_score=row.get("avg_risk"),
                supplier_count=row.get("count", 0),
                high_risk_count=dist.get("High", 0),
                critical_risk_count=dist.get("Critical", 0),
                risk_distribution=dist,
            )
        )

    # Compute deltas: first vs last month in window
    esg_delta = risk_delta = None
    if len(points) >= 2:
        first, last = points[0], points[-1]
        if first.avg_esg_score is not None and last.avg_esg_score is not None:
            esg_delta = round(last.avg_esg_score - first.avg_esg_score, 1)
        if first.avg_risk_score is not None and last.avg_risk_score is not None:
            risk_delta = round(last.avg_risk_score - first.avg_risk_score, 1)

    return KPITrendResult(
        period_days=period_days,
        data_points=points,
        current_snapshot=current_snapshot,
        esg_delta=esg_delta,
        risk_delta=risk_delta,
    )


# ── Action effectiveness ──────────────────────────────────────────────────────


def compute_action_effectiveness(
    opened_this_period: int,
    closed_this_period: int,
    total_open: int,
    total_overdue: int,
    avg_resolution_days: float | None,
) -> dict:
    """Build action effectiveness metrics dict."""
    resolution_rate = (
        round(closed_this_period / (opened_this_period + closed_this_period), 3)
        if (opened_this_period + closed_this_period) > 0
        else None
    )
    return {
        "opened_this_period": opened_this_period,
        "closed_this_period": closed_this_period,
        "total_open": total_open,
        "total_overdue": total_overdue,
        "resolution_rate": resolution_rate,
        "avg_resolution_days": avg_resolution_days,
    }


# ── Governance effectiveness ──────────────────────────────────────────────────


def compute_governance_metrics(
    total_decisions: int,
    approved: int,
    rejected: int,
    changes_requested: int,
    avg_review_days: float | None,
) -> dict:
    """Build governance effectiveness metrics dict."""

    def _rate(n: int) -> float | None:
        return round(n / total_decisions, 3) if total_decisions > 0 else None

    return {
        "total_review_decisions": total_decisions,
        "approved": approved,
        "rejected": rejected,
        "changes_requested": changes_requested,
        "approval_rate": _rate(approved),
        "rejection_rate": _rate(rejected),
        "changes_requested_rate": _rate(changes_requested),
        "avg_review_days": avg_review_days,
    }
