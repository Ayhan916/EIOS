"""AI Incident Management — triage, resolution, and ESG escalation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.ai_governance import (
    INCIDENT_TYPES,
    RISK_LEVELS,
    HIGH_SEVERITY_LEVELS,
    AIIncidentModel,
    HumanReviewModel,
)

from .inventory_service import AIGovernanceError, AIGovernanceConflict, _assert_org_ownership


def _now() -> datetime:
    return datetime.now(timezone.utc)


def report_incident(
    model_id: str,
    organization_id: str,
    incident_type: str,
    severity: str,
    description: str,
    actor_id: str,
    session: Session,
    *,
    reported_by: str | None = None,
) -> AIIncidentModel:
    if incident_type not in INCIDENT_TYPES:
        raise AIGovernanceError(f"Invalid incident_type: {incident_type}")
    if severity not in RISK_LEVELS:
        raise AIGovernanceError(f"Invalid severity: {severity}")

    inc = AIIncidentModel(
        id=str(uuid.uuid4()),
        model_id=model_id,
        organization_id=organization_id,
        incident_type=incident_type,
        severity=severity,
        description=description,
        reported_by=reported_by or actor_id,
        is_resolved=False,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(inc)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.incident.reported",
        actor_id=actor_id,
        resource_type="ai_incident",
        resource_id=inc.id,
        details={
            "model_id": model_id,
            "incident_type": incident_type,
            "severity": severity,
        },
    )
    return inc


def resolve_incident(
    incident_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
    esg_action_id: str | None = None,
    strategic_risk_id: str | None = None,
) -> AIIncidentModel:
    inc = session.get(AIIncidentModel, incident_id)
    _assert_org_ownership(inc, organization_id, "Incident")

    # Idempotency guard — return 409 if already resolved
    if inc.is_resolved:
        raise AIGovernanceConflict(f"Incident {incident_id} is already resolved")

    # Severity gate: HIGH and CRITICAL incidents require a human review first
    if inc.severity in HIGH_SEVERITY_LEVELS:
        review = (
            session.query(HumanReviewModel)
            .filter(
                HumanReviewModel.incident_id == incident_id,
                HumanReviewModel.decision.in_(["APPROVED", "OVERRIDE"]),
            )
            .first()
        )
        if review is None:
            raise AIGovernanceError(
                f"{inc.severity} severity incidents require a human review record before resolution. "
                f"Submit a HumanReview with incident_id='{incident_id}' first."
            )

    inc.is_resolved = True
    inc.resolved_at = _now()
    inc.updated_by = actor_id
    if esg_action_id:
        inc.esg_action_id = esg_action_id
    if strategic_risk_id:
        inc.strategic_risk_id = strategic_risk_id

    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.incident.resolved",
        actor_id=actor_id,
        resource_type="ai_incident",
        resource_id=incident_id,
        details={"esg_action_id": esg_action_id, "strategic_risk_id": strategic_risk_id},
    )
    return inc


def list_incidents(
    organization_id: str,
    session: Session,
    *,
    unresolved_only: bool = False,
    model_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AIIncidentModel]:
    q = session.query(AIIncidentModel).filter(
        AIIncidentModel.organization_id == organization_id
    )
    if model_id:
        q = q.filter(AIIncidentModel.model_id == model_id)
    if unresolved_only:
        q = q.filter(AIIncidentModel.is_resolved == False)  # noqa: E712
    return q.order_by(AIIncidentModel.created_at.desc()).limit(limit).offset(offset).all()
