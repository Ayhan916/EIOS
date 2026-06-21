"""Prompt Registry — versioned prompt template management with human approval."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.ai_governance import (
    PromptChangeModel,
    PromptTemplateModel,
)

from .inventory_service import AIGovernanceError, _assert_org_ownership


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_prompt_template(
    organization_id: str,
    name: str,
    prompt_text: str,
    actor_id: str,
    session: Session,
    *,
    model_id: str | None = None,
    owner_user_id: str | None = None,
) -> PromptTemplateModel:
    pt = PromptTemplateModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        model_id=model_id,
        name=name,
        prompt_version=1,
        prompt_text=prompt_text,
        owner_user_id=owner_user_id or actor_id,
        is_approved=False,
        is_active=True,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(pt)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.prompt.created",
        actor_id=actor_id,
        resource_type="prompt_template",
        resource_id=pt.id,
        details={"name": name, "version": 1},
    )
    return pt


def approve_prompt_template(
    prompt_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> PromptTemplateModel:
    """Human must approve a prompt template before it can be used in production."""
    pt = session.get(PromptTemplateModel, prompt_id)
    _assert_org_ownership(pt, organization_id, "Prompt template")

    pt.is_approved = True
    pt.approved_by = actor_id
    pt.approved_at = _now()
    pt.updated_by = actor_id
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.prompt.approved",
        actor_id=actor_id,
        resource_type="prompt_template",
        resource_id=prompt_id,
        details={"version": pt.prompt_version},
    )
    return pt


def revise_prompt_template(
    prompt_id: str,
    new_text: str,
    change_rationale: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> tuple[PromptTemplateModel, PromptChangeModel]:
    """Create a new version — preserves previous text, resets approval."""
    pt = session.get(PromptTemplateModel, prompt_id)
    _assert_org_ownership(pt, organization_id, "Prompt template")

    old_version = pt.prompt_version
    new_version = old_version + 1
    old_text = pt.prompt_text  # capture before overwrite

    change = PromptChangeModel(
        id=str(uuid.uuid4()),
        prompt_id=prompt_id,
        previous_version=old_version,
        new_version=new_version,
        previous_prompt_text=old_text,
        new_prompt_text=new_text,
        change_rationale=change_rationale,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(change)

    pt.prompt_version = new_version
    pt.prompt_text = new_text
    pt.is_approved = False
    pt.approved_by = None
    pt.approved_at = None
    pt.updated_by = actor_id
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.prompt.revised",
        actor_id=actor_id,
        resource_type="prompt_template",
        resource_id=prompt_id,
        details={"old_version": old_version, "new_version": new_version},
    )
    return pt, change


def get_prompt_template(
    prompt_id: str,
    session: Session,
) -> PromptTemplateModel | None:
    return session.get(PromptTemplateModel, prompt_id)


def list_prompt_templates(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[PromptTemplateModel]:
    return (
        session.query(PromptTemplateModel)
        .filter(PromptTemplateModel.organization_id == organization_id)
        .order_by(PromptTemplateModel.name)
        .limit(limit)
        .offset(offset)
        .all()
    )


def list_prompt_changes(
    prompt_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[PromptChangeModel]:
    return (
        session.query(PromptChangeModel)
        .filter(PromptChangeModel.prompt_id == prompt_id)
        .order_by(PromptChangeModel.new_version.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
