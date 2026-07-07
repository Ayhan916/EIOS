"""M43 — Cost of Carbon Framework.

All calculations are deterministic and persisted with their formula.

Formula:
  total_carbon_cost = total_emissions × internal_carbon_price
  regulatory_exposure = total_emissions × regulatory_carbon_price
  net_avoided_cost = avoided_emissions × internal_carbon_price
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.kpi_service import (
    _now,
)
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import CarbonCostModelRecord


def _compute_carbon_cost(
    total_emissions: float,
    internal_carbon_price: float,
    regulatory_carbon_price: float,
    avoided_emissions: float,
) -> dict:
    total_carbon_cost = round(total_emissions * internal_carbon_price, 6)
    regulatory_exposure = round(total_emissions * regulatory_carbon_price, 6)
    avoided_cost = round(avoided_emissions * internal_carbon_price, 6)
    return {
        "total_carbon_cost": total_carbon_cost,
        "regulatory_exposure": regulatory_exposure,
        "avoided_cost": avoided_cost,
        "formula": {
            "total_carbon_cost": "total_emissions × internal_carbon_price",
            "regulatory_exposure": "total_emissions × regulatory_carbon_price",
            "avoided_cost": "avoided_emissions × internal_carbon_price",
        },
    }


def create_carbon_cost_model(
    organization_id: str,
    name: str,
    assessment_year: int,
    total_emissions: float,
    internal_carbon_price: float,
    regulatory_carbon_price: float,
    actor_id: str,
    session: Session,
    *,
    avoided_emissions: float = 0.0,
    currency: str = "USD",
    inventory_id: str | None = None,
    notes: str | None = None,
) -> CarbonCostModelRecord:
    computed = _compute_carbon_cost(
        total_emissions, internal_carbon_price, regulatory_carbon_price, avoided_emissions
    )
    now = _now()
    record = CarbonCostModelRecord(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        assessment_year=assessment_year,
        total_emissions=total_emissions,
        internal_carbon_price=internal_carbon_price,
        regulatory_carbon_price=regulatory_carbon_price,
        avoided_emissions=avoided_emissions,
        avoided_cost=computed["avoided_cost"],
        total_carbon_cost=computed["total_carbon_cost"],
        regulatory_exposure=computed["regulatory_exposure"],
        formula=computed["formula"],
        currency=currency,
        inventory_id=inventory_id,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.carbon_cost.created",
        actor_id=actor_id,
        resource_type="carbon_cost_model",
        resource_id=record.id,
        details={
            "assessment_year": assessment_year,
            "total_carbon_cost": computed["total_carbon_cost"],
            "regulatory_exposure": computed["regulatory_exposure"],
        },
    )
    financial_esg_counters.record_carbon_cost_model()
    return record


def list_carbon_cost_models(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[CarbonCostModelRecord]:
    return (
        session.query(CarbonCostModelRecord)
        .filter(CarbonCostModelRecord.organization_id == organization_id)
        .order_by(CarbonCostModelRecord.assessment_year.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
