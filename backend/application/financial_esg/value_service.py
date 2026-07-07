"""M43 — ESG Value Creation Model and Climate Finance Analytics.

ROI formula:
  roi_percent = (realized_value - investment_amount) / investment_amount × 100
  (undefined when investment_amount == 0)

Cost per ton reduced:
  cost_per_ton_reduced = transition_investment / emissions_reduction
  (undefined when emissions_reduction == 0)

Climate finance ROI:
  roi_percent = (emissions_reduction × carbon_price_proxy - transition_investment)
                / transition_investment × 100
  Uses internal carbon price proxy of USD 50/tCO2e when not specified.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.kpi_service import (
    FinancialESGError,
    _assert_org,
    _now,
)
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import (
    INITIATIVE_STATUSES_FIN,
    ClimateFinanceAnalysisModel,
    SustainabilityValuationModelRecord,
    ValueCreationInitiativeModel,
)

_DEFAULT_CARBON_PRICE_PROXY = 50.0  # USD / tCO2e


def _compute_roi(realized: float, investment: float) -> float | None:
    if investment == 0:
        return None
    return round((realized - investment) / investment * 100, 4)


def create_value_creation_initiative(
    organization_id: str,
    name: str,
    investment_amount: float,
    expected_value: float,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    realized_value: float = 0.0,
    payback_period_months: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    currency: str = "USD",
    category: str | None = None,
) -> ValueCreationInitiativeModel:
    now = _now()
    roi = _compute_roi(realized_value, investment_amount)
    rec = ValueCreationInitiativeModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        description=description,
        investment_amount=investment_amount,
        expected_value=expected_value,
        realized_value=realized_value,
        roi_percent=roi,
        payback_period_months=payback_period_months,
        initiative_status="PLANNED",
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        category=category,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.value_initiative.created",
        actor_id=actor_id,
        resource_type="value_creation_initiative",
        resource_id=rec.id,
        details={"name": name, "investment_amount": investment_amount},
    )
    financial_esg_counters.record_value_initiative()
    return rec


def update_realized_value(
    initiative_id: str,
    realized_value: float,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
    new_status: str | None = None,
) -> ValueCreationInitiativeModel:
    rec = session.get(ValueCreationInitiativeModel, initiative_id)
    _assert_org(rec, organization_id, "Value creation initiative")
    if new_status and new_status not in INITIATIVE_STATUSES_FIN:
        raise FinancialESGError(f"Invalid status: {new_status}")
    rec.realized_value = realized_value
    rec.roi_percent = _compute_roi(realized_value, rec.investment_amount)
    if new_status:
        rec.initiative_status = new_status
    rec.updated_by = actor_id
    rec.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.value_initiative.updated",
        actor_id=actor_id,
        resource_type="value_creation_initiative",
        resource_id=initiative_id,
        details={"realized_value": realized_value, "roi_percent": rec.roi_percent},
    )
    return rec


def list_value_initiatives(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[ValueCreationInitiativeModel]:
    return (
        session.query(ValueCreationInitiativeModel)
        .filter(ValueCreationInitiativeModel.organization_id == organization_id)
        .order_by(ValueCreationInitiativeModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def create_climate_finance_analysis(
    organization_id: str,
    analysis_name: str,
    analysis_year: int,
    transition_investment: float,
    emissions_reduction: float,
    actor_id: str,
    session: Session,
    *,
    carbon_price_proxy: float = _DEFAULT_CARBON_PRICE_PROXY,
    currency: str = "USD",
    notes: str | None = None,
) -> ClimateFinanceAnalysisModel:
    cost_per_ton = (
        round(transition_investment / emissions_reduction, 6) if emissions_reduction > 0 else None
    )
    roi = None
    if transition_investment > 0 and emissions_reduction > 0:
        value_created = emissions_reduction * carbon_price_proxy
        roi = round((value_created - transition_investment) / transition_investment * 100, 4)
    now = _now()
    rec = ClimateFinanceAnalysisModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        analysis_name=analysis_name,
        analysis_year=analysis_year,
        transition_investment=transition_investment,
        emissions_reduction=emissions_reduction,
        cost_per_ton_reduced=cost_per_ton,
        roi_percent=roi,
        methodology={
            "cost_per_ton_formula": "transition_investment / emissions_reduction",
            "roi_formula": "(emissions_reduction × carbon_price_proxy - investment) / investment × 100",
            "carbon_price_proxy_usd": carbon_price_proxy,
        },
        currency=currency,
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
        event_type="financial_esg.climate_finance.created",
        actor_id=actor_id,
        resource_type="climate_finance_analysis",
        resource_id=rec.id,
        details={
            "analysis_year": analysis_year,
            "cost_per_ton_reduced": cost_per_ton,
            "roi_percent": roi,
        },
    )
    financial_esg_counters.record_climate_finance_analysis()
    return rec


def create_sustainability_valuation(
    organization_id: str,
    valuation_name: str,
    valuation_year: int,
    risk_reduction_value: float,
    carbon_reduction_value: float,
    operational_efficiency_value: float,
    actor_id: str,
    session: Session,
    *,
    currency: str = "USD",
    notes: str | None = None,
) -> SustainabilityValuationModelRecord:
    total = round(risk_reduction_value + carbon_reduction_value + operational_efficiency_value, 6)
    now = _now()
    rec = SustainabilityValuationModelRecord(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        valuation_name=valuation_name,
        valuation_year=valuation_year,
        risk_reduction_value=risk_reduction_value,
        carbon_reduction_value=carbon_reduction_value,
        operational_efficiency_value=operational_efficiency_value,
        total_sustainability_value=total,
        methodology={
            "formula": "risk_reduction_value + carbon_reduction_value + operational_efficiency_value",
        },
        currency=currency,
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
        event_type="financial_esg.valuation.created",
        actor_id=actor_id,
        resource_type="sustainability_valuation_model",
        resource_id=rec.id,
        details={"total_sustainability_value": total},
    )
    return rec


def list_climate_analyses(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[ClimateFinanceAnalysisModel]:
    return (
        session.query(ClimateFinanceAnalysisModel)
        .filter(ClimateFinanceAnalysisModel.organization_id == organization_id)
        .order_by(ClimateFinanceAnalysisModel.analysis_year.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def list_valuations(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[SustainabilityValuationModelRecord]:
    return (
        session.query(SustainabilityValuationModelRecord)
        .filter(SustainabilityValuationModelRecord.organization_id == organization_id)
        .order_by(SustainabilityValuationModelRecord.valuation_year.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
