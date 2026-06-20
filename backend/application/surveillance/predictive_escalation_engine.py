"""M37 Predictive Escalation Engine.

Deterministic rule-based only. No LLM predictions.
Combines multiple signals to generate HIGH escalation recommendations.

Rules:
  - Rising risk score (3 months) AND overdue remediation → HIGH escalation
  - 3+ active DRIFT signals AND watchlist → CRITICAL escalation
  - EMERGING_RISK + EARLY_WARNING in same 30d window → HIGH escalation
"""

from __future__ import annotations

import structlog

from application.surveillance.signal_service import create_signal
from application.surveillance.metrics import surveillance_counters

logger = structlog.get_logger(__name__)

_RISK_TREND_MONTHS = 3          # rising risk for 3 consecutive months
_MIN_DRIFT_SIGNALS = 3          # drift signals on watchlist supplier
_COMBINED_SIGNAL_WINDOW_DAYS = 30


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    from infrastructure.persistence.models.supplier import SupplierModel
    from sqlalchemy import select

    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
    )
    suppliers = list((await session.execute(suppliers_stmt)).scalars().all())

    signals_created = 0
    for supplier in suppliers:
        signals_created += await _rule_rising_risk_plus_overdue(
            supplier, organization_id, session
        )
        signals_created += await _rule_watchlist_with_multiple_drift(
            supplier, organization_id, session
        )
        signals_created += await _rule_combined_emerging_early_warning(
            supplier, organization_id, session
        )

    return signals_created


async def _rule_rising_risk_plus_overdue(supplier, organization_id: str, session) -> int:
    """IF risk score rising 3 months AND remediation overdue → HIGH escalation."""
    from infrastructure.persistence.models.risk import RiskTrendModel as ScoreTrend
    from sqlalchemy import select
    from datetime import UTC, datetime

    # Check for rising risk in trends
    try:
        from infrastructure.persistence.models.surveillance import RiskTrendModel
        trend_stmt = (
            select(RiskTrendModel)
            .where(
                RiskTrendModel.organization_id == organization_id,
                RiskTrendModel.supplier_id == supplier.id,
                RiskTrendModel.trend == "DETERIORATING",
            )
            .order_by(RiskTrendModel.period.desc())
            .limit(_RISK_TREND_MONTHS)
        )
        trends = list((await session.execute(trend_stmt)).scalars().all())
        rising_months = len(trends)
    except Exception:
        rising_months = 0

    if rising_months < _RISK_TREND_MONTHS:
        # Fallback: check raw score history
        try:
            from infrastructure.persistence.models.supplier_score import SupplierScoreModel

            scores_stmt = (
                select(SupplierScoreModel)
                .where(
                    SupplierScoreModel.supplier_id == supplier.id,
                    SupplierScoreModel.organization_id == organization_id,
                )
                .order_by(SupplierScoreModel.created_at.desc())
                .limit(4)
            )
            scores = list((await session.execute(scores_stmt)).scalars().all())
            if len(scores) < 4:
                return 0
            rising_months = sum(
                1 for i in range(len(scores) - 1)
                if scores[i].risk_score > scores[i + 1].risk_score
            )
        except Exception:
            return 0

    if rising_months < _RISK_TREND_MONTHS:
        return 0

    # Check overdue remediation
    overdue = 0
    try:
        from infrastructure.persistence.models.risk import RemediationPlanModel
        from sqlalchemy import func

        overdue_stmt = select(func.count()).select_from(RemediationPlanModel).where(
            RemediationPlanModel.organization_id == organization_id,
            RemediationPlanModel.supplier_id == supplier.id,
            RemediationPlanModel.plan_status == "OVERDUE",
        )
        overdue = (await session.execute(overdue_stmt)).scalar_one()
    except Exception:
        pass

    if overdue == 0:
        return 0

    month = datetime.now(UTC).strftime("%Y-%m")
    dedupe = f"predictive:rising_risk_overdue:{supplier.id}:{month}"
    await create_signal(
        organization_id=organization_id,
        signal_type="PREDICTIVE_ESCALATION",
        source_type="predictive_engine",
        severity="HIGH",
        title=f"Predictive escalation: rising risk + overdue remediation ({supplier.name})",
        description=(
            f"Risk score rising for {rising_months} consecutive periods "
            f"and {overdue} overdue remediation plan(s)."
        ),
        confidence=0.85,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "rising_risk_score_and_overdue_remediation",
            "rationale": (
                "IF risk_score rising >= 3 periods AND remediation_overdue > 0 "
                "THEN generate HIGH escalation recommendation"
            ),
            "source_data": {
                "rising_risk_periods": rising_months,
                "overdue_remediation_count": overdue,
            },
            "thresholds": {
                "min_rising_periods": _RISK_TREND_MONTHS,
                "min_overdue": 1,
            },
        },
        session=session,
    )
    surveillance_counters.record_escalation()
    return 1


async def _rule_watchlist_with_multiple_drift(supplier, organization_id: str, session) -> int:
    """IF supplier on watchlist AND >= 3 active DRIFT signals → CRITICAL escalation."""
    from infrastructure.persistence.models.surveillance import (
        SupplierWatchlistModel,
        SurveillanceSignalModel,
    )
    from sqlalchemy import func, select
    from datetime import UTC, datetime

    watchlist_stmt = select(SupplierWatchlistModel).where(
        SupplierWatchlistModel.organization_id == organization_id,
        SupplierWatchlistModel.supplier_id == supplier.id,
        SupplierWatchlistModel.watchlist_status == "ACTIVE",
    )
    on_watchlist = (await session.execute(watchlist_stmt)).scalar_one_or_none()
    if on_watchlist is None:
        return 0

    drift_count_stmt = select(func.count()).select_from(SurveillanceSignalModel).where(
        SurveillanceSignalModel.organization_id == organization_id,
        SurveillanceSignalModel.supplier_id == supplier.id,
        SurveillanceSignalModel.signal_type == "DRIFT",
        SurveillanceSignalModel.signal_status == "ACTIVE",
    )
    drift_count = (await session.execute(drift_count_stmt)).scalar_one()
    if drift_count < _MIN_DRIFT_SIGNALS:
        return 0

    month = datetime.now(UTC).strftime("%Y-%m")
    dedupe = f"predictive:watchlist_drift:{supplier.id}:{month}"
    await create_signal(
        organization_id=organization_id,
        signal_type="PREDICTIVE_ESCALATION",
        source_type="predictive_engine",
        severity="CRITICAL",
        title=f"Critical predictive escalation: watchlisted supplier with multiple drift ({supplier.name})",
        description=(
            f"Supplier is on watchlist and has {drift_count} active drift signals."
        ),
        confidence=0.90,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "watchlist_plus_multiple_drift_signals",
            "rationale": (
                "IF supplier ON watchlist AND active DRIFT signals >= 3 "
                "THEN generate CRITICAL escalation recommendation"
            ),
            "source_data": {
                "on_watchlist": True,
                "active_drift_signals": drift_count,
            },
            "thresholds": {
                "min_drift_signals": _MIN_DRIFT_SIGNALS,
            },
        },
        session=session,
    )
    surveillance_counters.record_escalation()
    return 1


async def _rule_combined_emerging_early_warning(
    supplier, organization_id: str, session
) -> int:
    """IF EMERGING_RISK + EARLY_WARNING in same 30d window → HIGH escalation."""
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from sqlalchemy import func, select
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=_COMBINED_SIGNAL_WINDOW_DAYS)

    for sig_type in ["EMERGING_RISK", "EARLY_WARNING"]:
        stmt = select(func.count()).select_from(SurveillanceSignalModel).where(
            SurveillanceSignalModel.organization_id == organization_id,
            SurveillanceSignalModel.supplier_id == supplier.id,
            SurveillanceSignalModel.signal_type == sig_type,
            SurveillanceSignalModel.signal_status == "ACTIVE",
            SurveillanceSignalModel.detected_at >= cutoff,
        )
        count = (await session.execute(stmt)).scalar_one()
        if count == 0:
            return 0

    month = datetime.now(UTC).strftime("%Y-%m")
    dedupe = f"predictive:combined_emerging_warning:{supplier.id}:{month}"
    await create_signal(
        organization_id=organization_id,
        signal_type="PREDICTIVE_ESCALATION",
        source_type="predictive_engine",
        severity="HIGH",
        title=f"Combined risk pattern: {supplier.name}",
        description=(
            "Emerging risk and early warning signals co-occurring in the last 30 days."
        ),
        confidence=0.80,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "emerging_risk_plus_early_warning_combined",
            "rationale": (
                "IF EMERGING_RISK signal AND EARLY_WARNING signal within 30 days "
                "THEN generate HIGH escalation recommendation"
            ),
            "source_data": {"window_days": _COMBINED_SIGNAL_WINDOW_DAYS},
            "thresholds": {
                "min_emerging_signals": 1,
                "min_early_warning_signals": 1,
                "window_days": _COMBINED_SIGNAL_WINDOW_DAYS,
            },
        },
        session=session,
    )
    surveillance_counters.record_escalation()
    return 1
