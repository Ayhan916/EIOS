"""AI Control management — create, test, and track governance controls."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.ai_governance import (
    CONTROL_TYPES,
    RISK_LEVELS,
    TEST_RESULTS,
    AIControlModel,
    AIControlTestModel,
    AIRiskAssessmentModel,
    AIRegulationMappingModel,
    AIRegulationMappingHistoryModel,
    REGULATION_FRAMEWORKS,
    COMPLIANCE_STATUSES,
)

from .inventory_service import AIGovernanceError, _assert_org_ownership


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Controls ─────────────────────────────────────────────────────────────────

def create_control(
    organization_id: str,
    name: str,
    control_type: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    examples: list | None = None,
    model_id: str | None = None,
) -> AIControlModel:
    if control_type not in CONTROL_TYPES:
        raise AIGovernanceError(f"Invalid control_type: {control_type}")

    ctrl = AIControlModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        control_type=control_type,
        description=description,
        examples=examples or [],
        model_id=model_id,
        is_active=True,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(ctrl)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.control.created",
        actor_id=actor_id,
        resource_type="ai_control",
        resource_id=ctrl.id,
        details={"name": name, "control_type": control_type},
    )
    return ctrl


def record_control_test(
    control_id: str,
    test_result: str,
    actor_id: str,
    session: Session,
    *,
    model_id: str | None = None,
    notes: str | None = None,
    tested_at: datetime | None = None,
) -> AIControlTestModel:
    if test_result not in TEST_RESULTS:
        raise AIGovernanceError(f"Invalid test_result: {test_result}")

    t = AIControlTestModel(
        id=str(uuid.uuid4()),
        control_id=control_id,
        model_id=model_id,
        test_result=test_result,
        tested_by=actor_id,
        notes=notes,
        tested_at=tested_at or _now(),
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(t)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.control.tested",
        actor_id=actor_id,
        resource_type="ai_control_test",
        resource_id=t.id,
        details={"control_id": control_id, "result": test_result},
    )
    return t


def list_controls(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[AIControlModel]:
    return (
        session.query(AIControlModel)
        .filter(AIControlModel.organization_id == organization_id)
        .limit(limit)
        .offset(offset)
        .all()
    )


def list_control_tests(
    control_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[AIControlTestModel]:
    return (
        session.query(AIControlTestModel)
        .filter(AIControlTestModel.control_id == control_id)
        .order_by(AIControlTestModel.tested_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── Risk Assessments ──────────────────────────────────────────────────────────

def create_risk_assessment(
    model_id: str,
    actor_id: str,
    session: Session,
    *,
    use_case_id: str | None = None,
    methodology: str | None = None,
    bias_risk: str | None = None,
    explainability_risk: str | None = None,
    privacy_risk: str | None = None,
    regulatory_risk: str | None = None,
    operational_risk: str | None = None,
    overall_score: float = 0.0,
    rationale: str | None = None,
) -> AIRiskAssessmentModel:
    for field_name, val in [
        ("bias_risk", bias_risk),
        ("explainability_risk", explainability_risk),
        ("privacy_risk", privacy_risk),
        ("regulatory_risk", regulatory_risk),
        ("operational_risk", operational_risk),
    ]:
        if val is not None and val not in RISK_LEVELS:
            raise AIGovernanceError(f"Invalid {field_name}: {val}")

    ra = AIRiskAssessmentModel(
        id=str(uuid.uuid4()),
        model_id=model_id,
        use_case_id=use_case_id,
        methodology=methodology,
        bias_risk=bias_risk,
        explainability_risk=explainability_risk,
        privacy_risk=privacy_risk,
        regulatory_risk=regulatory_risk,
        operational_risk=operational_risk,
        overall_score=overall_score,
        rationale=rationale,
        assessor_user_id=actor_id,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(ra)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.risk_assessment.created",
        actor_id=actor_id,
        resource_type="ai_risk_assessment",
        resource_id=ra.id,
        details={"model_id": model_id, "overall_score": overall_score},
    )
    return ra


# ── Regulation Mappings ───────────────────────────────────────────────────────

def create_regulation_mapping(
    framework: str,
    organization_id: str,
    actor_id: str,
    session: Session,
    *,
    use_case_id: str | None = None,
    risk_assessment_id: str | None = None,
    control_id: str | None = None,
    article_reference: str | None = None,
    requirement_text: str | None = None,
    compliance_status: str = "NOT_ASSESSED",
    notes: str | None = None,
) -> AIRegulationMappingModel:
    if framework not in REGULATION_FRAMEWORKS:
        raise AIGovernanceError(f"Invalid framework: {framework}")
    if compliance_status not in COMPLIANCE_STATUSES:
        raise AIGovernanceError(f"Invalid compliance_status: {compliance_status}")

    rm = AIRegulationMappingModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        use_case_id=use_case_id,
        risk_assessment_id=risk_assessment_id,
        control_id=control_id,
        framework=framework,
        article_reference=article_reference,
        requirement_text=requirement_text,
        compliance_status=compliance_status,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(rm)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.regulation_mapping.created",
        actor_id=actor_id,
        resource_type="ai_regulation_mapping",
        resource_id=rm.id,
        details={
            "framework": framework,
            "compliance_status": compliance_status,
            "organization_id": organization_id,
        },
    )
    return rm


def update_regulation_mapping_status(
    mapping_id: str,
    new_status: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> AIRegulationMappingModel:
    """Update compliance_status and create a history record."""
    if new_status not in COMPLIANCE_STATUSES:
        raise AIGovernanceError(f"Invalid compliance_status: {new_status}")

    rm = session.get(AIRegulationMappingModel, mapping_id)
    _assert_org_ownership(rm, organization_id, "Regulation mapping")

    old_status = rm.compliance_status

    history = AIRegulationMappingHistoryModel(
        id=str(uuid.uuid4()),
        mapping_id=mapping_id,
        previous_status=old_status,
        new_status=new_status,
        changed_by=actor_id,
        changed_at=_now(),
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(history)

    rm.compliance_status = new_status
    rm.updated_by = actor_id
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.regulation_mapping.status_changed",
        actor_id=actor_id,
        resource_type="ai_regulation_mapping",
        resource_id=mapping_id,
        details={"old_status": old_status, "new_status": new_status},
    )
    return rm


def list_regulation_mappings(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[AIRegulationMappingModel]:
    return (
        session.query(AIRegulationMappingModel)
        .filter(AIRegulationMappingModel.organization_id == organization_id)
        .order_by(AIRegulationMappingModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
