"""M37 Risk Drift Detection Engine.

Detects gradual deterioration in ESG scores, risk scores, compliance status,
and due diligence status. Integrates with M28 (SupplierScore), M31 (compliance),
M32 (due diligence).

Thresholds are calibrated to avoid noise while catching meaningful drift.
"""

from __future__ import annotations

import structlog

from application.surveillance.signal_service import create_signal
from application.surveillance.watchlist_service import auto_watchlist_from_score_drop

logger = structlog.get_logger(__name__)

# ESG score decline thresholds (negative = decline)
_ESG_DRIFT_MINOR = -5.0
_ESG_DRIFT_MODERATE = -10.0
_ESG_DRIFT_SEVERE = -20.0

# Risk score increase thresholds (positive = worse)
_RISK_DRIFT_MODERATE = 10.0
_RISK_DRIFT_SEVERE = 20.0
_RISK_DRIFT_CRITICAL = 30.0

# Compliance: percentage of gaps worsening
_COMPLIANCE_GAP_THRESHOLD = 3  # new gaps in last 30 days


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    """Run drift detection for one organization. Returns signal count."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier import SupplierModel

    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
    )
    suppliers = list((await session.execute(suppliers_stmt)).scalars().all())

    signals_created = 0
    for supplier in suppliers:
        signals_created += await _check_score_drift(supplier, organization_id, session)
        signals_created += await _check_compliance_drift(supplier, organization_id, session)
        signals_created += await _check_due_diligence_drift(supplier, organization_id, session)

    return signals_created


async def _check_score_drift(supplier, organization_id: str, session) -> int:
    """Compare latest two score snapshots. Generate drift signal on decline."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_score import SupplierScoreModel

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
    if len(scores) < 2:
        return 0

    current, previous = scores[0], scores[1]
    esg_delta = current.esg_score - previous.esg_score
    risk_delta = current.risk_score - previous.risk_score

    signals = 0

    # ESG score decline
    if esg_delta <= _ESG_DRIFT_SEVERE:
        severity, label = "CRITICAL", "SEVERE"
    elif esg_delta <= _ESG_DRIFT_MODERATE:
        severity, label = "HIGH", "MODERATE"
    elif esg_delta <= _ESG_DRIFT_MINOR:
        severity, label = "MEDIUM", "MINOR"
    else:
        severity = label = None

    if severity:
        dedupe = f"drift:esg:{supplier.id}:{current.id}"
        await create_signal(
            organization_id=organization_id,
            signal_type="DRIFT",
            source_type="supplier_score",
            source_id=current.id,
            severity=severity,
            title=f"{label} ESG score decline: {supplier.name}",
            description=(
                f"ESG score dropped {abs(esg_delta):.1f} points "
                f"({previous.esg_score:.1f} → {current.esg_score:.1f})"
            ),
            confidence=0.95,
            supplier_id=supplier.id,
            dedupe_key=dedupe,
            explainability={
                "rule_triggered": f"esg_score_decline_{label.lower()}",
                "source_data": {
                    "esg_score_previous": previous.esg_score,
                    "esg_score_current": current.esg_score,
                    "esg_delta": esg_delta,
                },
                "thresholds": {
                    "minor": _ESG_DRIFT_MINOR,
                    "moderate": _ESG_DRIFT_MODERATE,
                    "severe": _ESG_DRIFT_SEVERE,
                },
            },
            session=session,
        )
        signals += 1
        # Auto-watchlist on score drop
        await auto_watchlist_from_score_drop(organization_id, supplier.id, esg_delta, session)

    # Risk score increase
    if risk_delta >= _RISK_DRIFT_CRITICAL:
        r_severity, r_label = "CRITICAL", "CRITICAL"
    elif risk_delta >= _RISK_DRIFT_SEVERE:
        r_severity, r_label = "HIGH", "SEVERE"
    elif risk_delta >= _RISK_DRIFT_MODERATE:
        r_severity, r_label = "MEDIUM", "MODERATE"
    else:
        r_severity = r_label = None

    if r_severity:
        r_dedupe = f"drift:risk:{supplier.id}:{current.id}"
        await create_signal(
            organization_id=organization_id,
            signal_type="DRIFT",
            source_type="supplier_score",
            source_id=current.id,
            severity=r_severity,
            title=f"{r_label} risk score increase: {supplier.name}",
            description=(
                f"Risk score increased {risk_delta:.1f} points "
                f"({previous.risk_score:.1f} → {current.risk_score:.1f})"
            ),
            confidence=0.95,
            supplier_id=supplier.id,
            dedupe_key=r_dedupe,
            explainability={
                "rule_triggered": f"risk_score_increase_{r_label.lower()}",
                "source_data": {
                    "risk_score_previous": previous.risk_score,
                    "risk_score_current": current.risk_score,
                    "risk_delta": risk_delta,
                },
                "thresholds": {
                    "moderate": _RISK_DRIFT_MODERATE,
                    "severe": _RISK_DRIFT_SEVERE,
                    "critical": _RISK_DRIFT_CRITICAL,
                },
            },
            session=session,
        )
        signals += 1

    return signals


async def _check_compliance_drift(supplier, organization_id: str, session) -> int:
    """Detect new compliance gaps opened in last 30 days for this supplier."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import func, select

    from infrastructure.persistence.models.regulatory import ComplianceGapModel

    cutoff = datetime.now(UTC) - timedelta(days=30)
    gap_stmt = (
        select(func.count())
        .select_from(ComplianceGapModel)
        .where(
            ComplianceGapModel.organization_id == organization_id,
            ComplianceGapModel.entity_id == supplier.id,
            ComplianceGapModel.gap_status == "OPEN",
            ComplianceGapModel.created_at >= cutoff,
        )
    )
    new_gaps = (await session.execute(gap_stmt)).scalar_one()
    if new_gaps < _COMPLIANCE_GAP_THRESHOLD:
        return 0

    dedupe = f"drift:compliance:{supplier.id}:{cutoff.date().isoformat()}"
    await create_signal(
        organization_id=organization_id,
        signal_type="DRIFT",
        source_type="compliance_gap",
        severity="HIGH",
        title=f"Compliance deterioration: {supplier.name}",
        description=f"{new_gaps} new compliance gaps opened in the last 30 days",
        confidence=0.90,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "compliance_gap_count_threshold",
            "source_data": {"new_gaps_30d": new_gaps},
            "thresholds": {"min_gaps": _COMPLIANCE_GAP_THRESHOLD},
        },
        session=session,
    )
    return 1


async def _check_due_diligence_drift(supplier, organization_id: str, session) -> int:
    """Detect deterioration in due diligence findings (M32 integration)."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import func, select

    # Avoid hard import failure if M32 table doesn't exist yet
    try:
        from infrastructure.persistence.models.due_diligence import DueDiligenceFindingModel
    except ImportError:
        return 0

    cutoff = datetime.now(UTC) - timedelta(days=30)
    try:
        stmt = (
            select(func.count())
            .select_from(DueDiligenceFindingModel)
            .where(
                DueDiligenceFindingModel.organization_id == organization_id,
                DueDiligenceFindingModel.supplier_id == supplier.id,
                DueDiligenceFindingModel.created_at >= cutoff,
            )
        )
        new_findings = (await session.execute(stmt)).scalar_one()
    except Exception:
        return 0

    if new_findings < 2:
        return 0

    dedupe = f"drift:due_diligence:{supplier.id}:{cutoff.date().isoformat()}"
    await create_signal(
        organization_id=organization_id,
        signal_type="DRIFT",
        source_type="due_diligence",
        severity="HIGH",
        title=f"Due diligence deterioration: {supplier.name}",
        description=f"{new_findings} new due diligence findings in the last 30 days",
        confidence=0.85,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "due_diligence_finding_count",
            "source_data": {"new_findings_30d": new_findings},
            "thresholds": {"min_findings": 2},
        },
        session=session,
    )
    return 1
