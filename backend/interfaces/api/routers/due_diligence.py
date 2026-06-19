"""
M32.1 Supply Chain Due Diligence Reporting API

Routes:
  GET  /due-diligence/dashboard                  — KPI dashboard
  GET  /due-diligence/reports                    — list generated reports
  POST /due-diligence/reports/generate           — generate + store a report
  GET  /due-diligence/reports/{id}               — report detail
  GET  /due-diligence/reports/{id}/download      — download as PDF
  GET  /due-diligence/suppliers                  — supplier due diligence list
  GET  /due-diligence/suppliers/{id}             — supplier DD detail
  GET  /due-diligence/human-rights               — human rights report (live)
  GET  /due-diligence/environmental              — environmental report (live)
  GET  /due-diligence/remediation                — remediation report (live)
  GET  /due-diligence/preventive-measures        — preventive measures register (live)
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from io import BytesIO

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.due_diligence.csddd_engine import build_csddd_report
from application.due_diligence.environmental_engine import build_environmental_report
from application.due_diligence.human_rights_engine import build_human_rights_report
from application.due_diligence.lksgg_engine import build_lksgg_report
from application.due_diligence.preventive_measures_engine import build_preventive_measures_report
from application.due_diligence.remediation_engine import build_remediation_report
from domain.due_diligence_report import DueDiligenceReport
from domain.enums import DueDiligenceReportType, EntityStatus
from domain.user import User
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.control import ControlModel
from infrastructure.persistence.models.due_diligence import DueDiligenceReportModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.associations import control_risk
from infrastructure.persistence.repositories.due_diligence import SQLDueDiligenceReportRepository
from infrastructure.persistence.repositories.regulatory import SQLComplianceGapRepository
from infrastructure.persistence.repositories.supplier import SQLSupplierRepository
from infrastructure.persistence.repositories.supplier_score import SQLSupplierScoreRepository
from interfaces.api.deps import (
    get_current_user,
    get_db,
    require_analyst,
    require_executive,
    scope_gate,
)
from interfaces.api.schemas.due_diligence import (
    DueDiligenceKPIResponse,
    DueDiligenceReportDetail,
    DueDiligenceReportSummary,
    EnvironmentalReportResponse,
    EnvironmentalTopicSummary,
    GenerateDueDiligenceReportRequest,
    HumanRightsReportResponse,
    HumanRightsTopicSummary,
    PreventiveMeasureItem,
    PreventiveMeasuresCategoryResponse,
    PreventiveMeasuresReportResponse,
    RemediationReportResponse,
    SupplierDueDiligenceDetail,
    SupplierDueDiligenceSummary,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/due-diligence",
    tags=["Due Diligence Reporting"],
    dependencies=[Depends(scope_gate("due_diligence:read", "due_diligence:write"))],
)

_VALID_REPORT_TYPES = {t.value for t in DueDiligenceReportType}
_RESOLVED_STATUSES = frozenset({"resolved", "verified"})


# ── Data Gathering Helpers ────────────────────────────────────────────────────


async def _get_org_assessments(session: AsyncSession, org_id: str) -> list[AssessmentModel]:
    rows = (
        await session.execute(
            select(AssessmentModel).where(AssessmentModel.organization_id == org_id)
        )
    ).scalars().all()
    return list(rows)


async def _get_org_findings(session: AsyncSession, assessment_ids: set[str]) -> list[FindingModel]:
    if not assessment_ids:
        return []
    rows = (
        await session.execute(
            select(FindingModel).where(FindingModel.assessment_id.in_(assessment_ids))
        )
    ).scalars().all()
    return list(rows)


async def _get_org_risks(session: AsyncSession, assessment_ids: set[str]) -> list[RiskModel]:
    if not assessment_ids:
        return []
    rows = (
        await session.execute(
            select(RiskModel).where(RiskModel.assessment_id.in_(assessment_ids))
        )
    ).scalars().all()
    return list(rows)


async def _get_org_recommendations(
    session: AsyncSession, assessment_ids: set[str]
) -> list[RecommendationModel]:
    if not assessment_ids:
        return []
    rows = (
        await session.execute(
            select(RecommendationModel).where(
                RecommendationModel.assessment_id.in_(assessment_ids)
            )
        )
    ).scalars().all()
    return list(rows)


async def _get_org_controls(
    session: AsyncSession, risk_ids: set[str]
) -> list[ControlModel]:
    if not risk_ids:
        return []
    rows = (
        await session.execute(
            select(ControlModel)
            .join(control_risk, ControlModel.id == control_risk.c.control_id)
            .where(control_risk.c.risk_id.in_(risk_ids))
            .distinct()
        )
    ).scalars().all()
    return list(rows)


def _now() -> datetime:
    return datetime.now(UTC)


def _supplier_id_for_assessment(
    assessment: AssessmentModel,
) -> str | None:
    return assessment.supplier_id


def _rec_to_dict(
    rec: RecommendationModel,
    supplier_id_by_assessment: dict[str, str | None],
    now: datetime,
) -> dict:
    supplier_id = supplier_id_by_assessment.get(rec.assessment_id or "")
    is_overdue = (
        rec.due_date is not None
        and rec.due_date < now
        and rec.action_status not in _RESOLVED_STATUSES
    )
    resolution_days: int | None = None
    if rec.action_status in _RESOLVED_STATUSES and rec.created_at:
        delta = rec.updated_at - rec.created_at
        resolution_days = max(0, delta.days)
    return {
        "id": rec.id,
        "title": rec.title,
        "action_status": rec.action_status,
        "due_date": rec.due_date.isoformat() if rec.due_date else None,
        "priority": rec.priority,
        "supplier_id": supplier_id,
        "overdue": is_overdue,
        "resolution_days": resolution_days,
    }


def _finding_to_dict(
    finding: FindingModel,
    supplier_id_by_assessment: dict[str, str | None],
) -> dict:
    return {
        "id": finding.id,
        "title": finding.title,
        "severity": finding.severity,
        "category": finding.category,
        "description": finding.description or "",
        "supplier_id": supplier_id_by_assessment.get(finding.assessment_id or ""),
    }


def _risk_to_dict(
    risk: RiskModel,
    supplier_id_by_assessment: dict[str, str | None],
) -> dict:
    return {
        "id": risk.id,
        "title": risk.title,
        "risk_level": risk.risk_level,
        "severity": risk.risk_level,
        "category": risk.category,
        "supplier_id": supplier_id_by_assessment.get(risk.assessment_id or ""),
    }


def _control_to_dict(control: ControlModel) -> dict:
    return {
        "id": control.id,
        "title": control.title,
        "description": control.description or "",
        "control_type": control.control_type,
        "effectiveness": control.effectiveness,
        "status": "Active",
    }


async def _gather_org_data(
    session: AsyncSession,
    org_id: str,
) -> dict:
    """Pull all data needed by the DD engines in one pass."""
    supplier_repo = SQLSupplierRepository(session)
    score_repo = SQLSupplierScoreRepository(session)
    gap_repo = SQLComplianceGapRepository(session)

    suppliers = await supplier_repo.list_by_organization(org_id)
    scores = await score_repo.get_latest_for_org(org_id)
    scores_by_supplier = {s.supplier_id: s for s in scores}

    assessments = await _get_org_assessments(session, org_id)
    assessment_ids = {a.id for a in assessments}
    supplier_id_by_assessment = {a.id: a.supplier_id for a in assessments}

    findings = await _get_org_findings(session, assessment_ids)
    risks = await _get_org_risks(session, assessment_ids)
    recommendations = await _get_org_recommendations(session, assessment_ids)
    risk_ids = {r.id for r in risks}
    controls = await _get_org_controls(session, risk_ids)

    gaps = await gap_repo.list_for_org(org_id)

    now = _now()

    return {
        "suppliers": suppliers,
        "scores_by_supplier": scores_by_supplier,
        "supplier_id_by_assessment": supplier_id_by_assessment,
        "findings": findings,
        "risks": risks,
        "recommendations": recommendations,
        "controls": controls,
        "gaps": gaps,
        "now": now,
    }


def _to_engine_inputs(data: dict) -> dict:
    """Convert domain objects to plain dicts for engine inputs."""
    now = data["now"]
    supplier_id_by_assessment = data["supplier_id_by_assessment"]
    scores_by_supplier = data["scores_by_supplier"]

    suppliers_dicts = [
        {
            "id": s.id,
            "name": s.name,
            "tier": s.supplier_tier.value if hasattr(s.supplier_tier, "value") else str(s.supplier_tier),
            "country": s.country,
            "industry": s.industry,
            "status": s.supplier_status.value if hasattr(s.supplier_status, "value") else str(s.supplier_status),
        }
        for s in data["suppliers"]
    ]
    scores_dict = {
        sid: {
            "esg_score": sc.esg_score,
            "environmental_score": sc.environmental_score,
            "social_score": sc.social_score,
            "governance_score": sc.governance_score,
            "risk_score": sc.risk_score,
            "risk_band": sc.risk_band.value if hasattr(sc.risk_band, "value") else str(sc.risk_band),
            "trend": sc.trend.value if hasattr(sc.trend, "value") else str(sc.trend),
        }
        for sid, sc in scores_by_supplier.items()
    }
    findings_dicts = [_finding_to_dict(f, supplier_id_by_assessment) for f in data["findings"]]
    risks_dicts = [_risk_to_dict(r, supplier_id_by_assessment) for r in data["risks"]]
    recs_dicts = [_rec_to_dict(r, supplier_id_by_assessment, now) for r in data["recommendations"]]
    controls_dicts = [_control_to_dict(c) for c in data["controls"]]
    gaps_dicts = [
        {
            "id": g.id,
            "supplier_id": g.supplier_id,
            "severity": g.severity,
            "is_resolved": g.is_resolved,
            "gap_type": g.gap_type,
            "description": g.description,
        }
        for g in data["gaps"]
    ]
    evidence_items: list[dict] = []

    return {
        "suppliers": suppliers_dicts,
        "supplier_scores": scores_dict,
        "findings": findings_dicts,
        "risks": risks_dicts,
        "recommendations": recs_dicts,
        "controls": controls_dicts,
        "compliance_gaps": gaps_dicts,
        "evidence_items": evidence_items,
    }


# ── Schema helpers ────────────────────────────────────────────────────────────


def _rpt_to_summary(rpt: DueDiligenceReport) -> DueDiligenceReportSummary:
    return DueDiligenceReportSummary(
        id=rpt.id,
        organization_id=rpt.organization_id,
        report_type=rpt.report_type,
        framework=rpt.framework,
        framework_version=rpt.framework_version,
        generated_at=rpt.generated_at.isoformat(),
        generated_by=rpt.generated_by,
        report_hash=rpt.report_hash,
        status=rpt.status.value,
    )


def _rpt_to_detail(rpt: DueDiligenceReport) -> DueDiligenceReportDetail:
    return DueDiligenceReportDetail(
        id=rpt.id,
        organization_id=rpt.organization_id,
        report_type=rpt.report_type,
        framework=rpt.framework,
        framework_version=rpt.framework_version,
        generated_at=rpt.generated_at.isoformat(),
        generated_by=rpt.generated_by,
        report_hash=rpt.report_hash,
        report_data=rpt.report_data,
        status=rpt.status.value,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DueDiligenceKPIResponse)
async def due_diligence_dashboard(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DueDiligenceKPIResponse:
    org_id = current_user.organization_id
    data = await _gather_org_data(session, org_id)
    inputs = _to_engine_inputs(data)

    suppliers = inputs["suppliers"]
    scores = inputs["supplier_scores"]
    findings = inputs["findings"]
    risks = inputs["risks"]
    recs = inputs["recommendations"]
    gaps = inputs["compliance_gaps"]

    critical_suppliers = sum(
        1 for s in suppliers if (scores.get(s["id"]) or {}).get("risk_band") == "Critical"
    )
    high_risk_suppliers = sum(
        1 for s in suppliers if (scores.get(s["id"]) or {}).get("risk_band") in ("Critical", "High")
    )

    # HR and Env unresolved risks
    from application.due_diligence.human_rights_engine import _TOPIC_KEYWORDS as _HR_KWS
    from application.due_diligence.environmental_engine import _TOPIC_KEYWORDS as _ENV_KWS

    hr_finding_ids = {
        f["id"] for f in findings
        if any(
            any(kw in ((f.get("title") or "") + " " + (f.get("category") or "")).lower() for kw in kws)
            for kws in _HR_KWS.values()
        )
    }
    env_finding_ids = {
        f["id"] for f in findings
        if any(
            any(kw in ((f.get("title") or "") + " " + (f.get("category") or "")).lower() for kw in kws)
            for kws in _ENV_KWS.values()
        )
    }

    unresolved_hr = sum(
        1 for r in risks
        if r.get("risk_level") in ("Critical", "High")
        and any(
            any(kw in ((r.get("title") or "") + " " + (r.get("category") or "")).lower() for kw in kws)
            for kws in _HR_KWS.values()
        )
    )
    unresolved_env = sum(
        1 for r in risks
        if r.get("risk_level") in ("Critical", "High")
        and any(
            any(kw in ((r.get("title") or "") + " " + (r.get("category") or "")).lower() for kw in kws)
            for kws in _ENV_KWS.values()
        )
    )

    overdue_actions = sum(1 for r in recs if r.get("overdue", False))
    open_actions = sum(1 for r in recs if r.get("action_status") in ("open", "in_progress"))
    resolved = sum(1 for r in recs if r.get("action_status") in ("resolved", "verified"))
    total_recs = len(recs)
    remediation_pct = round(resolved / total_recs * 100, 1) if total_recs else 0.0

    avg_esg = (
        sum((scores.get(s["id"]) or {}).get("esg_score", 100.0) for s in suppliers) / len(suppliers)
        if suppliers else 100.0
    )
    avg_risk = (
        sum((scores.get(s["id"]) or {}).get("risk_score", 0.0) for s in suppliers) / len(suppliers)
        if suppliers else 0.0
    )

    rpt_repo = SQLDueDiligenceReportRepository(session)
    reports = await rpt_repo.list_for_org(org_id, limit=200)

    return DueDiligenceKPIResponse(
        organization_id=org_id,
        total_suppliers=len(suppliers),
        critical_suppliers=critical_suppliers,
        high_risk_suppliers=high_risk_suppliers,
        unresolved_hr_risks=unresolved_hr,
        unresolved_env_risks=unresolved_env,
        overdue_actions=overdue_actions,
        open_actions=open_actions,
        remediation_completion_pct=remediation_pct,
        avg_esg_score=round(avg_esg, 1),
        avg_risk_score=round(avg_risk, 1),
        reports_generated=len(reports),
    )


# ── Reports ───────────────────────────────────────────────────────────────────


@router.get("/reports", response_model=list[DueDiligenceReportSummary])
async def list_reports(
    report_type: str | None = Query(None),
    framework: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> list[DueDiligenceReportSummary]:
    rpt_repo = SQLDueDiligenceReportRepository(session)
    reports = await rpt_repo.list_for_org(
        organization_id=current_user.organization_id,
        report_type=report_type,
        framework=framework,
    )
    return [_rpt_to_summary(r) for r in reports]


@router.post("/reports/generate", response_model=DueDiligenceReportSummary, status_code=201)
async def generate_report(
    body: GenerateDueDiligenceReportRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_executive),
) -> DueDiligenceReportSummary:
    if body.report_type not in _VALID_REPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid report_type. Valid values: {sorted(_VALID_REPORT_TYPES)}",
        )

    org_id = current_user.organization_id
    data = await _gather_org_data(session, org_id)
    inputs = _to_engine_inputs(data)
    now = data["now"]

    _FRAMEWORK_MAP = {
        "lksgg_annual": ("LkSG", "2023"),
        "csddd": ("CSDDD", "2024/1760"),
        "human_rights": ("UN Guiding Principles", "2011"),
        "environmental": ("ESRS E1-E5 / TCFD", "2024"),
        "preventive_measures": ("ISO 37301", "2021"),
        "remediation": ("OECD Guidelines", "2023"),
    }
    framework, fw_version = _FRAMEWORK_MAP.get(body.report_type, ("", ""))

    if body.report_type == DueDiligenceReportType.LKSGG_ANNUAL.value:
        report_data = build_lksgg_report(
            organization_id=org_id,
            reporting_year=body.reporting_year or now.year,
            suppliers=inputs["suppliers"],
            supplier_scores=inputs["supplier_scores"],
            findings=inputs["findings"],
            risks=inputs["risks"],
            recommendations=inputs["recommendations"],
            compliance_gaps=inputs["compliance_gaps"],
            controls=inputs["controls"],
            evidence_items=inputs["evidence_items"],
        )
    elif body.report_type == DueDiligenceReportType.CSDDD.value:
        report_data = build_csddd_report(
            organization_id=org_id,
            suppliers=inputs["suppliers"],
            supplier_scores=inputs["supplier_scores"],
            findings=inputs["findings"],
            risks=inputs["risks"],
            recommendations=inputs["recommendations"],
            compliance_gaps=inputs["compliance_gaps"],
            evidence_items=inputs["evidence_items"],
        )
    elif body.report_type == DueDiligenceReportType.HUMAN_RIGHTS.value:
        report_data = build_human_rights_report(
            organization_id=org_id,
            findings=inputs["findings"],
            risks=inputs["risks"],
            recommendations=inputs["recommendations"],
            evidence_items=inputs["evidence_items"],
            controls=inputs["controls"],
        )
    elif body.report_type == DueDiligenceReportType.ENVIRONMENTAL.value:
        report_data = build_environmental_report(
            organization_id=org_id,
            findings=inputs["findings"],
            risks=inputs["risks"],
            recommendations=inputs["recommendations"],
            evidence_items=inputs["evidence_items"],
            controls=inputs["controls"],
        )
    elif body.report_type == DueDiligenceReportType.PREVENTIVE_MEASURES.value:
        report_data = build_preventive_measures_report(
            organization_id=org_id,
            controls=inputs["controls"],
        )
    elif body.report_type == DueDiligenceReportType.REMEDIATION.value:
        report_data = build_remediation_report(
            organization_id=org_id,
            recommendations=inputs["recommendations"],
        )
    else:
        raise HTTPException(status_code=422, detail="Unsupported report_type")

    # Add meta for PDF rendering
    report_data.setdefault("meta", {}).update({
        "report_type": body.report_type,
        "generated_at": now.isoformat(),
        "organization_id": org_id,
    })

    snapshot_bytes = json.dumps(report_data, sort_keys=True, default=str).encode()
    report_hash = hashlib.sha256(snapshot_bytes).hexdigest()

    rpt = DueDiligenceReport(
        organization_id=org_id,
        report_type=body.report_type,
        framework=framework,
        framework_version=fw_version,
        generated_at=now,
        generated_by=current_user.id,
        report_data=report_data,
        report_hash=report_hash,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )

    rpt_repo = SQLDueDiligenceReportRepository(session)
    await rpt_repo.save(rpt)

    logger.info(
        "due_diligence_report_generated",
        org_id=org_id,
        report_type=body.report_type,
        report_id=rpt.id,
        hash=report_hash[:12],
    )
    return _rpt_to_summary(rpt)


@router.get("/reports/{report_id}", response_model=DueDiligenceReportDetail)
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DueDiligenceReportDetail:
    rpt_repo = SQLDueDiligenceReportRepository(session)
    rpt = await rpt_repo.get_by_id(report_id)
    if rpt is None or rpt.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Due diligence report not found")
    return _rpt_to_detail(rpt)


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> StreamingResponse:
    rpt_repo = SQLDueDiligenceReportRepository(session)
    rpt = await rpt_repo.get_by_id(report_id)
    if rpt is None or rpt.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Due diligence report not found")

    from infrastructure.reporting.due_diligence_pdf_renderer import render_due_diligence_report  # noqa: PLC0415

    pdf_bytes = render_due_diligence_report(
        org_name=current_user.organization_id,
        report=rpt.report_data,
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="dd-report-{report_id[:8]}.pdf"',
            "X-Report-ID": rpt.id,
            "X-Report-Hash": rpt.report_hash,
            "X-Framework": rpt.framework,
        },
    )


# ── Supplier Due Diligence ─────────────────────────────────────────────────────


@router.get("/suppliers", response_model=list[SupplierDueDiligenceSummary])
async def list_supplier_due_diligence(
    risk_band: str | None = Query(None),
    tier: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> list[SupplierDueDiligenceSummary]:
    org_id = current_user.organization_id
    data = await _gather_org_data(session, org_id)
    inputs = _to_engine_inputs(data)

    suppliers = inputs["suppliers"]
    scores = inputs["supplier_scores"]
    findings = inputs["findings"]
    recs = inputs["recommendations"]

    from application.due_diligence.human_rights_engine import _TOPIC_KEYWORDS as _HR_KWS
    from application.due_diligence.environmental_engine import _TOPIC_KEYWORDS as _ENV_KWS

    def _count_topic_findings(supplier_id: str, topic_kws: dict) -> int:
        return sum(
            1 for f in findings
            if f.get("supplier_id") == supplier_id
            and any(
                any(kw in ((f.get("title") or "") + " " + (f.get("category") or "")).lower() for kw in kws)
                for kws in topic_kws.values()
            )
        )

    result = []
    for s in suppliers:
        sc = scores.get(s["id"]) or {}
        band = sc.get("risk_band", "Low")

        if risk_band and band != risk_band:
            continue
        if tier and s.get("tier") != tier:
            continue

        supplier_findings = [f for f in findings if f.get("supplier_id") == s["id"]]
        supplier_recs = [r for r in recs if r.get("supplier_id") == s["id"]]

        result.append(SupplierDueDiligenceSummary(
            supplier_id=s["id"],
            supplier_name=s["name"],
            country=s.get("country", ""),
            tier=s.get("tier", ""),
            risk_band=band,
            esg_score=sc.get("esg_score", 100.0),
            risk_score=sc.get("risk_score", 0.0),
            trend=sc.get("trend", "Stable"),
            critical_findings=sum(1 for f in supplier_findings if f.get("severity") == "Critical"),
            high_findings=sum(1 for f in supplier_findings if f.get("severity") == "High"),
            open_actions=sum(1 for r in supplier_recs if r.get("action_status") in ("open", "in_progress")),
            overdue_actions=sum(1 for r in supplier_recs if r.get("overdue", False)),
            hr_findings=_count_topic_findings(s["id"], _HR_KWS),
            env_findings=_count_topic_findings(s["id"], _ENV_KWS),
        ))

    result.sort(key=lambda x: -x.risk_score)
    return result


@router.get("/suppliers/{supplier_id}", response_model=SupplierDueDiligenceDetail)
async def get_supplier_due_diligence(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> SupplierDueDiligenceDetail:
    org_id = current_user.organization_id

    supplier_repo = SQLSupplierRepository(session)
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Supplier not found")

    score_repo = SQLSupplierScoreRepository(session)
    sc = await score_repo.get_latest_for_supplier(supplier_id)

    gap_repo = SQLComplianceGapRepository(session)
    gaps = await gap_repo.list_for_org(org_id, supplier_id=supplier_id)
    unresolved_gaps = sum(1 for g in gaps if not g.is_resolved)

    assessments = await _get_org_assessments(session, org_id)
    supplier_assessment_ids = {a.id for a in assessments if a.supplier_id == supplier_id}

    findings = await _get_org_findings(session, supplier_assessment_ids)
    risks = await _get_org_risks(session, supplier_assessment_ids)
    recs = await _get_org_recommendations(session, supplier_assessment_ids)

    now = _now()
    supplier_id_by_assessment: dict[str, str | None] = {a.id: a.supplier_id for a in assessments}

    findings_dicts = [_finding_to_dict(f, supplier_id_by_assessment) for f in findings]
    risks_dicts = [_risk_to_dict(r, supplier_id_by_assessment) for r in risks]
    recs_dicts = [_rec_to_dict(r, supplier_id_by_assessment, now) for r in recs]

    from application.due_diligence.human_rights_engine import _TOPIC_KEYWORDS as _HR_KWS
    from application.due_diligence.environmental_engine import _TOPIC_KEYWORDS as _ENV_KWS

    def _count_by_kws(dicts: list[dict], kws_map: dict) -> int:
        return sum(
            1 for f in dicts
            if any(
                any(kw in ((f.get("title") or "") + " " + (f.get("category") or "")).lower() for kw in kws)
                for kws in kws_map.values()
            )
        )

    band = sc.risk_band.value if sc else "Low"
    lksgg_coverage = (
        "High" if unresolved_gaps == 0 and band in ("Low", "Moderate") else
        "Partial" if unresolved_gaps <= 2 else "Low"
    )
    csddd_coverage = (
        "Compliant" if band in ("Low", "Moderate") else
        "Partially Compliant" if band == "High" else "Non-Compliant"
    )

    explainability = [
        {
            "factor": "risk_band",
            "value": band,
            "detail": f"Risk band derived from ESG and finding analysis",
        },
        {
            "factor": "unresolved_gaps",
            "value": unresolved_gaps,
            "detail": f"{unresolved_gaps} unresolved compliance gaps require remediation",
        },
        {
            "factor": "open_actions",
            "value": sum(1 for r in recs_dicts if r.get("action_status") in ("open", "in_progress")),
            "detail": "Open remediation actions pending resolution",
        },
    ]

    return SupplierDueDiligenceDetail(
        supplier_id=supplier_id,
        supplier_name=supplier.name,
        country=supplier.country,
        industry=supplier.industry,
        tier=supplier.supplier_tier.value if hasattr(supplier.supplier_tier, "value") else str(supplier.supplier_tier),
        risk_band=band,
        esg_score=sc.esg_score if sc else 100.0,
        environmental_score=sc.environmental_score if sc else 100.0,
        social_score=sc.social_score if sc else 100.0,
        governance_score=sc.governance_score if sc else 100.0,
        risk_score=sc.risk_score if sc else 0.0,
        trend=sc.trend.value if sc else "Stable",
        critical_findings=sum(1 for f in findings_dicts if f.get("severity") == "Critical"),
        high_findings=sum(1 for f in findings_dicts if f.get("severity") == "High"),
        open_actions=sum(1 for r in recs_dicts if r.get("action_status") in ("open", "in_progress")),
        overdue_actions=sum(1 for r in recs_dicts if r.get("overdue", False)),
        hr_findings=_count_by_kws(findings_dicts, _HR_KWS),
        env_findings=_count_by_kws(findings_dicts, _ENV_KWS),
        unresolved_gaps=unresolved_gaps,
        lksgg_coverage=lksgg_coverage,
        csddd_coverage=csddd_coverage,
        explainability=explainability,
    )


# ── Human Rights ──────────────────────────────────────────────────────────────


@router.get("/human-rights", response_model=HumanRightsReportResponse)
async def human_rights_report(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> HumanRightsReportResponse:
    org_id = current_user.organization_id
    data = await _gather_org_data(session, org_id)
    inputs = _to_engine_inputs(data)

    result = build_human_rights_report(
        organization_id=org_id,
        findings=inputs["findings"],
        risks=inputs["risks"],
        recommendations=inputs["recommendations"],
        evidence_items=inputs["evidence_items"],
        controls=inputs["controls"],
    )

    summary = result["summary"]
    by_topic = [
        HumanRightsTopicSummary(
            topic=t["topic"],
            display_name=t["display_name"],
            finding_count=t["finding_count"],
            critical_findings=t["critical_findings"],
            high_findings=t["high_findings"],
            risk_count=t["risk_count"],
            suppliers_impacted=t["suppliers_impacted"],
        )
        for t in result["by_topic"]
    ]

    return HumanRightsReportResponse(
        organization_id=org_id,
        total_hr_findings=summary.get("total_hr_findings", 0),
        total_hr_risks=summary.get("total_hr_risks", 0),
        suppliers_impacted=summary.get("suppliers_impacted", 0),
        open_remediation_actions=summary.get("open_remediation_actions", 0),
        overdue_actions=summary.get("overdue_actions", 0),
        resolved_actions=summary.get("resolved_actions", 0),
        by_topic=by_topic,
    )


# ── Environmental ─────────────────────────────────────────────────────────────


@router.get("/environmental", response_model=EnvironmentalReportResponse)
async def environmental_report(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> EnvironmentalReportResponse:
    org_id = current_user.organization_id
    data = await _gather_org_data(session, org_id)
    inputs = _to_engine_inputs(data)

    result = build_environmental_report(
        organization_id=org_id,
        findings=inputs["findings"],
        risks=inputs["risks"],
        recommendations=inputs["recommendations"],
        evidence_items=inputs["evidence_items"],
        controls=inputs["controls"],
    )

    summary = result["summary"]
    by_topic = [
        EnvironmentalTopicSummary(
            topic=t["topic"],
            display_name=t["display_name"],
            finding_count=t["finding_count"],
            critical_findings=t["critical_findings"],
            risk_count=t["risk_count"],
            unresolved_risks=t["unresolved_risks"],
            suppliers_impacted=t["suppliers_impacted"],
        )
        for t in result["by_topic"]
    ]

    return EnvironmentalReportResponse(
        organization_id=org_id,
        total_env_findings=summary.get("total_env_findings", 0),
        total_env_risks=summary.get("total_env_risks", 0),
        unresolved_risks=summary.get("unresolved_risks", 0),
        suppliers_impacted=summary.get("suppliers_impacted", 0),
        mitigation_controls=summary.get("mitigation_controls", 0),
        effective_controls=summary.get("effective_controls", 0),
        by_topic=by_topic,
    )


# ── Remediation ───────────────────────────────────────────────────────────────


@router.get("/remediation", response_model=RemediationReportResponse)
async def remediation_report(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> RemediationReportResponse:
    org_id = current_user.organization_id
    data = await _gather_org_data(session, org_id)
    inputs = _to_engine_inputs(data)

    result = build_remediation_report(
        organization_id=org_id,
        recommendations=inputs["recommendations"],
    )

    s = result["summary"]
    return RemediationReportResponse(
        organization_id=org_id,
        total=s.get("total", 0),
        open=s.get("open", 0),
        in_progress=s.get("in_progress", 0),
        completed=s.get("completed", 0),
        overdue=s.get("overdue", 0),
        closure_rate=s.get("closure_rate", 0.0),
        avg_resolution_days=s.get("avg_resolution_days"),
        by_priority=result.get("by_priority", {}),
        top_overdue=result.get("top_overdue", []),
    )


# ── Preventive Measures ────────────────────────────────────────────────────────


@router.get("/preventive-measures", response_model=PreventiveMeasuresReportResponse)
async def preventive_measures_report(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> PreventiveMeasuresReportResponse:
    org_id = current_user.organization_id
    data = await _gather_org_data(session, org_id)
    inputs = _to_engine_inputs(data)

    result = build_preventive_measures_report(
        organization_id=org_id,
        controls=inputs["controls"],
    )

    s = result["summary"]
    by_cat = [
        PreventiveMeasuresCategoryResponse(
            category=cat["category"],
            display_name=cat["display_name"],
            total=cat["total"],
            by_effectiveness=cat["by_effectiveness"],
            items=[
                PreventiveMeasureItem(
                    id=item["id"],
                    title=item["title"],
                    control_type=item["control_type"],
                    effectiveness_score=item["effectiveness_score"],
                    effectiveness_status=item["effectiveness_status"],
                )
                for item in cat.get("items", [])
            ],
        )
        for cat in result.get("by_category", [])
    ]

    return PreventiveMeasuresReportResponse(
        organization_id=org_id,
        total_controls=s.get("total_controls", 0),
        preventive=s.get("preventive", 0),
        detective=s.get("detective", 0),
        corrective=s.get("corrective", 0),
        by_effectiveness=s.get("by_effectiveness", {}),
        by_category=by_cat,
    )
