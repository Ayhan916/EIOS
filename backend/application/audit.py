"""Audit event factory helpers.

Keeps event construction consistent across the codebase.
Callers persist the returned AuditEvent via their injected repository.
"""

from __future__ import annotations

from domain.audit_event import AuditEvent
from domain.enums import EntityStatus


def workflow_completed(
    workflow_run_id: str,
    workflow_type: str,
    verdict: str | None,
    actor_id: str | None = None,
    assessment_id: str | None = None,
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
    actor_id: str | None = None,
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
    approved_by_email: str | None = None,
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
        detail=f"Assessment {assessment_id} returned for revision"
        + (f": {reason}" if reason else ""),
        status=EntityStatus.ACTIVE,
        event_metadata={"revised_by": revised_by_id, "reason": reason},
    )


def compliance_assessed(
    assessment_id: str,
    verdict_status: str,
    mandatory_coverage_ratio: float,
    mandatory_gap_count: int,
    critical_gap_count: int,
    actor_id: str | None = None,
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
    workflow_run_id: str | None = None,
    actor_id: str | None = None,
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


def user_registered(
    user_id: str,
    email: str,
    organization_id: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="user.registered",
        actor_id=user_id,
        actor_email=email,
        entity_type="User",
        entity_id=user_id,
        outcome="success",
        detail=f"New user registered: {email}",
        status=EntityStatus.ACTIVE,
        event_metadata={"organization_id": organization_id},
    )


def evidence_uploaded(
    evidence_id: str,
    actor_id: str,
    file_name: str,
    file_size_bytes: int,
    ingestion_status: str,
    chunks_created: int,
) -> AuditEvent:
    return AuditEvent(
        action="evidence.uploaded",
        actor_id=actor_id,
        entity_type="Evidence",
        entity_id=evidence_id,
        outcome="success",
        detail=f"Document '{file_name}' ingested: {chunks_created} chunks, status={ingestion_status}",  # noqa: E501
        status=EntityStatus.ACTIVE,
        event_metadata={
            "file_name": file_name,
            "file_size_bytes": file_size_bytes,
            "ingestion_status": ingestion_status,
            "chunks_created": chunks_created,
        },
    )


def report_generated(
    report_id: str,
    assessment_id: str,
    actor_id: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="report.generated",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Report",
        entity_id=report_id,
        outcome="success",
        detail=f"Executive report generated for assessment {assessment_id}",
        status=EntityStatus.ACTIVE,
        event_metadata={"assessment_id": assessment_id},
    )


def assessment_created_manually(
    assessment_id: str,
    actor_id: str,
    actor_email: str | None = None,
    assessment_type: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="assessment.created",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Assessment",
        entity_id=assessment_id,
        outcome="success",
        detail="Assessment created manually via API",
        status=EntityStatus.ACTIVE,
        event_metadata={"assessment_type": assessment_type},
    )
