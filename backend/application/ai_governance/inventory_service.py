"""AI Asset Inventory — model and use-case management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.ai_governance import (
    AI_MODEL_STATUSES,
    AI_MODEL_TYPES,
    RISK_LEVELS,
    TERMINAL_WORKFLOW_STATUSES,
    AIModelModel,
    AIUseCaseModel,
    ModelApprovalWorkflowModel,
    WORKFLOW_STAGES,
)


class AIGovernanceError(Exception):
    pass


class AIGovernanceConflict(AIGovernanceError):
    """Resource is in a conflicting state (e.g., already resolved, terminal FSM state)."""
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_org_ownership(record: Any, organization_id: str, label: str = "resource") -> None:
    """Raise AIGovernanceError if record does not belong to organization_id."""
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise AIGovernanceError(f"{label} not found")


# ── AI Model ──────────────────────────────────────────────────────────────────

def register_ai_model(
    organization_id: str,
    name: str,
    provider: str,
    model_type: str,
    actor_id: str,
    session: Session,
    *,
    model_version: str | None = None,
    purpose: str | None = None,
    owner_user_id: str | None = None,
    metadata_: dict[str, Any] | None = None,
) -> AIModelModel:
    if model_type not in AI_MODEL_TYPES:
        raise AIGovernanceError(f"Invalid model_type: {model_type}")

    model = AIModelModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        provider=provider,
        model_type=model_type,
        model_version=model_version,
        purpose=purpose,
        owner_user_id=owner_user_id,
        ai_status="DRAFT",
        metadata_=metadata_ or {},
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(model)
    session.flush()

    _create_approval_workflow(model.id, actor_id, session)

    emit_audit_event(
        session=session,
        event_type="ai.model.registered",
        actor_id=actor_id,
        resource_type="ai_model",
        resource_id=model.id,
        details={"name": name, "provider": provider, "model_type": model_type},
    )
    return model


def update_ai_model_status(
    model_id: str,
    new_status: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> AIModelModel:
    if new_status not in AI_MODEL_STATUSES:
        raise AIGovernanceError(f"Invalid ai_status: {new_status}")

    model = session.get(AIModelModel, model_id)
    _assert_org_ownership(model, organization_id, "AI model")

    if new_status == "ACTIVE":
        _assert_workflow_approved(model_id, session)

    old_status = model.ai_status
    model.ai_status = new_status
    model.updated_by = actor_id
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.model.status_changed",
        actor_id=actor_id,
        resource_type="ai_model",
        resource_id=model_id,
        details={"old_status": old_status, "new_status": new_status},
    )
    return model


def get_ai_model(model_id: str, session: Session) -> AIModelModel | None:
    return session.get(AIModelModel, model_id)


def list_ai_models(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[AIModelModel]:
    return (
        session.query(AIModelModel)
        .filter(AIModelModel.organization_id == organization_id)
        .order_by(AIModelModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── Use Case ──────────────────────────────────────────────────────────────────

def register_use_case(
    model_id: str,
    organization_id: str,
    title: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    business_owner: str | None = None,
    technical_owner: str | None = None,
    risk_level: str = "MEDIUM",
) -> AIUseCaseModel:
    if risk_level not in RISK_LEVELS:
        raise AIGovernanceError(f"Invalid risk_level: {risk_level}")

    model = session.get(AIModelModel, model_id)
    if not model:
        raise AIGovernanceError(f"AI model {model_id} not found")

    uc = AIUseCaseModel(
        id=str(uuid.uuid4()),
        model_id=model_id,
        organization_id=organization_id,
        title=title,
        description=description,
        business_owner=business_owner,
        technical_owner=technical_owner,
        risk_level=risk_level,
        approval_status="PENDING",
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(uc)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.use_case.registered",
        actor_id=actor_id,
        resource_type="ai_use_case",
        resource_id=uc.id,
        details={"model_id": model_id, "title": title, "risk_level": risk_level},
    )
    return uc


def approve_use_case(
    use_case_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> AIUseCaseModel:
    uc = session.get(AIUseCaseModel, use_case_id)
    _assert_org_ownership(uc, organization_id, "Use case")

    uc.approval_status = "APPROVED"
    uc.updated_by = actor_id
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.use_case.approved",
        actor_id=actor_id,
        resource_type="ai_use_case",
        resource_id=use_case_id,
        details={"model_id": uc.model_id},
    )
    return uc


def list_use_cases(
    model_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[AIUseCaseModel]:
    return (
        session.query(AIUseCaseModel)
        .filter(AIUseCaseModel.model_id == model_id)
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── Approval Workflow ─────────────────────────────────────────────────────────

_STAGE_ORDER = {s: i for i, s in enumerate(WORKFLOW_STAGES)}


def _create_approval_workflow(
    model_id: str,
    actor_id: str,
    session: Session,
) -> list[ModelApprovalWorkflowModel]:
    stages = []
    for stage in WORKFLOW_STAGES:
        s = ModelApprovalWorkflowModel(
            id=str(uuid.uuid4()),
            model_id=model_id,
            stage=stage,
            stage_status="PENDING",
            stage_order=_STAGE_ORDER[stage],
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(s)
        stages.append(s)
    session.flush()
    return stages


def advance_approval_stage(
    model_id: str,
    stage: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
    approved: bool = True,
    notes: str | None = None,
) -> ModelApprovalWorkflowModel:
    if stage not in WORKFLOW_STAGES:
        raise AIGovernanceError(f"Invalid stage: {stage}")

    # Verify model belongs to this organization
    model = session.get(AIModelModel, model_id)
    _assert_org_ownership(model, organization_id, "AI model")

    wf = (
        session.query(ModelApprovalWorkflowModel)
        .filter(
            ModelApprovalWorkflowModel.model_id == model_id,
            ModelApprovalWorkflowModel.stage == stage,
        )
        .first()
    )
    if not wf:
        raise AIGovernanceError(f"Workflow stage {stage} not found for model {model_id}")

    # FSM enforcement: terminal states cannot be re-transitioned
    if wf.stage_status in TERMINAL_WORKFLOW_STATUSES:
        raise AIGovernanceConflict(
            f"Workflow stage '{stage}' is already in terminal state '{wf.stage_status}'"
        )

    wf.stage_status = "APPROVED" if approved else "REJECTED"
    wf.approver_user_id = actor_id
    wf.notes = notes
    wf.completed_at = _now()
    wf.updated_by = actor_id
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.model.workflow_stage_completed",
        actor_id=actor_id,
        resource_type="ai_model",
        resource_id=model_id,
        details={"stage": stage, "approved": approved},
    )
    return wf


def _assert_workflow_approved(model_id: str, session: Session) -> None:
    required = {"review", "risk_assessment", "control_validation", "executive_approval"}
    approved = {
        w.stage
        for w in session.query(ModelApprovalWorkflowModel)
        .filter(
            ModelApprovalWorkflowModel.model_id == model_id,
            ModelApprovalWorkflowModel.stage_status == "APPROVED",
        )
        .all()
    }
    missing = required - approved
    if missing:
        raise AIGovernanceError(
            f"Cannot activate model — pending workflow stages: {sorted(missing)}"
        )


def get_workflow_stages(model_id: str, session: Session) -> list[ModelApprovalWorkflowModel]:
    return (
        session.query(ModelApprovalWorkflowModel)
        .filter(ModelApprovalWorkflowModel.model_id == model_id)
        .order_by(ModelApprovalWorkflowModel.stage_order)
        .all()
    )
