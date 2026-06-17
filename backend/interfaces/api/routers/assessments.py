from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

import application.audit as audit_events
from application.compliance.coverage import compute_coverage
from application.compliance.gaps import compute_gaps
from application.compliance.verdict import compute_verdict
from application.remediation.brief import compute_brief
from application.remediation.matcher import compute_matches
from application.remediation.planner import compute_remediation_plan
from domain.assessment import Assessment
from domain.enums import EntityStatus
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLFindingRepository,
    SQLRecommendationRepository,
    SQLRiskRepository,
    SQLWorkflowRunRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_audit_event_repo,
    get_current_user,
    get_finding_repo,
    get_recommendation_repo,
    get_risk_repo,
    get_workflow_run_repo,
    require_admin,
    require_analyst,
    require_reviewer,
)
from interfaces.api.schemas.assessment import AssessmentCreate, AssessmentResponse
from interfaces.api.schemas.finding import FindingResponse
from interfaces.api.schemas.pagination import Page, PaginationParams
from interfaces.api.schemas.remediation import (
    AssessmentTraceResponse,
    DecisionBriefResponse,
    RemediationActionResponse,
    RemediationPlanResponse,
)
from interfaces.api.schemas.risk import RiskResponse


class AssessmentReviseRequest(BaseModel):
    reason: str = ""


router = APIRouter(
    prefix="/assessments",
    tags=["assessments"],
    dependencies=[Depends(get_current_user)],
)


def _assert_org_access(item_org_id: str | None, user_org_id: str | None) -> None:
    """Raise 404 if item does not belong to user's organization (avoids info leakage)."""
    if item_org_id and user_org_id and item_org_id != user_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")


@router.post(
    "/",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_assessment(
    body: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> AssessmentResponse:
    assessment = Assessment(
        title=body.title,
        description=body.description,
        assessment_type=body.assessment_type,
        scope=body.scope,
        sector_id=body.sector_id,
        methodology=body.methodology,
        confidence=body.confidence,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    saved = await repo.save(assessment)
    return AssessmentResponse.model_validate(saved)


@router.get("/", response_model=Page[AssessmentResponse])
async def list_assessments(
    pagination: PaginationParams = Depends(),
    filter_status: str | None = Query(default=None, alias="status"),
    assessment_type: str | None = Query(default=None),
    sector_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> Page[AssessmentResponse]:
    if not current_user.organization_id:
        return Page(items=[], total=0, page=pagination.page, page_size=pagination.page_size)
    items, total = await repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=filter_status,
        assessment_type=assessment_type,
        sector_id=sector_id,
        search=search,
    )
    return Page(
        items=[AssessmentResponse.model_validate(a) for a in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> AssessmentResponse:
    assessment = await repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)
    return AssessmentResponse.model_validate(assessment)


@router.get("/{assessment_id}/findings", response_model=list[FindingResponse])
async def list_assessment_findings(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    repo: SQLFindingRepository = Depends(get_finding_repo),
) -> list[FindingResponse]:
    assessment = await assessment_repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)
    findings = await repo.list_by_assessment(assessment_id)
    return [FindingResponse.model_validate(f) for f in findings]


@router.get("/{assessment_id}/risks", response_model=list[RiskResponse])
async def list_assessment_risks(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    repo: SQLRiskRepository = Depends(get_risk_repo),
) -> list[RiskResponse]:
    assessment = await assessment_repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)
    risks = await repo.list_by_assessment(assessment_id)
    return [RiskResponse.model_validate(r) for r in risks]


@router.patch(
    "/{assessment_id}/approve",
    response_model=AssessmentResponse,
    dependencies=[Depends(require_reviewer)],
)
async def approve_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> AssessmentResponse:
    assessment = await repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)
    if assessment.status == EntityStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Assessment already approved"
        )

    assessment.status = EntityStatus.APPROVED
    assessment.approved_by = current_user.id
    assessment.approval_date = datetime.now(UTC)
    saved = await repo.save(assessment)

    event = audit_events.assessment_approved(
        assessment_id=assessment_id,
        approved_by_id=current_user.id,
        approved_by_email=current_user.email,
    )
    await audit_repo.save(event)

    return AssessmentResponse.model_validate(saved)


@router.patch(
    "/{assessment_id}/revise",
    response_model=AssessmentResponse,
    dependencies=[Depends(require_reviewer)],
)
async def revise_assessment(
    assessment_id: str,
    body: AssessmentReviseRequest,
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> AssessmentResponse:
    assessment = await repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)
    if assessment.status not in (EntityStatus.REVIEWED, EntityStatus.APPROVED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only reviewed or approved assessments can be sent for revision",
        )

    assessment.status = EntityStatus.DRAFT
    assessment.approved_by = None
    assessment.approval_date = None
    assessment.updated_by = current_user.id
    if body.reason:
        assessment.description = assessment.description + f"\n\n[Revision requested: {body.reason}]"

    saved = await repo.save(assessment)

    event = audit_events.assessment_revised(
        assessment_id=assessment_id,
        revised_by_id=current_user.id,
        reason=body.reason,
    )
    await audit_repo.save(event)

    return AssessmentResponse.model_validate(saved)


@router.get("/{assessment_id}/trace", response_model=AssessmentTraceResponse)
async def get_assessment_trace(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    risk_repo: SQLRiskRepository = Depends(get_risk_repo),
    rec_repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
    workflow_run_repo: SQLWorkflowRunRepository = Depends(get_workflow_run_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> AssessmentTraceResponse:
    assessment = await assessment_repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    findings = await finding_repo.list_by_assessment(assessment_id)
    risks = await risk_repo.list_by_assessment(assessment_id)
    recs = await rec_repo.list_by_assessment(assessment_id)
    workflow_runs = await workflow_run_repo.list_by_assessment_id(assessment_id)
    audit_events_list = await audit_repo.list_by_entity("Assessment", assessment_id)

    wf = workflow_runs[0] if workflow_runs else None

    texts = [
        assessment.description,
        assessment.methodology or "",
        *(f.description for f in findings),
        *(f.reasoning or "" for f in findings),
        *(r.description for r in risks),
        *(r.reasoning or "" for r in risks),
    ]
    coverage = compute_coverage(texts)
    gaps = compute_gaps(coverage)
    verdict = compute_verdict(coverage, gaps)

    return AssessmentTraceResponse(
        assessment_id=assessment_id,
        assessment_title=assessment.title,
        assessment_status=assessment.status.value,
        quality_score=assessment.quality_score,
        workflow_run_id=wf.id if wf else None,
        workflow_type=wf.workflow_type if wf else None,
        workflow_verdict=wf.verdict if wf else None,
        workflow_overall_risk_level=wf.overall_risk_level if wf else None,
        workflow_steps_completed=wf.steps_completed if wf else 0,
        workflow_total_steps=wf.total_steps if wf else 0,
        finding_count=len(findings),
        risk_count=len(risks),
        recommendation_count=len(recs),
        compliance_mandatory_coverage_ratio=verdict.mandatory_coverage_ratio,
        compliance_mandatory_coverage_pct=round(verdict.mandatory_coverage_ratio * 100),
        compliance_critical_gap_count=verdict.critical_gap_count,
        compliance_verdict_status=verdict.status,
        audit_event_count=len(audit_events_list),
    )


@router.get("/{assessment_id}/remediation", response_model=RemediationPlanResponse)
async def get_assessment_remediation(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    risk_repo: SQLRiskRepository = Depends(get_risk_repo),
    rec_repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
) -> RemediationPlanResponse:
    assessment = await assessment_repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    findings = await finding_repo.list_by_assessment(assessment_id)
    risks = await risk_repo.list_by_assessment(assessment_id)
    recs = await rec_repo.list_by_assessment(assessment_id)

    texts = [
        assessment.description,
        assessment.methodology or "",
        *(f.description for f in findings),
        *(f.reasoning or "" for f in findings),
        *(r.description for r in risks),
        *(r.reasoning or "" for r in risks),
    ]
    coverage = compute_coverage(texts)
    gaps = compute_gaps(coverage)
    links = compute_matches(gaps, recs)
    plan = compute_remediation_plan(assessment_id, gaps, links)

    def _action_resp(a) -> RemediationActionResponse:
        return RemediationActionResponse(
            priority_rank=a.priority_rank,
            article_code=a.article_code,
            framework=a.framework,
            article=a.article,
            gap_title=a.gap_title,
            gap_severity=a.gap_severity,
            regulatory_exposure=a.regulatory_exposure,
            timeline_label=a.timeline_label,
            explanation=a.explanation,
            remediation_hint=a.remediation_hint,
            linked_recommendation_ids=a.linked_recommendation_ids,
            linked_recommendation_titles=a.linked_recommendation_titles,
        )

    return RemediationPlanResponse(
        assessment_id=plan.assessment_id,
        total_gaps=plan.total_gaps,
        immediate_actions=[_action_resp(a) for a in plan.immediate_actions],
        short_term_actions=[_action_resp(a) for a in plan.short_term_actions],
        medium_term_actions=[_action_resp(a) for a in plan.medium_term_actions],
        linked_gap_count=plan.linked_gap_count,
        unlinked_gap_count=plan.unlinked_gap_count,
    )


@router.get("/{assessment_id}/brief", response_model=DecisionBriefResponse)
async def get_assessment_brief(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    risk_repo: SQLRiskRepository = Depends(get_risk_repo),
    rec_repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
) -> DecisionBriefResponse:
    assessment = await assessment_repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    findings = await finding_repo.list_by_assessment(assessment_id)
    risks = await risk_repo.list_by_assessment(assessment_id)
    recs = await rec_repo.list_by_assessment(assessment_id)

    texts = [
        assessment.description,
        assessment.methodology or "",
        *(f.description for f in findings),
        *(f.reasoning or "" for f in findings),
        *(r.description for r in risks),
        *(r.reasoning or "" for r in risks),
    ]
    coverage = compute_coverage(texts)
    gaps = compute_gaps(coverage)
    verdict = compute_verdict(coverage, gaps)
    links = compute_matches(gaps, recs)
    plan = compute_remediation_plan(assessment_id, gaps, links)

    critical_gaps = [g for g in gaps if g.gap_severity == "critical"]
    brief = compute_brief(
        assessment=assessment,
        verdict=verdict,
        top_critical_gaps=critical_gaps[:3],
        finding_titles=[f.title for f in findings],
        recommendation_titles=[r.title for r in recs],
        immediate_action_count=len(plan.immediate_actions),
    )

    return DecisionBriefResponse(
        assessment_id=brief.assessment_id,
        assessment_title=brief.assessment_title,
        assessment_status=brief.assessment_status,
        compliance_verdict=brief.compliance_verdict,
        mandatory_coverage_pct=brief.mandatory_coverage_pct,
        quality_score=brief.quality_score,
        finding_count=brief.finding_count,
        risk_count=brief.risk_count,
        recommendation_count=brief.recommendation_count,
        critical_gap_count=brief.critical_gap_count,
        immediate_action_count=brief.immediate_action_count,
        executive_summary=brief.executive_summary,
        key_findings=brief.key_findings,
        top_critical_gaps=brief.top_critical_gaps,
        top_recommendations=brief.top_recommendations,
        disclaimer=brief.disclaimer,
    )


@router.delete(
    "/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> None:
    existing = await repo.get_by_id(assessment_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(existing.organization_id, current_user.organization_id)
    await repo.delete(assessment_id)
