"""
EIOS Compliance Intelligence API

Endpoints:
  GET /compliance/frameworks               — list all supported regulatory frameworks
  GET /assessments/{id}/compliance         — full compliance report: coverage + gaps + verdict
  GET /assessments/{id}/compliance/gaps    — gap list only (lighter payload)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

import application.audit as audit_events
from application.compliance.coverage import compute_coverage
from application.compliance.frameworks import FrameworkArticle, all_frameworks, get_by_framework
from application.compliance.gaps import compute_gaps
from application.compliance.verdict import compute_verdict
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLFindingRepository,
    SQLRiskRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_audit_event_repo,
    get_current_user,
    get_finding_repo,
    get_risk_repo,
)
from interfaces.api.schemas.compliance import (
    ArticleCoverageResponse,
    ComplianceCoverageResponse,
    ComplianceVerdictResponse,
    FrameworkCoverageResponse,
    FrameworkInfo,
    GapResponse,
)

frameworks_router = APIRouter(
    prefix="/compliance",
    tags=["compliance"],
    dependencies=[Depends(get_current_user)],
)

assessments_compliance_router = APIRouter(
    prefix="/assessments",
    tags=["compliance"],
    dependencies=[Depends(get_current_user)],
)


def _article_to_response(
    article: FrameworkArticle, covered: bool = False
) -> ArticleCoverageResponse:
    return ArticleCoverageResponse(
        code=article.code,
        framework=article.framework,
        article=article.article,
        title=article.title,
        obligation_type=article.obligation_type,
        esg_categories=list(article.esg_categories),
        covered=covered,
    )


async def _load_assessment_texts(
    assessment_id: str,
    assessment_repo: SQLAssessmentRepository,
    finding_repo: SQLFindingRepository,
    risk_repo: SQLRiskRepository,
    user_org_id: str | None = None,
):
    """Return (assessment, texts) or raise 404. Enforces org isolation."""
    assessment = await assessment_repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    # Tenant isolation: treat cross-org access as 404 (no info leakage)
    if assessment.organization_id and user_org_id and assessment.organization_id != user_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    findings = await finding_repo.list_by_assessment(assessment_id)
    risks = await risk_repo.list_by_assessment(assessment_id)

    texts: list[str] = [
        assessment.description,
        assessment.methodology or "",
        *(f.description for f in findings),
        *(f.reasoning or "" for f in findings),
        *(r.description for r in risks),
        *(r.reasoning or "" for r in risks),
    ]
    return assessment, texts


@frameworks_router.get("/frameworks", response_model=list[FrameworkInfo])
async def list_frameworks() -> list[FrameworkInfo]:
    result = []
    for fw_name in all_frameworks():
        articles = get_by_framework(fw_name)
        mandatory = [a for a in articles if a.obligation_type == "mandatory"]
        recommended = [a for a in articles if a.obligation_type == "recommended"]
        result.append(
            FrameworkInfo(
                framework=fw_name,
                article_count=len(articles),
                mandatory_count=len(mandatory),
                recommended_count=len(recommended),
                articles=[_article_to_response(a) for a in articles],
            )
        )
    return result


@assessments_compliance_router.get(
    "/{assessment_id}/compliance",
    response_model=ComplianceCoverageResponse,
)
async def get_assessment_compliance(
    assessment_id: str,
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    risk_repo: SQLRiskRepository = Depends(get_risk_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    current_user=Depends(get_current_user),
) -> ComplianceCoverageResponse:
    assessment, texts = await _load_assessment_texts(
        assessment_id,
        assessment_repo,
        finding_repo,
        risk_repo,
        user_org_id=current_user.organization_id,
    )

    coverage = compute_coverage(texts)
    gaps = compute_gaps(coverage)
    verdict = compute_verdict(coverage, gaps)

    # Emit audit event for compliance assessment (governance action)
    event = audit_events.compliance_assessed(
        assessment_id=assessment_id,
        verdict_status=verdict.status,
        mandatory_coverage_ratio=verdict.mandatory_coverage_ratio,
        mandatory_gap_count=verdict.mandatory_gap_count,
        critical_gap_count=verdict.critical_gap_count,
        actor_id=current_user.id,
    )
    await audit_repo.save(event)

    fw_responses: list[FrameworkCoverageResponse] = [
        FrameworkCoverageResponse(
            framework=fc.framework,
            total_articles=fc.total_articles,
            covered_count=fc.covered_count,
            coverage_ratio=fc.coverage_ratio,
            articles=[
                ArticleCoverageResponse(
                    code=ac.code,
                    framework=ac.framework,
                    article=ac.article,
                    title=ac.title,
                    obligation_type=ac.obligation_type,
                    esg_categories=list(ac.esg_categories),
                    covered=ac.covered,
                )
                for ac in fc.articles
            ],
        )
        for fc in coverage.framework_coverage
    ]

    gap_responses: list[GapResponse] = [
        GapResponse(
            article_code=g.article_code,
            framework=g.framework,
            article=g.article,
            title=g.title,
            obligation_type=g.obligation_type,
            esg_categories=list(g.esg_categories),
            regulatory_exposure=g.regulatory_exposure,
            gap_severity=g.gap_severity,
            explanation=g.explanation,
            remediation_hint=g.remediation_hint,
        )
        for g in gaps
    ]

    verdict_response = ComplianceVerdictResponse(
        status=verdict.status,
        mandatory_coverage_ratio=verdict.mandatory_coverage_ratio,
        total_mandatory_articles=verdict.total_mandatory_articles,
        covered_mandatory_count=verdict.covered_mandatory_count,
        mandatory_gap_count=verdict.mandatory_gap_count,
        critical_gap_count=verdict.critical_gap_count,
        high_gap_count=verdict.high_gap_count,
        weighted_gap_score=verdict.weighted_gap_score,
        explanation=verdict.explanation,
        top_gap_codes=verdict.top_gap_codes,
    )

    return ComplianceCoverageResponse(
        assessment_id=assessment_id,
        covered_article_codes=coverage.covered_article_codes,
        framework_coverage=fw_responses,
        overall_coverage_ratio=coverage.overall_coverage_ratio,
        mandatory_coverage_ratio=coverage.mandatory_coverage_ratio,
        quality_score=assessment.quality_score,
        gaps=gap_responses,
        verdict=verdict_response,
    )


@assessments_compliance_router.get(
    "/{assessment_id}/compliance/gaps",
    response_model=list[GapResponse],
)
async def list_assessment_compliance_gaps(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    risk_repo: SQLRiskRepository = Depends(get_risk_repo),
) -> list[GapResponse]:
    _, texts = await _load_assessment_texts(
        assessment_id,
        assessment_repo,
        finding_repo,
        risk_repo,
        user_org_id=current_user.organization_id,
    )
    coverage = compute_coverage(texts)
    gaps = compute_gaps(coverage)

    return [
        GapResponse(
            article_code=g.article_code,
            framework=g.framework,
            article=g.article,
            title=g.title,
            obligation_type=g.obligation_type,
            esg_categories=list(g.esg_categories),
            regulatory_exposure=g.regulatory_exposure,
            gap_severity=g.gap_severity,
            explanation=g.explanation,
            remediation_hint=g.remediation_hint,
        )
        for g in gaps
    ]
