"""M39 ESG Playbook and Workflow Execution services.

Human approval is required at every checkpoint.
Agents may never advance, approve, or complete workflow executions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.operating_system.metrics import os_counters


async def _log_audit(
    session: AsyncSession,
    action: str,
    entity_id: str,
    entity_type: str,
    organization_id: str,
    detail: str = "",
) -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel

    evt = AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=None,
        outcome="success",
        detail=detail,
        event_metadata={"organization_id": organization_id},
    )
    session.add(evt)


# ── Playbooks ─────────────────────────────────────────────────────────────────


async def create_playbook(
    organization_id: str,
    title: str,
    playbook_type: str,
    session: AsyncSession,
    description: str = "",
    steps: list | None = None,
    escalation_rules: list | None = None,
    evidence_required: list | None = None,
) -> dict:
    from infrastructure.persistence.models.operating_system import ESGPlaybookModel

    now = datetime.now(UTC)
    pb = ESGPlaybookModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        title=title,
        description=description,
        playbook_type=playbook_type,
        steps=steps or [],
        escalation_rules=escalation_rules or [],
        evidence_required=evidence_required or [],
        playbook_status="ACTIVE",
    )
    session.add(pb)
    await session.flush()
    os_counters.record_playbook_created()
    await _log_audit(
        session,
        "playbook.created",
        pb.id,
        "ESGPlaybook",
        organization_id,
        detail=f"type={playbook_type}",
    )
    return _pb_to_dict(pb)


async def list_playbooks(
    organization_id: str, session: AsyncSession, playbook_type: str | None = None
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ESGPlaybookModel

    stmt = select(ESGPlaybookModel).where(
        ESGPlaybookModel.organization_id == organization_id,
        ESGPlaybookModel.playbook_status == "ACTIVE",
    )
    if playbook_type:
        stmt = stmt.where(ESGPlaybookModel.playbook_type == playbook_type)
    rows = (await session.execute(stmt)).scalars().all()
    return [_pb_to_dict(r) for r in rows]


async def get_playbook(
    organization_id: str, playbook_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGPlaybookModel

    stmt = select(ESGPlaybookModel).where(
        ESGPlaybookModel.organization_id == organization_id,
        ESGPlaybookModel.id == playbook_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _pb_to_dict(row) if row else None


# ── Workflow Executions ───────────────────────────────────────────────────────


async def start_workflow(
    organization_id: str,
    workflow_type: str,
    session: AsyncSession,
    playbook_id: str | None = None,
    initiated_by: str | None = None,
    linked_entity_type: str | None = None,
    linked_entity_id: str | None = None,
    total_steps: int = 0,
) -> dict:
    from infrastructure.persistence.models.operating_system import (
        ESGPlaybookModel,
        WorkflowExecutionModel,
    )

    # Infer total_steps from playbook if not provided
    if total_steps == 0 and playbook_id:
        pb_stmt = select(ESGPlaybookModel).where(
            ESGPlaybookModel.organization_id == organization_id,
            ESGPlaybookModel.id == playbook_id,
        )
        pb = (await session.execute(pb_stmt)).scalar_one_or_none()
        if pb:
            total_steps = len(pb.steps)

    now = datetime.now(UTC)
    wf = WorkflowExecutionModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        playbook_id=playbook_id,
        workflow_type=workflow_type,
        current_step=0,
        total_steps=total_steps,
        execution_status="IN_PROGRESS",
        steps_completed=[],
        pending_approvals=[],
        initiated_by=initiated_by,
        linked_entity_type=linked_entity_type,
        linked_entity_id=linked_entity_id,
    )
    session.add(wf)
    await session.flush()
    os_counters.record_workflow_started()
    await _log_audit(
        session,
        "playbook.executed",
        wf.id,
        "WorkflowExecution",
        organization_id,
        detail=f"type={workflow_type}",
    )
    return _wf_to_dict(wf)


async def approve_workflow_step(
    organization_id: str,
    execution_id: str,
    approved_by: str,
    session: AsyncSession,
    step_note: str = "",
) -> dict | None:
    """Human-only: advance workflow to next step after approval."""
    from infrastructure.persistence.models.operating_system import WorkflowExecutionModel

    stmt = select(WorkflowExecutionModel).where(
        WorkflowExecutionModel.organization_id == organization_id,
        WorkflowExecutionModel.id == execution_id,
    )
    wf = (await session.execute(stmt)).scalar_one_or_none()
    if wf is None:
        return None

    completed_step = {
        "step": wf.current_step,
        "approved_by": approved_by,
        "approved_at": datetime.now(UTC).isoformat(),
        "note": step_note,
    }
    wf.steps_completed = [*(wf.steps_completed or []), completed_step]
    wf.current_step = wf.current_step + 1

    if wf.current_step >= wf.total_steps:
        wf.execution_status = "COMPLETED"
    else:
        wf.execution_status = "IN_PROGRESS"

    wf.updated_at = datetime.now(UTC)
    await session.flush()
    await _log_audit(
        session,
        "workflow.approved",
        wf.id,
        "WorkflowExecution",
        organization_id,
        detail=f"step={completed_step['step']} by={approved_by}",
    )
    return _wf_to_dict(wf)


async def reject_workflow_step(
    organization_id: str,
    execution_id: str,
    rejected_by: str,
    session: AsyncSession,
    reason: str = "",
) -> dict | None:
    """Human-only: halt workflow execution with rejection."""
    from infrastructure.persistence.models.operating_system import WorkflowExecutionModel

    stmt = select(WorkflowExecutionModel).where(
        WorkflowExecutionModel.organization_id == organization_id,
        WorkflowExecutionModel.id == execution_id,
    )
    wf = (await session.execute(stmt)).scalar_one_or_none()
    if wf is None:
        return None
    wf.execution_status = "REJECTED"
    wf.updated_at = datetime.now(UTC)
    await session.flush()
    await _log_audit(
        session,
        "workflow.rejected",
        wf.id,
        "WorkflowExecution",
        organization_id,
        detail=f"by={rejected_by} reason={reason}",
    )
    return _wf_to_dict(wf)


async def list_workflow_executions(
    organization_id: str,
    session: AsyncSession,
    execution_status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import WorkflowExecutionModel

    stmt = select(WorkflowExecutionModel).where(
        WorkflowExecutionModel.organization_id == organization_id
    )
    if execution_status:
        stmt = stmt.where(WorkflowExecutionModel.execution_status == execution_status)
    stmt = stmt.order_by(WorkflowExecutionModel.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_wf_to_dict(r) for r in rows]


def _pb_to_dict(p) -> dict:
    return {
        "id": p.id,
        "organization_id": p.organization_id,
        "title": p.title,
        "description": p.description,
        "playbook_type": p.playbook_type,
        "steps": p.steps,
        "escalation_rules": p.escalation_rules,
        "evidence_required": p.evidence_required,
        "playbook_status": p.playbook_status,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _wf_to_dict(w) -> dict:
    return {
        "id": w.id,
        "organization_id": w.organization_id,
        "playbook_id": w.playbook_id,
        "workflow_type": w.workflow_type,
        "current_step": w.current_step,
        "total_steps": w.total_steps,
        "execution_status": w.execution_status,
        "steps_completed": w.steps_completed,
        "pending_approvals": w.pending_approvals,
        "initiated_by": w.initiated_by,
        "linked_entity_type": w.linked_entity_type,
        "linked_entity_id": w.linked_entity_id,
        "created_at": w.created_at,
        "updated_at": w.updated_at,
    }
