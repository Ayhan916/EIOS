"""Audit event factory helpers.

Keeps event construction consistent across the codebase.
Callers persist the returned AuditEvent via their injected repository.
"""

from __future__ import annotations

from typing import Optional

from domain.audit_event import AuditEvent
from domain.enums import EntityStatus


def workflow_completed(
    workflow_run_id: str,
    workflow_type: str,
    verdict: Optional[str],
    actor_id: Optional[str] = None,
    assessment_id: Optional[str] = None,
) -> AuditEvent:
    return AuditEvent(
        action="workflow.completed",
        actor_id=actor_id,
        entity_type="WorkflowRun",
        entity_id=workflow_run_id,
        outcome="success",
        detail=f"Workflow '{workflow_type}' completed with verdict '{verdict}'",
        status=EntityStatus.ACTIVE,
        event_metadata={
            "workflow_type": workflow_type,
            "verdict": verdict,
            "assessment_id": assessment_id,
        },
    )


def assessment_created(
    assessment_id: str,
    workflow_run_id: str,
    finding_count: int,
    risk_count: int,
    recommendation_count: int,
    actor_id: Optional[str] = None,
) -> AuditEvent:
    return AuditEvent(
        action="assessment.created",
        actor_id=actor_id,
        entity_type="Assessment",
        entity_id=assessment_id,
        outcome="success",
        detail=(
            f"Structured assessment extracted from workflow {workflow_run_id}: "
            f"{finding_count} findings, {risk_count} risks, {recommendation_count} recommendations"
        ),
        status=EntityStatus.ACTIVE,
        event_metadata={
            "workflow_run_id": workflow_run_id,
            "finding_count": finding_count,
            "risk_count": risk_count,
            "recommendation_count": recommendation_count,
        },
    )


def user_authenticated(
    user_id: str,
    email: str,
    outcome: str = "success",
) -> AuditEvent:
    return AuditEvent(
        action="user.authenticated",
        actor_id=user_id,
        actor_email=email,
        entity_type="User",
        entity_id=user_id,
        outcome=outcome,
        status=EntityStatus.ACTIVE,
    )


def assessment_approved(
    assessment_id: str,
    approved_by_id: str,
    approved_by_email: Optional[str] = None,
) -> AuditEvent:
    return AuditEvent(
        action="assessment.approved",
        actor_id=approved_by_id,
        actor_email=approved_by_email,
        entity_type="Assessment",
        entity_id=assessment_id,
        outcome="success",
        detail=f"Assessment {assessment_id} approved",
        status=EntityStatus.ACTIVE,
        event_metadata={"approved_by": approved_by_id},
    )


def assessment_revised(
    assessment_id: str,
    revised_by_id: str,
    reason: str = "",
) -> AuditEvent:
    return AuditEvent(
        action="assessment.revised",
        actor_id=revised_by_id,
        entity_type="Assessment",
        entity_id=assessment_id,
        outcome="success",
        detail=f"Assessment {assessment_id} returned for revision" + (f": {reason}" if reason else ""),
        status=EntityStatus.ACTIVE,
        event_metadata={"revised_by": revised_by_id, "reason": reason},
    )


def compliance_assessed(
    assessment_id: str,
    verdict_status: str,
    mandatory_coverage_ratio: float,
    mandatory_gap_count: int,
    critical_gap_count: int,
    actor_id: Optional[str] = None,
) -> AuditEvent:
    return AuditEvent(
        action="compliance.assessed",
        actor_id=actor_id,
        entity_type="Assessment",
        entity_id=assessment_id,
        outcome="success",
        detail=(
            f"Compliance assessment: {verdict_status}, "
            f"{round(mandatory_coverage_ratio * 100)}% mandatory coverage, "
            f"{critical_gap_count} critical gap{'s' if critical_gap_count != 1 else ''}"
        ),
        status=EntityStatus.ACTIVE,
        event_metadata={
            "verdict_status": verdict_status,
            "mandatory_coverage_ratio": mandatory_coverage_ratio,
            "mandatory_gap_count": mandatory_gap_count,
            "critical_gap_count": critical_gap_count,
        },
    )


def agent_run_completed(
    agent_run_id: str,
    agent_type: str,
    workflow_run_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    outcome: str = "success",
) -> AuditEvent:
    return AuditEvent(
        action="agent.run.completed",
        actor_id=actor_id,
        entity_type="AgentRun",
        entity_id=agent_run_id,
        outcome=outcome,
        status=EntityStatus.ACTIVE,
        event_metadata={
            "agent_type": agent_type,
            "workflow_run_id": workflow_run_id,
        },
    )
