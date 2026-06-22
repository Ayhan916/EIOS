"""Climate Risk Assessments — integrates with M38 Network Intelligence and M31 Regulatory."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.sustainability.metrics import sustainability_counters
from infrastructure.persistence.models.sustainability import (
    CLIMATE_SCENARIOS,
    ClimateRiskAssessmentModel,
)

from .objective_service import SustainabilityError, _assert_org, _now


def _compute_overall_risk(transition: float, physical: float, regulatory: float) -> float:
    """Weighted average: 35% transition, 35% physical, 30% regulatory."""
    return round(transition * 0.35 + physical * 0.35 + regulatory * 0.30, 2)


def create_climate_risk_assessment(
    organization_id: str,
    title: str,
    assessment_year: int,
    transition_risk_score: float,
    physical_risk_score: float,
    regulatory_risk_score: float,
    actor_id: str,
    session: Session,
    *,
    scenario: str = "2C",
    transition_risk_details: dict | None = None,
    physical_risk_details: dict | None = None,
    regulatory_risk_details: dict | None = None,
    network_entity_id: str | None = None,
    regulation_id: str | None = None,
    notes: str | None = None,
) -> ClimateRiskAssessmentModel:
    if scenario not in CLIMATE_SCENARIOS:
        raise SustainabilityError(f"Invalid climate scenario: {scenario}")
    for name, val in [
        ("transition_risk_score", transition_risk_score),
        ("physical_risk_score", physical_risk_score),
        ("regulatory_risk_score", regulatory_risk_score),
    ]:
        if not (0.0 <= val <= 100.0):
            raise SustainabilityError(f"{name} must be between 0 and 100")
    overall = _compute_overall_risk(transition_risk_score, physical_risk_score, regulatory_risk_score)
    now = _now()
    cra = ClimateRiskAssessmentModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        title=title,
        assessment_year=assessment_year,
        scenario=scenario,
        transition_risk_score=transition_risk_score,
        physical_risk_score=physical_risk_score,
        regulatory_risk_score=regulatory_risk_score,
        overall_risk_score=overall,
        transition_risk_details=transition_risk_details or {},
        physical_risk_details=physical_risk_details or {},
        regulatory_risk_details=regulatory_risk_details or {},
        network_entity_id=network_entity_id,
        regulation_id=regulation_id,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(cra)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.climate_risk.assessed",
        actor_id=actor_id,
        resource_type="climate_risk_assessment",
        resource_id=cra.id,
        details={
            "overall_risk_score": overall,
            "scenario": scenario,
            "assessment_year": assessment_year,
        },
    )
    sustainability_counters.record_climate_risk_created()
    return cra


def get_climate_risk_assessment(
    assessment_id: str, session: Session
) -> ClimateRiskAssessmentModel | None:
    return session.get(ClimateRiskAssessmentModel, assessment_id)


def list_climate_risk_assessments(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[ClimateRiskAssessmentModel]:
    return (
        session.query(ClimateRiskAssessmentModel)
        .filter(ClimateRiskAssessmentModel.organization_id == organization_id)
        .order_by(ClimateRiskAssessmentModel.assessment_year.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
