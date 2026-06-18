from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

import application.audit as audit_factory
from application.reporting.service import ReportService
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLEvidenceRepository,
    SQLFindingEvidenceLinkRepository,
    SQLFindingRepository,
    SQLRecommendationRepository,
    SQLRiskRepository,
)
from infrastructure.persistence.repositories.report import SQLReportRepository
from interfaces.api.deps import (
    get_assessment_repo,
    get_audit_event_repo,
    get_current_user,
    get_evidence_repo,
    get_finding_evidence_link_repo,
    get_finding_repo,
    get_recommendation_repo,
    get_report_repo,
    get_risk_repo,
    require_analyst,
)
from interfaces.api.schemas.report import ReportGenerateRequest, ReportResponse

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


def _build_service(
    assessment_repo: SQLAssessmentRepository,
    finding_repo: SQLFindingRepository,
    risk_repo: SQLRiskRepository,
    recommendation_repo: SQLRecommendationRepository,
    evidence_repo: SQLEvidenceRepository,
    report_repo: SQLReportRepository,
    link_repo: SQLFindingEvidenceLinkRepository | None = None,
) -> ReportService:
    return ReportService(
        assessment_repo=assessment_repo,
        finding_repo=finding_repo,
        risk_repo=risk_repo,
        recommendation_repo=recommendation_repo,
        evidence_repo=evidence_repo,
        report_repo=report_repo,
        finding_evidence_link_repo=link_repo,
    )


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
    summary="Generate an executive PDF report for an assessment",
)
async def generate_report(
    body: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    risk_repo: SQLRiskRepository = Depends(get_risk_repo),
    recommendation_repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
    evidence_repo: SQLEvidenceRepository = Depends(get_evidence_repo),
    report_repo: SQLReportRepository = Depends(get_report_repo),
    link_repo: SQLFindingEvidenceLinkRepository = Depends(get_finding_evidence_link_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> ReportResponse:
    service = _build_service(
        assessment_repo,
        finding_repo,
        risk_repo,
        recommendation_repo,
        evidence_repo,
        report_repo,
        link_repo,
    )
    try:
        report = await service.generate(
            assessment_id=body.assessment_id,
            current_user=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await audit_repo.save(
        audit_factory.report_generated(
            report_id=report.id,
            assessment_id=body.assessment_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    )
    return ReportResponse.model_validate(report)


@router.get(
    "/",
    response_model=list[ReportResponse],
    summary="List reports for an assessment",
)
async def list_reports(
    assessment_id: str | None = Query(default=None),
    report_repo: SQLReportRepository = Depends(get_report_repo),
) -> list[ReportResponse]:
    if not assessment_id:
        return []
    results = await report_repo.list_by_assessment(assessment_id)
    return [ReportResponse.model_validate(r) for r in results]


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get report metadata",
)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    report_repo: SQLReportRepository = Depends(get_report_repo),
) -> ReportResponse:
    report = await report_repo.get_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.organization_id and report.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.get(
    "/{report_id}/download",
    summary="Download report as PDF",
    response_class=Response,
)
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    report_repo: SQLReportRepository = Depends(get_report_repo),
) -> Response:
    report = await report_repo.get_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.organization_id and report.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    pdf_bytes = await report_repo.get_pdf_data(report_id)
    if not pdf_bytes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not available")

    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in report.title)[:80]
    filename = f"{safe_title}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
