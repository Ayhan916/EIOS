"""M43 — Green Revenue, CapEx, and OpEx Tracking.

Green Revenue % = green_amount / total_revenue × 100
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.kpi_service import FinancialESGError, _now
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import (
    ALIGNMENT_STATUSES,
    GreenCapexRecordModel,
    GreenOpexRecordModel,
    GreenRevenueRecordModel,
)


def _green_pct(amount: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(amount / total * 100, 4)


# ── Green Revenue ─────────────────────────────────────────────────────────────

def create_green_revenue(
    organization_id: str,
    revenue_stream: str,
    amount: float,
    total_revenue: float,
    period: str,
    actor_id: str,
    session: Session,
    *,
    taxonomy_category: str | None = None,
    alignment_status: str = "ELIGIBLE",
    currency: str = "USD",
    notes: str | None = None,
) -> GreenRevenueRecordModel:
    if alignment_status not in ALIGNMENT_STATUSES:
        raise FinancialESGError(f"Invalid alignment_status: {alignment_status}")
    pct = _green_pct(amount, total_revenue)
    now = _now()
    rec = GreenRevenueRecordModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        revenue_stream=revenue_stream,
        taxonomy_category=taxonomy_category,
        amount=amount,
        currency=currency,
        period=period,
        alignment_status=alignment_status,
        total_revenue=total_revenue,
        green_revenue_percent=pct,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.green_revenue.created",
        actor_id=actor_id,
        resource_type="green_revenue_record",
        resource_id=rec.id,
        details={"period": period, "amount": amount, "green_revenue_percent": pct},
    )
    financial_esg_counters.record_green_revenue()
    return rec


def list_green_revenue(
    organization_id: str,
    session: Session,
    *,
    period: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[GreenRevenueRecordModel]:
    q = session.query(GreenRevenueRecordModel).filter(
        GreenRevenueRecordModel.organization_id == organization_id
    )
    if period:
        q = q.filter(GreenRevenueRecordModel.period == period)
    return q.order_by(GreenRevenueRecordModel.period.desc()).limit(limit).offset(offset).all()


def compute_green_revenue_percent(
    organization_id: str,
    period: str,
    session: Session,
) -> dict:
    rows = (
        session.query(GreenRevenueRecordModel)
        .filter(
            GreenRevenueRecordModel.organization_id == organization_id,
            GreenRevenueRecordModel.period == period,
            GreenRevenueRecordModel.alignment_status.in_(["ALIGNED", "ELIGIBLE"]),
        )
        .all()
    )
    total_green = sum(r.amount for r in rows)
    total_revenue = rows[0].total_revenue if rows else 0.0
    return {
        "period": period,
        "total_green_amount": total_green,
        "total_revenue": total_revenue,
        "green_revenue_percent": _green_pct(total_green, total_revenue),
    }


# ── Green CapEx ───────────────────────────────────────────────────────────────

def create_green_capex(
    organization_id: str,
    project_name: str,
    amount: float,
    alignment_percent: float,
    period: str,
    actor_id: str,
    session: Session,
    *,
    taxonomy_category: str | None = None,
    currency: str = "USD",
    notes: str | None = None,
) -> GreenCapexRecordModel:
    if not (0.0 <= alignment_percent <= 100.0):
        raise FinancialESGError("alignment_percent must be between 0 and 100")
    now = _now()
    rec = GreenCapexRecordModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        project_name=project_name,
        taxonomy_category=taxonomy_category,
        amount=amount,
        currency=currency,
        alignment_percent=alignment_percent,
        period=period,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.green_capex.created",
        actor_id=actor_id,
        resource_type="green_capex_record",
        resource_id=rec.id,
        details={"project_name": project_name, "amount": amount, "alignment_percent": alignment_percent},
    )
    financial_esg_counters.record_green_capex()
    return rec


def list_green_capex(
    organization_id: str,
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[GreenCapexRecordModel]:
    return (
        session.query(GreenCapexRecordModel)
        .filter(GreenCapexRecordModel.organization_id == organization_id)
        .order_by(GreenCapexRecordModel.period.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── Green OpEx ────────────────────────────────────────────────────────────────

def create_green_opex(
    organization_id: str,
    description: str,
    amount: float,
    alignment_percent: float,
    period: str,
    actor_id: str,
    session: Session,
    *,
    category: str | None = None,
    currency: str = "USD",
    notes: str | None = None,
) -> GreenOpexRecordModel:
    if not (0.0 <= alignment_percent <= 100.0):
        raise FinancialESGError("alignment_percent must be between 0 and 100")
    now = _now()
    rec = GreenOpexRecordModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        description=description,
        category=category,
        amount=amount,
        currency=currency,
        alignment_percent=alignment_percent,
        period=period,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.green_opex.created",
        actor_id=actor_id,
        resource_type="green_opex_record",
        resource_id=rec.id,
        details={"description": description, "amount": amount, "alignment_percent": alignment_percent},
    )
    financial_esg_counters.record_green_opex()
    return rec


def list_green_opex(
    organization_id: str,
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[GreenOpexRecordModel]:
    return (
        session.query(GreenOpexRecordModel)
        .filter(GreenOpexRecordModel.organization_id == organization_id)
        .order_by(GreenOpexRecordModel.period.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
