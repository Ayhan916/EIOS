"""AI Decision Logging & Explainability — caller-provided SHA-256 hashes stored as-is."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.ai_governance import (
    HUMAN_REVIEW_DECISIONS,
    AIDecisionLogModel,
    AIExplanationModel,
    HumanReviewModel,
    PromptTemplateModel,
)

from .inventory_service import AIGovernanceError


def _now() -> datetime:
    return datetime.now(UTC)


def log_ai_decision(
    model_id: str,
    organization_id: str,
    inputs_hash: str,
    output_hash: str,
    actor_id: str,
    session: Session,
    *,
    prompt_id: str | None = None,
    use_case_id: str | None = None,
    user_id: str | None = None,
    decision_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AIDecisionLogModel:
    """Store pre-hashed decision record.

    inputs_hash and output_hash must be SHA-256 hex strings (64 chars).
    They are stored exactly as provided — no re-hashing occurs here.
    If prompt_id is given, the prompt must exist, belong to this organization, and be approved.
    """
    if prompt_id is not None:
        pt = session.get(PromptTemplateModel, prompt_id)
        if pt is None or pt.organization_id != organization_id:
            raise AIGovernanceError(
                "prompt_id must reference a prompt template in this organization"
            )
        if not pt.is_approved:
            raise AIGovernanceError(
                f"Prompt template {prompt_id} is not approved for production use"
            )

    log = AIDecisionLogModel(
        id=str(uuid.uuid4()),
        model_id=model_id,
        prompt_id=prompt_id,
        use_case_id=use_case_id,
        organization_id=organization_id,
        user_id=user_id,
        inputs_hash=inputs_hash,
        output_hash=output_hash,
        decision_type=decision_type,
        decision_metadata=metadata or {},
        logged_at=_now(),
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(log)
    session.flush()
    return log


def add_explanation(
    decision_log_id: str,
    actor_id: str,
    session: Session,
    *,
    factors: list[dict] | None = None,
    confidence: float | None = None,
    rationale: str | None = None,
    source_references: list | None = None,
) -> AIExplanationModel:
    exp = AIExplanationModel(
        id=str(uuid.uuid4()),
        decision_log_id=decision_log_id,
        factors=factors or [],
        confidence=confidence,
        rationale=rationale,
        source_references=source_references or [],
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(exp)
    session.flush()
    return exp


def submit_human_review(
    model_id: str,
    reviewer_user_id: str,
    decision: str,
    session: Session,
    *,
    decision_log_id: str | None = None,
    incident_id: str | None = None,
    override_reason: str | None = None,
    rationale: str | None = None,
) -> HumanReviewModel:
    if decision not in HUMAN_REVIEW_DECISIONS:
        raise AIGovernanceError(f"Invalid review decision: {decision}")

    review = HumanReviewModel(
        id=str(uuid.uuid4()),
        decision_log_id=decision_log_id,
        incident_id=incident_id,
        model_id=model_id,
        reviewer_user_id=reviewer_user_id,
        decision=decision,
        override_reason=override_reason,
        rationale=rationale,
        reviewed_at=_now(),
        created_by=reviewer_user_id,
        updated_by=reviewer_user_id,
    )
    session.add(review)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.human_review.submitted",
        actor_id=reviewer_user_id,
        resource_type="human_review",
        resource_id=review.id,
        details={
            "model_id": model_id,
            "decision": decision,
            "decision_log_id": decision_log_id,
            "incident_id": incident_id,
        },
    )
    return review


def get_decision_log(log_id: str, session: Session) -> AIDecisionLogModel | None:
    return session.get(AIDecisionLogModel, log_id)


def list_decision_logs(
    model_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[AIDecisionLogModel]:
    return (
        session.query(AIDecisionLogModel)
        .filter(AIDecisionLogModel.model_id == model_id)
        .order_by(AIDecisionLogModel.logged_at.desc())
        .limit(min(limit, 500))
        .offset(offset)
        .all()
    )
