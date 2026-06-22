"""Sustainability Reporting, Assurance, and Regulatory Mappings.

Reports are immutable once finalized (is_final=True).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.sustainability.metrics import sustainability_counters
from infrastructure.persistence.models.sustainability import (
    ASSURANCE_LEVELS,
    ASSURANCE_REPORT_TYPES,
    ASSURANCE_STATUSES,
    CSRD_ESRS_STANDARDS,
    ISSB_STANDARDS,
    MAPPING_COMPLIANCE_STATUSES,
    REPORT_RAG_STATUSES,
    REPORT_TYPES,
    CSRDPerformanceMappingModel,
    ESGKPIModel,
    SustainabilityObjectiveModel,
    ESGTargetModel,
    ISSBSustainabilityMappingModel,
    SustainabilityAssuranceRecordModel,
    SustainabilityPerformanceReportModel,
    CarbonInventoryModel,
)
from .objective_service import SustainabilityConflict, SustainabilityError, _assert_org, _now


def _rag_status(objectives_complete_pct: float, kpi_attainment_pct: float) -> str:
    avg = (objectives_complete_pct + kpi_attainment_pct) / 2
    if avg >= 80:
        return "GREEN"
    if avg >= 50:
        return "AMBER"
    return "RED"


def generate_report(
    organization_id: str,
    title: str,
    period_start: datetime,
    period_end: datetime,
    report_type: str,
    actor_id: str,
    session: Session,
) -> SustainabilityPerformanceReportModel:
    if report_type not in REPORT_TYPES:
        raise SustainabilityError(f"Invalid report_type: {report_type}")

    # KPI summary
    kpis = (
        session.query(ESGKPIModel)
        .filter(ESGKPIModel.organization_id == organization_id, ESGKPIModel.is_active == True)  # noqa: E712
        .count()
    )
    kpi_summary = {"total_active_kpis": kpis}

    # Emissions summary from most recent finalized inventory
    latest_inv = (
        session.query(CarbonInventoryModel)
        .filter(
            CarbonInventoryModel.organization_id == organization_id,
            CarbonInventoryModel.inventory_status == "FINALIZED",
        )
        .order_by(CarbonInventoryModel.reporting_year.desc())
        .first()
    )
    emissions_summary = (
        {
            "reporting_year": latest_inv.reporting_year,
            "total_emissions": latest_inv.total_emissions,
            "scope1": latest_inv.scope1_emissions,
            "scope2": latest_inv.scope2_emissions,
            "scope3": latest_inv.scope3_emissions,
            "unit": latest_inv.unit,
        }
        if latest_inv
        else {}
    )

    # Target progress
    targets_total = (
        session.query(ESGTargetModel)
        .filter(ESGTargetModel.organization_id == organization_id)
        .count()
    )
    targets_with_value = (
        session.query(ESGTargetModel)
        .filter(
            ESGTargetModel.organization_id == organization_id,
            ESGTargetModel.current_value.isnot(None),
        )
        .count()
    )
    target_progress = {
        "total_targets": targets_total,
        "targets_with_measurements": targets_with_value,
    }

    # Objective status
    objs = (
        session.query(SustainabilityObjectiveModel)
        .filter(SustainabilityObjectiveModel.organization_id == organization_id)
        .all()
    )
    status_counts: dict[str, int] = {}
    for o in objs:
        status_counts[o.objective_status] = status_counts.get(o.objective_status, 0) + 1
    total_objs = len(objs)
    completed = status_counts.get("COMPLETED", 0)
    objective_status = {
        "total": total_objs,
        "by_status": status_counts,
        "completion_rate_pct": round(completed / total_objs * 100, 1) if total_objs else 0.0,
    }

    # RAG status
    obj_complete_pct = objective_status["completion_rate_pct"]
    kpi_attainment_pct = 0.0  # simplified — full calculation in scorecard
    rag = _rag_status(obj_complete_pct, kpi_attainment_pct)

    now = _now()
    report = SustainabilityPerformanceReportModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        title=title,
        period_start=period_start,
        period_end=period_end,
        report_type=report_type,
        kpi_summary=kpi_summary,
        emissions_summary=emissions_summary,
        target_progress=target_progress,
        objective_status=objective_status,
        overall_status=rag,
        generated_by=actor_id,
        is_final=False,
        finalized_at=None,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(report)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.report.generated",
        actor_id=actor_id,
        resource_type="sustainability_performance_report",
        resource_id=report.id,
        details={"title": title, "overall_status": rag, "report_type": report_type},
    )
    sustainability_counters.record_report_generated()
    return report


def finalize_report(
    report_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> SustainabilityPerformanceReportModel:
    """Finalize report — immutable after this point."""
    report = session.get(SustainabilityPerformanceReportModel, report_id)
    _assert_org(report, organization_id, "Sustainability report")
    if report.is_final:
        raise SustainabilityConflict("Report is already finalized")
    report.is_final = True
    report.finalized_at = _now()
    report.updated_by = actor_id
    report.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.report.finalized",
        actor_id=actor_id,
        resource_type="sustainability_performance_report",
        resource_id=report_id,
        details={"finalized_at": report.finalized_at.isoformat()},
    )
    sustainability_counters.record_report_finalized()
    return report


def get_report(report_id: str, session: Session) -> SustainabilityPerformanceReportModel | None:
    return session.get(SustainabilityPerformanceReportModel, report_id)


def list_reports(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[SustainabilityPerformanceReportModel]:
    return (
        session.query(SustainabilityPerformanceReportModel)
        .filter(SustainabilityPerformanceReportModel.organization_id == organization_id)
        .order_by(SustainabilityPerformanceReportModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── Assurance ─────────────────────────────────────────────────────────────────

def create_assurance_record(
    organization_id: str,
    report_type: str,
    reviewed_period_start: datetime,
    reviewed_period_end: datetime,
    reviewer_user_id: str,
    assurance_level: str,
    actor_id: str,
    session: Session,
    *,
    findings: list | None = None,
    methodology: str | None = None,
) -> SustainabilityAssuranceRecordModel:
    if report_type not in ASSURANCE_REPORT_TYPES:
        raise SustainabilityError(f"Invalid report_type: {report_type}")
    if assurance_level not in ASSURANCE_LEVELS:
        raise SustainabilityError(f"Invalid assurance_level: {assurance_level}")
    now = _now()
    rec = SustainabilityAssuranceRecordModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        report_type=report_type,
        reviewed_period_start=reviewed_period_start,
        reviewed_period_end=reviewed_period_end,
        reviewer_user_id=reviewer_user_id,
        assurance_level=assurance_level,
        findings=findings or [],
        assurance_status="DRAFT",
        methodology=methodology,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.assurance.created",
        actor_id=actor_id,
        resource_type="sustainability_assurance_record",
        resource_id=rec.id,
        details={"report_type": report_type, "assurance_level": assurance_level},
    )
    return rec


def complete_assurance(
    record_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> SustainabilityAssuranceRecordModel:
    rec = session.get(SustainabilityAssuranceRecordModel, record_id)
    _assert_org(rec, organization_id, "Assurance record")
    rec.assurance_status = "COMPLETE"
    rec.updated_by = actor_id
    rec.updated_at = _now()
    session.flush()
    return rec


def list_assurance_records(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[SustainabilityAssuranceRecordModel]:
    return (
        session.query(SustainabilityAssuranceRecordModel)
        .filter(SustainabilityAssuranceRecordModel.organization_id == organization_id)
        .order_by(SustainabilityAssuranceRecordModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── CSRD Mappings ─────────────────────────────────────────────────────────────

def create_csrd_mapping(
    organization_id: str,
    esrs_standard: str,
    actor_id: str,
    session: Session,
    *,
    kpi_id: str | None = None,
    objective_id: str | None = None,
    target_id: str | None = None,
    disclosure_requirement: str | None = None,
    data_point_reference: str | None = None,
    compliance_status: str = "NOT_ASSESSED",
    notes: str | None = None,
) -> CSRDPerformanceMappingModel:
    if esrs_standard not in CSRD_ESRS_STANDARDS:
        raise SustainabilityError(f"Invalid ESRS standard: {esrs_standard}")
    if compliance_status not in MAPPING_COMPLIANCE_STATUSES:
        raise SustainabilityError(f"Invalid compliance_status: {compliance_status}")
    now = _now()
    m = CSRDPerformanceMappingModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        kpi_id=kpi_id,
        objective_id=objective_id,
        target_id=target_id,
        esrs_standard=esrs_standard,
        disclosure_requirement=disclosure_requirement,
        data_point_reference=data_point_reference,
        mapping_compliance_status=compliance_status,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(m)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.csrd_mapping.created",
        actor_id=actor_id,
        resource_type="csrd_performance_mapping",
        resource_id=m.id,
        details={"esrs_standard": esrs_standard, "compliance_status": compliance_status},
    )
    return m


def list_csrd_mappings(
    organization_id: str,
    session: Session,
    *,
    esrs_standard: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[CSRDPerformanceMappingModel]:
    q = session.query(CSRDPerformanceMappingModel).filter(
        CSRDPerformanceMappingModel.organization_id == organization_id
    )
    if esrs_standard:
        q = q.filter(CSRDPerformanceMappingModel.esrs_standard == esrs_standard)
    return q.order_by(CSRDPerformanceMappingModel.created_at.desc()).limit(limit).offset(offset).all()


# ── ISSB Mappings ─────────────────────────────────────────────────────────────

def create_issb_mapping(
    organization_id: str,
    issb_standard: str,
    actor_id: str,
    session: Session,
    *,
    kpi_id: str | None = None,
    objective_id: str | None = None,
    disclosure_topic: str | None = None,
    metric_reference: str | None = None,
    compliance_status: str = "NOT_ASSESSED",
    notes: str | None = None,
) -> ISSBSustainabilityMappingModel:
    if issb_standard not in ISSB_STANDARDS:
        raise SustainabilityError(f"Invalid ISSB standard: {issb_standard}. Valid: {ISSB_STANDARDS}")
    if compliance_status not in MAPPING_COMPLIANCE_STATUSES:
        raise SustainabilityError(f"Invalid compliance_status: {compliance_status}")
    now = _now()
    m = ISSBSustainabilityMappingModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        kpi_id=kpi_id,
        objective_id=objective_id,
        issb_standard=issb_standard,
        disclosure_topic=disclosure_topic,
        metric_reference=metric_reference,
        mapping_compliance_status=compliance_status,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(m)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.issb_mapping.created",
        actor_id=actor_id,
        resource_type="issb_sustainability_mapping",
        resource_id=m.id,
        details={"issb_standard": issb_standard, "compliance_status": compliance_status},
    )
    return m


def list_issb_mappings(
    organization_id: str,
    session: Session,
    *,
    issb_standard: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ISSBSustainabilityMappingModel]:
    q = session.query(ISSBSustainabilityMappingModel).filter(
        ISSBSustainabilityMappingModel.organization_id == organization_id
    )
    if issb_standard:
        q = q.filter(ISSBSustainabilityMappingModel.issb_standard == issb_standard)
    return q.order_by(ISSBSustainabilityMappingModel.created_at.desc()).limit(limit).offset(offset).all()
