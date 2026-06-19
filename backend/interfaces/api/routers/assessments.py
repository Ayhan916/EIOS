from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

import application.audit as audit_events
import application.notification_service as notification_service
from application.compliance.coverage import compute_coverage
from application.compliance.gaps import compute_gaps
from application.compliance.verdict import compute_verdict
from application.remediation.brief import compute_brief
from application.remediation.matcher import compute_matches
from application.remediation.planner import compute_remediation_plan
from domain.assessment import Assessment
from domain.enums import (
    EntityStatus,
    NotificationType,
    ReviewActionType,
    ReviewStatus,
    is_valid_review_transition,
)
from domain.review_action import ReviewAction
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLFindingEvidenceLinkRepository,
    SQLFindingRepository,
    SQLRecommendationRepository,
    SQLReviewActionRepository,
    SQLRiskRepository,
    SQLSupplierRepository,
    SQLUserRepository,
    SQLWorkflowRunRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_audit_event_repo,
    get_current_user,
    get_db,
    get_finding_evidence_link_repo,
    get_finding_repo,
    get_recommendation_repo,
    get_review_action_repo,
    get_risk_repo,
    get_supplier_repo,
    get_user_repo,
    get_workflow_run_repo,
    require_admin,
    require_analyst,
    require_reviewer,
    scope_gate,
)
from interfaces.api.routers.api_platform import dispatch_webhook_event
from interfaces.api.schemas.assessment import AssessmentCreate, AssessmentResponse
from interfaces.api.schemas.finding import (
    EvidenceInsightsResponse,
    FindingEvidenceLinkResponse,
    FindingResponse,
    FindingWithLinksResponse,
)
from interfaces.api.schemas.pagination import Page, PaginationParams
from interfaces.api.schemas.remediation import (
    AssessmentTraceResponse,
    DecisionBriefResponse,
    RemediationActionResponse,
    RemediationPlanResponse,
)
from interfaces.api.schemas.review import (
    ActivityEvent,
    AssignReviewerRequest,
    ReviewActionRequest,
    ReviewActionResponse,
    SubmitForReviewRequest,
)
from interfaces.api.schemas.risk import RiskResponse


class AssessmentReviseRequest(BaseModel):
    reason: str = ""


router = APIRouter(
    prefix="/assessments",
    tags=["assessments"],
    dependencies=[Depends(get_current_user), Depends(scope_gate("assessments:read", "assessments:write"))],
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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> AssessmentResponse:
    if body.supplier_id is not None:
        supplier = await supplier_repo.get_by_id(body.supplier_id)
        if supplier is None or supplier.status.value == "Deleted":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Supplier not found.",
            )
        if supplier.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Supplier not found.",
            )
        from domain.enums import SupplierStatus  # noqa: PLC0415
        if supplier.supplier_status != SupplierStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Supplier '{supplier.name}' is {supplier.supplier_status.value.lower()} "
                    "and cannot be assigned to new assessments."
                ),
            )

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
        supplier_id=body.supplier_id,
    )
    saved = await repo.save(assessment)
    await audit_repo.save(
        audit_events.assessment_created_manually(
            assessment_id=saved.id,
            actor_id=current_user.id,
            actor_email=current_user.email,
            assessment_type=body.assessment_type,
        )
    )
    if current_user.organization_id:
        background_tasks.add_task(
            dispatch_webhook_event,
            current_user.organization_id,
            "assessment.created",
            {"assessment_id": saved.id, "title": saved.title, "assessment_type": saved.assessment_type},
        )
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


@router.get(
    "/{assessment_id}/evidence-insights",
    response_model=EvidenceInsightsResponse,
    summary="Evidence intelligence panel — per-finding citations (M25)",
)
async def get_assessment_evidence_insights(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    link_repo: SQLFindingEvidenceLinkRepository = Depends(get_finding_evidence_link_repo),
) -> EvidenceInsightsResponse:
    assessment = await assessment_repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    findings = await finding_repo.list_by_assessment(assessment_id)
    finding_ids = [f.id for f in findings]
    all_links = await link_repo.list_by_assessment_findings(finding_ids)

    links_by_finding: dict[str, list] = {}
    for lnk in all_links:
        links_by_finding.setdefault(lnk.finding_id, []).append(lnk)

    strength_dist: dict[str, int] = {}
    findings_with_links: list[FindingWithLinksResponse] = []
    for f in findings:
        f_links = links_by_finding.get(f.id, [])
        if f.evidence_strength:
            strength_dist[f.evidence_strength.value] = strength_dist.get(f.evidence_strength.value, 0) + 1
        findings_with_links.append(
            FindingWithLinksResponse(
                finding=FindingResponse.model_validate(f),
                evidence_links=[FindingEvidenceLinkResponse.model_validate(lnk) for lnk in f_links],
            )
        )

    return EvidenceInsightsResponse(
        assessment_id=assessment_id,
        total_findings=len(findings),
        linked_findings=sum(1 for f in findings if links_by_finding.get(f.id)),
        total_evidence_links=len(all_links),
        strength_distribution=strength_dist,
        findings=findings_with_links,
    )


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
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    user_repo: SQLUserRepository = Depends(get_user_repo),
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

    # Notify the assessment creator
    if assessment.created_by and assessment.created_by != current_user.id:
        creator = await user_repo.get_by_id(assessment.created_by)
        if creator and creator.organization_id == current_user.organization_id:
            await notification_service.notify(
                session=session,
                user_id=creator.id,
                organization_id=creator.organization_id or "",
                notification_type=NotificationType.ASSESSMENT_APPROVED,
                title="Assessment approved",
                body=f"Your assessment has been approved by {current_user.display_name}.",
                entity_type="assessment",
                entity_id=assessment_id,
                dedupe_key=f"assessment_approved:{assessment_id}",
                user_email=creator.email,
            )

    if current_user.organization_id:
        background_tasks.add_task(
            dispatch_webhook_event,
            current_user.organization_id,
            "assessment.approved",
            {"assessment_id": assessment_id, "approved_by": current_user.id},
        )
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


@router.post(
    "/{assessment_id}/submit-for-review",
    response_model=AssessmentResponse,
    dependencies=[Depends(require_analyst)],
    summary="Submit assessment for formal review (M26)",
)
async def submit_for_review(
    assessment_id: str,
    body: SubmitForReviewRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    user_repo: SQLUserRepository = Depends(get_user_repo),
) -> AssessmentResponse:
    assessment = await repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    if not is_valid_review_transition(assessment.review_status, ReviewStatus.IN_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit for review from status '{assessment.review_status.value}'",
        )

    assessment.review_status = ReviewStatus.IN_REVIEW
    assessment.updated_by = current_user.id

    if body.reviewer_id:
        # Validate reviewer belongs to same org and has reviewer+ role
        reviewer = await user_repo.get_by_id(body.reviewer_id)
        if reviewer is None or reviewer.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewer not found")
        from domain.enums import UserRole, has_min_role
        if not has_min_role(reviewer.role, UserRole.REVIEWER):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assigned reviewer must have reviewer role or higher",
            )
        assessment.assigned_reviewer_id = body.reviewer_id
        if body.review_due_date:
            assessment.review_due_date = body.review_due_date

    saved = await repo.save(assessment)
    await audit_repo.save(
        audit_events.review_submitted(
            assessment_id=assessment_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    )

    # Notify assigned reviewer
    if assessment.assigned_reviewer_id:
        reviewer = await user_repo.get_by_id(assessment.assigned_reviewer_id)
        if reviewer and reviewer.organization_id == current_user.organization_id:
            await notification_service.notify(
                session=session,
                user_id=reviewer.id,
                organization_id=reviewer.organization_id or "",
                notification_type=NotificationType.REVIEWER_ASSIGNED,
                title="Assessment assigned for review",
                body=f"{current_user.display_name} submitted '{assessment.title}' for your review.",
                entity_type="assessment",
                entity_id=assessment_id,
                dedupe_key=f"review_assigned:{assessment_id}:{reviewer.id}",
                user_email=reviewer.email,
            )

    return AssessmentResponse.model_validate(saved)


@router.post(
    "/{assessment_id}/assign-reviewer",
    response_model=AssessmentResponse,
    dependencies=[Depends(require_admin)],
    summary="Assign a reviewer to an assessment (M26)",
)
async def assign_reviewer(
    assessment_id: str,
    body: AssignReviewerRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    user_repo: SQLUserRepository = Depends(get_user_repo),
) -> AssessmentResponse:
    assessment = await repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    reviewer = await user_repo.get_by_id(body.reviewer_id)
    if reviewer is None or reviewer.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewer not found")
    from domain.enums import UserRole, has_min_role
    if not has_min_role(reviewer.role, UserRole.REVIEWER):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assigned user must have reviewer role or higher",
        )

    assessment.assigned_reviewer_id = body.reviewer_id
    if body.review_due_date:
        assessment.review_due_date = body.review_due_date
    assessment.updated_by = current_user.id
    saved = await repo.save(assessment)

    await audit_repo.save(
        audit_events.reviewer_assigned(
            assessment_id=assessment_id,
            reviewer_id=body.reviewer_id,
            assigned_by_id=current_user.id,
            assigned_by_email=current_user.email,
        )
    )

    await notification_service.notify(
        session=session,
        user_id=reviewer.id,
        organization_id=reviewer.organization_id or "",
        notification_type=NotificationType.REVIEWER_ASSIGNED,
        title="You have been assigned as reviewer",
        body=f"{current_user.display_name} assigned you to review '{assessment.title}'.",
        entity_type="assessment",
        entity_id=assessment_id,
        dedupe_key=f"reviewer_assigned:{assessment_id}:{reviewer.id}",
        user_email=reviewer.email,
    )

    return AssessmentResponse.model_validate(saved)


@router.post(
    "/{assessment_id}/review-action",
    response_model=ReviewActionResponse,
    dependencies=[Depends(require_reviewer)],
    summary="Submit a formal review decision (approve / reject / request changes) (M26)",
)
async def submit_review_action(
    assessment_id: str,
    body: ReviewActionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    review_action_repo: SQLReviewActionRepository = Depends(get_review_action_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    user_repo: SQLUserRepository = Depends(get_user_repo),
) -> ReviewActionResponse:
    assessment = await repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    if assessment.review_status != ReviewStatus.IN_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Assessment must be InReview to submit a review action (current: {assessment.review_status.value})",
        )

    # Four-eyes principle: the creator of the assessment cannot review their own work
    if assessment.created_by and assessment.created_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewers cannot approve, reject or request changes on an assessment they created (four-eyes principle).",
        )

    # Map action to target review status
    action_to_status: dict[ReviewActionType, ReviewStatus] = {
        ReviewActionType.APPROVE: ReviewStatus.APPROVED,
        ReviewActionType.REJECT: ReviewStatus.CHANGES_REQUESTED,
        ReviewActionType.REQUEST_CHANGES: ReviewStatus.CHANGES_REQUESTED,
    }
    target_review_status = action_to_status[body.action_type]

    # Persist the formal review decision
    review_action = ReviewAction(
        assessment_id=assessment_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action_type=body.action_type,
        comment=body.comment,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    saved_action = await review_action_repo.save(review_action)

    # Transition assessment review status
    assessment.review_status = target_review_status
    assessment.updated_by = current_user.id
    if body.action_type == ReviewActionType.APPROVE:
        assessment.approved_by = current_user.id
        assessment.approval_date = datetime.now(UTC)
        assessment.status = EntityStatus.APPROVED

    await repo.save(assessment)

    await audit_repo.save(
        audit_events.review_action_taken(
            assessment_id=assessment_id,
            action_type=body.action_type.value,
            actor_id=current_user.id,
            actor_email=current_user.email,
            comment=body.comment,
        )
    )

    # Notify assessment creator
    if assessment.created_by and assessment.created_by != current_user.id:
        creator = await user_repo.get_by_id(assessment.created_by)
        if creator and creator.organization_id == current_user.organization_id:
            if body.action_type == ReviewActionType.APPROVE:
                notif_type = NotificationType.ASSESSMENT_APPROVED
                title = "Assessment approved"
                body_text = f"Your assessment '{assessment.title}' was approved by {current_user.display_name}."
                dedupe_key = f"assessment_approved:{assessment_id}"
            else:
                notif_type = NotificationType.CHANGES_REQUESTED
                title = "Changes requested on your assessment"
                body_text = (
                    f"{current_user.display_name} requested changes on '{assessment.title}'."
                    + (f" Note: {body.comment}" if body.comment else "")
                )
                dedupe_key = f"changes_requested:{assessment_id}:{saved_action.id}"
            await notification_service.notify(
                session=session,
                user_id=creator.id,
                organization_id=creator.organization_id or "",
                notification_type=notif_type,
                title=title,
                body=body_text,
                entity_type="assessment",
                entity_id=assessment_id,
                dedupe_key=dedupe_key,
                user_email=creator.email,
            )

    return ReviewActionResponse(
        id=saved_action.id,
        assessment_id=saved_action.assessment_id,
        actor_id=saved_action.actor_id,
        actor_email=saved_action.actor_email,
        action_type=saved_action.action_type.value,
        comment=saved_action.comment,
        created_at=saved_action.created_at,
    )


@router.get(
    "/{assessment_id}/review-actions",
    response_model=list[ReviewActionResponse],
    summary="List all formal review decisions for an assessment (M26)",
)
async def list_review_actions(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    review_action_repo: SQLReviewActionRepository = Depends(get_review_action_repo),
) -> list[ReviewActionResponse]:
    assessment = await repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    actions = await review_action_repo.list_by_assessment(assessment_id)
    return [
        ReviewActionResponse(
            id=a.id,
            assessment_id=a.assessment_id,
            actor_id=a.actor_id,
            actor_email=a.actor_email,
            action_type=a.action_type.value,
            comment=a.comment,
            created_at=a.created_at,
        )
        for a in actions
    ]


@router.get(
    "/{assessment_id}/activity",
    response_model=list[ActivityEvent],
    summary="Unified chronological activity timeline for an assessment (M26)",
)
async def get_assessment_activity(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    review_action_repo: SQLReviewActionRepository = Depends(get_review_action_repo),
    user_repo: SQLUserRepository = Depends(get_user_repo),
) -> list[ActivityEvent]:
    assessment = await repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    _assert_org_access(assessment.organization_id, current_user.organization_id)

    events: list[ActivityEvent] = []

    # 1. Audit trail events for this assessment
    audit_ev_list = await audit_repo.list_by_entity("Assessment", assessment_id)
    for ev in audit_ev_list:
        actor_name: str | None = None
        if ev.actor_id:
            u = await user_repo.get_by_id(ev.actor_id)
            if u:
                actor_name = u.display_name
        events.append(
            ActivityEvent(
                event_type="audit",
                timestamp=ev.created_at,
                actor_id=ev.actor_id,
                actor_name=actor_name,
                action=ev.action,
                detail=ev.detail,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
            )
        )

    # 2. Review actions
    review_actions = await review_action_repo.list_by_assessment(assessment_id)
    for ra in review_actions:
        events.append(
            ActivityEvent(
                event_type="review_action",
                timestamp=ra.created_at,
                actor_id=ra.actor_id,
                actor_name=ra.actor_email,
                action=f"review.{ra.action_type.value}",
                detail=ra.comment,
                entity_type="Assessment",
                entity_id=assessment_id,
            )
        )

    # Sort chronologically
    events.sort(key=lambda e: e.timestamp)
    return events


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
