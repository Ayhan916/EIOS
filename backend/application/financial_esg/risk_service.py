"""M43 — Cost of Risk Engine.

Deterministic formulae:

  composite_risk_score = (
      supplier_risk × 0.30 +
      climate_risk  × 0.30 +
      compliance_risk × 0.20 +
      operational_risk × 0.20
  )  [0–100 output]

  estimated_financial_exposure = exposure_base × (composite_risk_score / 100)

  expected_loss = estimated_financial_exposure × (composite_risk_score / 100)

  risk_adjusted_exposure = estimated_financial_exposure × (1 + composite_risk_score / 100)
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.kpi_service import FinancialESGError, _now
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import CostOfRiskAssessmentModel

_WEIGHTS = {
    "supplier": 0.30,
    "climate": 0.30,
    "compliance": 0.20,
    "operational": 0.20,
}


def _compute_risk(
    supplier_risk: float,
    climate_risk: float,
    compliance_risk: float,
    operational_risk: float,
    exposure_base: float,
) -> dict:
    for score in (supplier_risk, climate_risk, compliance_risk, operational_risk):
        if not (0.0 <= score <= 100.0):
            raise FinancialESGError("Risk scores must be between 0 and 100")
    composite = round(
        supplier_risk * _WEIGHTS["supplier"]
        + climate_risk * _WEIGHTS["climate"]
        + compliance_risk * _WEIGHTS["compliance"]
        + operational_risk * _WEIGHTS["operational"],
        4,
    )
    exposure = round(exposure_base * (composite / 100.0), 6)
    expected_loss = round(exposure * (composite / 100.0), 6)
    risk_adjusted = round(exposure * (1 + composite / 100.0), 6)
    return {
        "composite_risk_score": composite,
        "estimated_financial_exposure": exposure,
        "expected_loss": expected_loss,
        "risk_adjusted_exposure": risk_adjusted,
        "methodology": {
            "composite_formula": "supplier×0.30 + climate×0.30 + compliance×0.20 + operational×0.20",
            "exposure_formula": "exposure_base × (composite / 100)",
            "expected_loss_formula": "estimated_exposure × (composite / 100)",
            "risk_adjusted_formula": "estimated_exposure × (1 + composite / 100)",
        },
    }


def create_cost_of_risk_assessment(
    organization_id: str,
    name: str,
    supplier_risk_score: float,
    climate_risk_score: float,
    compliance_risk_score: float,
    operational_risk_score: float,
    exposure_base: float,
    actor_id: str,
    session: Session,
    *,
    currency: str = "USD",
    notes: str | None = None,
) -> CostOfRiskAssessmentModel:
    computed = _compute_risk(
        supplier_risk_score,
        climate_risk_score,
        compliance_risk_score,
        operational_risk_score,
        exposure_base,
    )
    now = _now()
    record = CostOfRiskAssessmentModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        assessment_date=now,
        supplier_risk_score=supplier_risk_score,
        climate_risk_score=climate_risk_score,
        compliance_risk_score=compliance_risk_score,
        operational_risk_score=operational_risk_score,
        exposure_base=exposure_base,
        composite_risk_score=computed["composite_risk_score"],
        estimated_financial_exposure=computed["estimated_financial_exposure"],
        expected_loss=computed["expected_loss"],
        risk_adjusted_exposure=computed["risk_adjusted_exposure"],
        methodology=computed["methodology"],
        currency=currency,
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
        event_type="financial_esg.cost_of_risk.created",
        actor_id=actor_id,
        resource_type="cost_of_risk_assessment",
        resource_id=record.id,
        details={
            "composite_risk_score": computed["composite_risk_score"],
            "expected_loss": computed["expected_loss"],
        },
    )
    financial_esg_counters.record_cost_of_risk()
    return record


def list_risk_assessments(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[CostOfRiskAssessmentModel]:
    return (
        session.query(CostOfRiskAssessmentModel)
        .filter(CostOfRiskAssessmentModel.organization_id == organization_id)
        .order_by(CostOfRiskAssessmentModel.assessment_date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
