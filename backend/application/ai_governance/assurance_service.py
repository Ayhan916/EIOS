"""AI Assurance Reporting — consolidated compliance snapshots for an organization."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.ai_governance import (
    ASSURANCE_STATUSES,
    AIAssuranceReportModel,
    AIControlModel,
    AIIncidentModel,
    AIModelModel,
    AIUseCaseModel,
    ModelApprovalWorkflowModel,
)

from .inventory_service import AIGovernanceError


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_dashboard_stats(organization_id: str, session: Session) -> dict:
    """Return all dashboard counts in as few queries as possible."""
    # Single query for all three AI model status counts
    model_row = session.query(
        func.count().label("total"),
        func.sum(case((AIModelModel.ai_status == "ACTIVE", 1), else_=0)).label("active"),
        func.sum(case((AIModelModel.ai_status == "DRAFT", 1), else_=0)).label("draft"),
    ).filter(AIModelModel.organization_id == organization_id).one()

    total_use_cases = (
        session.query(AIUseCaseModel)
        .filter(AIUseCaseModel.organization_id == organization_id)
        .count()
    )
    pending_approvals = (
        session.query(ModelApprovalWorkflowModel)
        .join(AIModelModel, AIModelModel.id == ModelApprovalWorkflowModel.model_id)
        .filter(
            AIModelModel.organization_id == organization_id,
            ModelApprovalWorkflowModel.stage_status == "PENDING",
        )
        .count()
    )
    open_incidents = (
        session.query(AIIncidentModel)
        .filter(
            AIIncidentModel.organization_id == organization_id,
            AIIncidentModel.is_resolved == False,  # noqa: E712
        )
        .count()
    )

    return {
        "total_models": model_row.total or 0,
        "active_models": int(model_row.active or 0),
        "draft_models": int(model_row.draft or 0),
        "total_use_cases": total_use_cases,
        "pending_approvals": pending_approvals,
        "open_incidents": open_incidents,
    }


def generate_assurance_report(
    organization_id: str,
    title: str,
    period_start: datetime,
    period_end: datetime,
    actor_id: str,
    session: Session,
) -> AIAssuranceReportModel:
    # All counts scoped to the report period (created_at within period)
    model_count = (
        session.query(AIModelModel)
        .filter(
            AIModelModel.organization_id == organization_id,
            AIModelModel.created_at >= period_start,
            AIModelModel.created_at <= period_end,
        )
        .count()
    )
    use_case_count = (
        session.query(AIUseCaseModel)
        .filter(
            AIUseCaseModel.organization_id == organization_id,
            AIUseCaseModel.created_at >= period_start,
            AIUseCaseModel.created_at <= period_end,
        )
        .count()
    )
    control_count = (
        session.query(AIControlModel)
        .filter(
            AIControlModel.organization_id == organization_id,
            AIControlModel.created_at >= period_start,
            AIControlModel.created_at <= period_end,
        )
        .count()
    )
    incident_count = (
        session.query(AIIncidentModel)
        .filter(
            AIIncidentModel.organization_id == organization_id,
            AIIncidentModel.created_at >= period_start,
            AIIncidentModel.created_at <= period_end,
        )
        .count()
    )
    # Active model count for the approval rate denominator (all-time active)
    active_model_count = (
        session.query(AIModelModel)
        .filter(
            AIModelModel.organization_id == organization_id,
            AIModelModel.ai_status == "ACTIVE",
        )
        .count()
    )
    approval_count = (
        session.query(ModelApprovalWorkflowModel)
        .join(AIModelModel, AIModelModel.id == ModelApprovalWorkflowModel.model_id)
        .filter(
            AIModelModel.organization_id == organization_id,
            ModelApprovalWorkflowModel.stage_status == "APPROVED",
        )
        .count()
    )

    overall_status = _compute_overall_status(incident_count, model_count)

    report = AIAssuranceReportModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        title=title,
        report_period_start=period_start,
        report_period_end=period_end,
        model_count=model_count,
        use_case_count=use_case_count,
        control_count=control_count,
        incident_count=incident_count,
        approval_count=approval_count,
        overall_status=overall_status,
        generated_by=actor_id,
        report_data={
            "organization_id": organization_id,
            "generated_at": _now().isoformat(),
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "counts": {
                "models_in_period": model_count,
                "use_cases_in_period": use_case_count,
                "controls_in_period": control_count,
                "incidents_in_period": incident_count,
                "active_models_all_time": active_model_count,
                "approvals": approval_count,
            },
        },
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(report)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.assurance_report.generated",
        actor_id=actor_id,
        resource_type="ai_assurance_report",
        resource_id=report.id,
        details={
            "title": title,
            "overall_status": overall_status,
            "incident_count": incident_count,
        },
    )
    return report


def _compute_overall_status(incident_count: int, model_count: int) -> str:
    if incident_count == 0:
        return "COMPLIANT"
    if model_count > 0 and incident_count / model_count < 0.1:
        return "PARTIALLY_COMPLIANT"
    return "NON_COMPLIANT"


def list_assurance_reports(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[AIAssuranceReportModel]:
    return (
        session.query(AIAssuranceReportModel)
        .filter(AIAssuranceReportModel.organization_id == organization_id)
        .order_by(AIAssuranceReportModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_assurance_report(
    report_id: str,
    session: Session,
) -> AIAssuranceReportModel | None:
    return session.get(AIAssuranceReportModel, report_id)
