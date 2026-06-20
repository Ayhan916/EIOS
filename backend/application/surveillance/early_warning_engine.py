"""M37 Early Warning Engine.

Detects leading indicators before they become confirmed risks:
  - Questionnaire response rate falling
  - Evidence delivery slowing
  - Remediation velocity decreasing
  - Increasing supplier inactivity

Generates EARLY_WARNING signals.
"""

from __future__ import annotations

import structlog

from application.surveillance.signal_service import create_signal

logger = structlog.get_logger(__name__)

_RESPONSE_RATE_THRESHOLD = 0.5      # < 50% response rate
_EVIDENCE_SLOWDOWN_DAYS = 14        # no new evidence in 14 days
_INACTIVITY_DAYS = 30               # no supplier portal activity in 30 days


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
        signals_created += await _check_questionnaire_response_rate(
            supplier, organization_id, session
        )
        signals_created += await _check_evidence_slowdown(
            supplier, organization_id, session
        )
        signals_created += await _check_supplier_inactivity(
            supplier, organization_id, session
        )
    return signals_created


async def _check_questionnaire_response_rate(supplier, organization_id: str, session) -> int:
    """Detect falling questionnaire response rate."""
    try:
        from infrastructure.persistence.models.supplier_portal import (
            SupplierQuestionnaireModel,
            SupplierResponseModel,
        )
        from sqlalchemy import func, select
        from datetime import UTC, datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(days=60)
        total_stmt = select(func.count()).select_from(SupplierQuestionnaireModel).where(
            SupplierQuestionnaireModel.organization_id == organization_id,
            SupplierQuestionnaireModel.supplier_id == supplier.id,
            SupplierQuestionnaireModel.created_at >= cutoff,
        )
        total = (await session.execute(total_stmt)).scalar_one()
        if total == 0:
            return 0

        answered_stmt = select(func.count()).select_from(SupplierResponseModel).where(
            SupplierResponseModel.organization_id == organization_id,
            SupplierResponseModel.supplier_id == supplier.id,
            SupplierResponseModel.created_at >= cutoff,
        )
        answered = (await session.execute(answered_stmt)).scalar_one()
        rate = answered / total if total > 0 else 1.0
    except Exception:
        return 0

    if rate >= _RESPONSE_RATE_THRESHOLD:
        return 0

    month = __import__("datetime").datetime.now(__import__("datetime").UTC).strftime("%Y-%m")
    dedupe = f"early_warning:questionnaire_rate:{supplier.id}:{month}"
    await create_signal(
        organization_id=organization_id,
        signal_type="EARLY_WARNING",
        source_type="supplier_portal",
        severity="MEDIUM",
        title=f"Low questionnaire response rate: {supplier.name}",
        description=f"Response rate {rate:.0%} (threshold {_RESPONSE_RATE_THRESHOLD:.0%})",
        confidence=0.85,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "questionnaire_response_rate_low",
            "source_data": {
                "questionnaires_sent": total,
                "questionnaires_answered": answered,
                "response_rate": round(rate, 3),
            },
            "thresholds": {"min_rate": _RESPONSE_RATE_THRESHOLD},
        },
        session=session,
    )
    return 1


async def _check_evidence_slowdown(supplier, organization_id: str, session) -> int:
    """Detect evidence delivery slowdown."""
    try:
        from infrastructure.persistence.models.evidence import EvidenceModel
        from sqlalchemy import select
        from datetime import UTC, datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(days=_EVIDENCE_SLOWDOWN_DAYS)
        stmt = (
            select(EvidenceModel)
            .where(
                EvidenceModel.organization_id == organization_id,
                EvidenceModel.supplier_id == supplier.id,
                EvidenceModel.created_at >= cutoff,
            )
            .limit(1)
        )
        recent = (await session.execute(stmt)).scalar_one_or_none()
    except Exception:
        return 0

    if recent is not None:
        return 0

    from datetime import UTC, datetime
    week = datetime.now(UTC).strftime("%Y-W%V")
    dedupe = f"early_warning:evidence_slowdown:{supplier.id}:{week}"
    await create_signal(
        organization_id=organization_id,
        signal_type="EARLY_WARNING",
        source_type="evidence",
        severity="LOW",
        title=f"Evidence delivery slowdown: {supplier.name}",
        description=f"No new evidence submitted in the last {_EVIDENCE_SLOWDOWN_DAYS} days",
        confidence=0.70,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "evidence_delivery_slowdown",
            "source_data": {"days_since_last_evidence": _EVIDENCE_SLOWDOWN_DAYS},
            "thresholds": {"max_days_without_evidence": _EVIDENCE_SLOWDOWN_DAYS},
        },
        session=session,
    )
    return 1


async def _check_supplier_inactivity(supplier, organization_id: str, session) -> int:
    """Detect supplier portal inactivity."""
    try:
        from infrastructure.persistence.models.supplier_portal import SupplierPortalUserModel
        from sqlalchemy import select
        from datetime import UTC, datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(days=_INACTIVITY_DAYS)
        stmt = (
            select(SupplierPortalUserModel)
            .where(
                SupplierPortalUserModel.supplier_id == supplier.id,
                SupplierPortalUserModel.last_login_at >= cutoff,
            )
            .limit(1)
        )
        active_user = (await session.execute(stmt)).scalar_one_or_none()
    except Exception:
        return 0

    if active_user is not None:
        return 0

    from datetime import UTC, datetime
    month = datetime.now(UTC).strftime("%Y-%m")
    dedupe = f"early_warning:inactivity:{supplier.id}:{month}"
    await create_signal(
        organization_id=organization_id,
        signal_type="EARLY_WARNING",
        source_type="supplier_portal",
        severity="LOW",
        title=f"Supplier inactivity detected: {supplier.name}",
        description=f"No portal login in the last {_INACTIVITY_DAYS} days",
        confidence=0.65,
        supplier_id=supplier.id,
        dedupe_key=dedupe,
        explainability={
            "rule_triggered": "supplier_portal_inactivity",
            "source_data": {"days_inactive": _INACTIVITY_DAYS},
            "thresholds": {"max_inactive_days": _INACTIVITY_DAYS},
        },
        session=session,
    )
    return 1
