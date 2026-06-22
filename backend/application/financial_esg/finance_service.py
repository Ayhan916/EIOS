"""M43 — Sustainable Finance Framework and Linked KPI Management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.kpi_service import FinancialESGError, FinancialESGConflict, _assert_org, _now
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import (
    COVENANT_STATUSES,
    INSTRUMENT_TYPES,
    PLAN_STATUSES,
    THRESHOLD_DIRECTIONS,
    FinanceLinkedKPIModel,
    SustainableFinanceInstrumentModel,
    TransitionPlanMilestoneModel,
    TransitionPlanModel,
)


# ── Sustainable Finance Instruments ──────────────────────────────────────────

def create_finance_instrument(
    organization_id: str,
    name: str,
    instrument_type: str,
    amount: float,
    actor_id: str,
    session: Session,
    *,
    currency: str = "USD",
    maturity_date: datetime | None = None,
    issuer: str | None = None,
    counterparty: str | None = None,
    description: str | None = None,
    kpi_linkage: dict | None = None,
) -> SustainableFinanceInstrumentModel:
    if instrument_type not in INSTRUMENT_TYPES:
        raise FinancialESGError(f"Invalid instrument_type: {instrument_type}")
    now = _now()
    rec = SustainableFinanceInstrumentModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        instrument_type=instrument_type,
        amount=amount,
        currency=currency,
        maturity_date=maturity_date,
        covenant_status="MONITORING",
        issuer=issuer,
        counterparty=counterparty,
        description=description,
        kpi_linkage=kpi_linkage or {},
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.finance_instrument.created",
        actor_id=actor_id,
        resource_type="sustainable_finance_instrument",
        resource_id=rec.id,
        details={"name": name, "instrument_type": instrument_type, "amount": amount},
    )
    financial_esg_counters.record_finance_instrument()
    return rec


def list_finance_instruments(
    organization_id: str,
    session: Session,
    *,
    instrument_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SustainableFinanceInstrumentModel]:
    q = session.query(SustainableFinanceInstrumentModel).filter(
        SustainableFinanceInstrumentModel.organization_id == organization_id
    )
    if instrument_type:
        q = q.filter(SustainableFinanceInstrumentModel.instrument_type == instrument_type)
    return q.order_by(SustainableFinanceInstrumentModel.created_at.desc()).limit(limit).offset(offset).all()


# ── Sustainability Linked KPIs ────────────────────────────────────────────────

def create_linked_kpi(
    organization_id: str,
    instrument_id: str,
    kpi_name: str,
    actor_id: str,
    session: Session,
    *,
    esg_target_id: str | None = None,
    kpi_description: str | None = None,
    threshold_value: float | None = None,
    threshold_direction: str = "BELOW",
    current_value: float | None = None,
) -> FinanceLinkedKPIModel:
    if threshold_direction not in THRESHOLD_DIRECTIONS:
        raise FinancialESGError(f"Invalid threshold_direction: {threshold_direction}")
    instrument = session.get(SustainableFinanceInstrumentModel, instrument_id)
    if instrument is None or instrument.organization_id != organization_id:
        raise FinancialESGError("Finance instrument not found")
    now = _now()

    covenant = _evaluate_covenant(threshold_value, threshold_direction, current_value)

    rec = FinanceLinkedKPIModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        instrument_id=instrument_id,
        esg_target_id=esg_target_id,
        kpi_name=kpi_name,
        kpi_description=kpi_description,
        threshold_value=threshold_value,
        threshold_direction=threshold_direction,
        covenant_status=covenant,
        last_assessed_at=now,
        current_value=current_value,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.linked_kpi.created",
        actor_id=actor_id,
        resource_type="finance_linked_kpi",
        resource_id=rec.id,
        details={"instrument_id": instrument_id, "kpi_name": kpi_name, "covenant_status": covenant},
    )
    return rec


def _evaluate_covenant(
    threshold_value: float | None,
    threshold_direction: str,
    current_value: float | None,
) -> str:
    if threshold_value is None or current_value is None:
        return "MONITORING"
    if threshold_direction == "BELOW":
        return "COMPLIANT" if current_value <= threshold_value else "AT_RISK"
    else:  # ABOVE
        return "COMPLIANT" if current_value >= threshold_value else "AT_RISK"


def monitor_covenant(
    linked_kpi_id: str,
    current_value: float,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> FinanceLinkedKPIModel:
    rec = session.get(FinanceLinkedKPIModel, linked_kpi_id)
    _assert_org(rec, organization_id, "Finance linked KPI")
    rec.current_value = current_value
    rec.last_assessed_at = _now()
    new_status = _evaluate_covenant(rec.threshold_value, rec.threshold_direction, current_value)
    old_status = rec.covenant_status
    rec.covenant_status = new_status
    rec.updated_by = actor_id
    rec.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.covenant.monitored",
        actor_id=actor_id,
        resource_type="finance_linked_kpi",
        resource_id=linked_kpi_id,
        details={"current_value": current_value, "covenant_status": new_status, "previous_status": old_status},
    )
    return rec


# ── Transition Plans ──────────────────────────────────────────────────────────

def create_transition_plan(
    organization_id: str,
    name: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    baseline_state: dict | None = None,
    target_state: dict | None = None,
    financing_needs: float = 0.0,
    funding_sources: dict | None = None,
    start_date: datetime | None = None,
    target_date: datetime | None = None,
    currency: str = "USD",
) -> TransitionPlanModel:
    now = _now()
    plan = TransitionPlanModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        description=description,
        baseline_state=baseline_state or {},
        target_state=target_state or {},
        financing_needs=financing_needs,
        funding_sources=funding_sources or {},
        plan_status="DRAFT",
        start_date=start_date,
        target_date=target_date,
        currency=currency,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(plan)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.transition_plan.created",
        actor_id=actor_id,
        resource_type="transition_plan",
        resource_id=plan.id,
        details={"name": name, "financing_needs": financing_needs},
    )
    return plan


def add_transition_milestone(
    plan_id: str,
    organization_id: str,
    title: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    due_date: datetime | None = None,
) -> TransitionPlanMilestoneModel:
    plan = session.get(TransitionPlanModel, plan_id)
    _assert_org(plan, organization_id, "Transition plan")
    now = _now()
    ms = TransitionPlanMilestoneModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        plan_id=plan_id,
        title=title,
        description=description,
        due_date=due_date,
        milestone_status="PENDING",
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(ms)
    session.flush()
    return ms


def list_transition_plans(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[TransitionPlanModel]:
    return (
        session.query(TransitionPlanModel)
        .filter(TransitionPlanModel.organization_id == organization_id)
        .order_by(TransitionPlanModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
