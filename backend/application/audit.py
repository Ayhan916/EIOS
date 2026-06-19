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


def recommendation_status_changed(
    recommendation_id: str,
    actor_id: str,
    old_status: str,
    new_status: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="recommendation.status_changed",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Recommendation",
        entity_id=recommendation_id,
        outcome="success",
        detail=f"Status changed: {old_status} → {new_status}",
        status=EntityStatus.ACTIVE,
        event_metadata={"old_status": old_status, "new_status": new_status},
    )


def recommendation_due_date_changed(
    recommendation_id: str,
    actor_id: str,
    new_due_date: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="recommendation.due_date_changed",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Recommendation",
        entity_id=recommendation_id,
        outcome="success",
        detail=f"Due date set to {new_due_date}",
        status=EntityStatus.ACTIVE,
        event_metadata={"new_due_date": new_due_date},
    )


def recommendation_assigned(
    recommendation_id: str,
    actor_id: str,
    assigned_to_id: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="recommendation.assigned",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Recommendation",
        entity_id=recommendation_id,
        outcome="success",
        detail=f"Assigned to user {assigned_to_id}",
        status=EntityStatus.ACTIVE,
        event_metadata={"assigned_to_id": assigned_to_id},
    )


def user_updated(
    target_user_id: str,
    actor_id: str,
    actor_email: str | None = None,
    changes: dict | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="user.updated",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="User",
        entity_id=target_user_id,
        outcome="success",
        detail=f"User {target_user_id} updated by admin",
        status=EntityStatus.ACTIVE,
        event_metadata={"changes": changes or {}},
    )


def user_invited(
    new_user_id: str,
    new_user_email: str,
    actor_id: str,
    actor_email: str | None = None,
    organization_id: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="user.invited",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="User",
        entity_id=new_user_id,
        outcome="success",
        detail=f"User {new_user_email} invited by admin",
        status=EntityStatus.ACTIVE,
        event_metadata={"organization_id": organization_id, "invited_email": new_user_email},
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


# ── M26 Collaboration & Review Workflow ───────────────────────────────────────


def review_submitted(
    assessment_id: str,
    actor_id: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="assessment.review_started",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Assessment",
        entity_id=assessment_id,
        outcome="success",
        detail=f"Assessment {assessment_id} submitted for review",
        status=EntityStatus.ACTIVE,
        event_metadata={"submitted_by": actor_id},
    )


def reviewer_assigned(
    assessment_id: str,
    reviewer_id: str,
    assigned_by_id: str,
    assigned_by_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="reviewer.assigned",
        actor_id=assigned_by_id,
        actor_email=assigned_by_email,
        entity_type="Assessment",
        entity_id=assessment_id,
        outcome="success",
        detail=f"Reviewer {reviewer_id} assigned to assessment {assessment_id}",
        status=EntityStatus.ACTIVE,
        event_metadata={"reviewer_id": reviewer_id, "assigned_by": assigned_by_id},
    )


def review_action_taken(
    assessment_id: str,
    action_type: str,
    actor_id: str,
    actor_email: str | None = None,
    comment: str | None = None,
) -> AuditEvent:
    action_map = {
        "approve": "assessment.approved",
        "reject": "assessment.rejected",
        "request_changes": "assessment.changes_requested",
    }
    return AuditEvent(
        action=action_map.get(action_type, f"assessment.{action_type}"),
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Assessment",
        entity_id=assessment_id,
        outcome="success",
        detail=f"Review action '{action_type}' taken on assessment {assessment_id}",
        status=EntityStatus.ACTIVE,
        event_metadata={"action_type": action_type, "comment": comment},
    )


def comment_created(
    comment_id: str,
    entity_type: str,
    entity_id: str,
    author_id: str,
    author_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="comment.created",
        actor_id=author_id,
        actor_email=author_email,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome="success",
        detail=f"Comment {comment_id} added to {entity_type} {entity_id}",
        status=EntityStatus.ACTIVE,
        event_metadata={"comment_id": comment_id},
    )


# ── M27 Supplier Management ───────────────────────────────────────────────────


def supplier_created(
    supplier_id: str,
    supplier_name: str,
    actor_id: str,
    actor_email: str | None = None,
    organization_id: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="supplier.created",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Supplier",
        entity_id=supplier_id,
        outcome="success",
        detail=f"Supplier '{supplier_name}' created",
        status=EntityStatus.ACTIVE,
        event_metadata={"organization_id": organization_id},
    )


def supplier_updated(
    supplier_id: str,
    supplier_name: str,
    actor_id: str,
    actor_email: str | None = None,
    changes: dict | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="supplier.updated",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Supplier",
        entity_id=supplier_id,
        outcome="success",
        detail=f"Supplier '{supplier_name}' updated",
        status=EntityStatus.ACTIVE,
        event_metadata={"changes": changes or {}},
    )


def supplier_archived(
    supplier_id: str,
    supplier_name: str,
    actor_id: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="supplier.archived",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Supplier",
        entity_id=supplier_id,
        outcome="success",
        detail=f"Supplier '{supplier_name}' archived",
        status=EntityStatus.ACTIVE,
        event_metadata={},
    )


def supplier_assessment_linked(
    supplier_id: str,
    assessment_id: str,
    actor_id: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="supplier.assessment_linked",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Supplier",
        entity_id=supplier_id,
        outcome="success",
        detail=f"Assessment {assessment_id} linked to supplier {supplier_id}",
        status=EntityStatus.ACTIVE,
        event_metadata={"assessment_id": assessment_id},
    )


def supplier_score_calculated(
    supplier_id: str,
    supplier_name: str,
    risk_score: float,
    risk_band: str,
    esg_score: float,
    actor_id: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="supplier.score_calculated",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="Supplier",
        entity_id=supplier_id,
        outcome="success",
        detail=(
            f"Score recalculated for '{supplier_name}': "
            f"Risk={risk_score} ({risk_band}), ESG={esg_score}"
        ),
        status=EntityStatus.ACTIVE,
        event_metadata={
            "risk_score": risk_score,
            "risk_band": risk_band,
            "esg_score": esg_score,
        },
    )


def make(
    action: str,
    actor_id: str,
    actor_email: str | None = None,
    entity_type: str = "",
    entity_id: str = "",
    detail: str = "",
    metadata: dict | None = None,
    outcome: str = "success",
) -> AuditEvent:
    """Generic audit event factory for ad-hoc actions."""
    return AuditEvent(
        action=action,
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome=outcome,
        detail=detail,
        status=EntityStatus.ACTIVE,
        event_metadata=metadata or {},
    )


def board_report_generated(
    report_id: str,
    actor_id: str,
    actor_email: str | None = None,
    organization_id: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="board_report.generated",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="BoardReport",
        entity_id=report_id,
        outcome="success",
        detail=f"Board report generated for period {period_start} – {period_end}",
        status=EntityStatus.ACTIVE,
        event_metadata={
            "organization_id": organization_id,
            "period_start": period_start,
            "period_end": period_end,
        },
    )


def board_report_downloaded(
    report_id: str,
    actor_id: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="board_report.downloaded",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type="BoardReport",
        entity_id=report_id,
        outcome="success",
        detail=f"Board report PDF downloaded",
        status=EntityStatus.ACTIVE,
        event_metadata={},
    )


def comment_deleted(
    comment_id: str,
    entity_type: str,
    entity_id: str,
    actor_id: str,
    actor_email: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        action="comment.deleted",
        actor_id=actor_id,
        actor_email=actor_email,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome="success",
        detail=f"Comment {comment_id} soft-deleted from {entity_type} {entity_id}",
        status=EntityStatus.ACTIVE,
        event_metadata={"comment_id": comment_id},
    )
