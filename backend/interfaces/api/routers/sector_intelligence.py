"""
EIOS Sector Intelligence API (M19)

Endpoints:
  GET /sectors/profiles                     — list all sector ESG profiles
  GET /sectors/{sector_id}/profile          — ESG profile for a specific sector
  GET /sectors/profile/nace/{nace_code}     — ESG profile by NACE code (no DB lookup)
  GET /assessments/{assessment_id}/benchmark — benchmark assessment vs sector baseline + org peers
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from application.compliance.coverage import compute_coverage
from application.sector_intelligence.benchmarking import compute_benchmark
from application.sector_intelligence.profiles import (
    SectorESGProfile,
    all_profiles,
    get_profile,
)
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLFindingRepository,
    SQLRiskRepository,
    SQLSectorRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_current_user,
    get_finding_repo,
    get_risk_repo,
    get_sector_repo,
)
from interfaces.api.schemas.sector_intelligence import (
    PeerSummaryResponse,
    SectorBenchmarkResponse,
    SectorESGProfileResponse,
    SeverityDistributionResponse,
)

sector_intelligence_router = APIRouter(
    prefix="/sectors",
    tags=["sector-intelligence"],
    dependencies=[Depends(get_current_user)],
)

assessments_benchmark_router = APIRouter(
    prefix="/assessments",
    tags=["sector-intelligence"],
    dependencies=[Depends(get_current_user)],
)


def _profile_to_response(p: SectorESGProfile) -> SectorESGProfileResponse:
    return SectorESGProfileResponse(
        nace_section=p.nace_section,
        section_name=p.section_name,
        environmental_risk=p.environmental_risk,
        social_risk=p.social_risk,
        governance_risk=p.governance_risk,
        overall_risk=p.overall_risk,
        key_risk_themes=list(p.key_risk_themes),
        applicable_frameworks=list(p.applicable_frameworks),
        baseline_mandatory_coverage=p.baseline_mandatory_coverage,
        expected_min_findings=p.expected_min_findings,
        expected_min_risks=p.expected_min_risks,
        regulatory_exposure_notes=p.regulatory_exposure_notes,
        esg_priority_categories=list(p.esg_priority_categories),
    )


@sector_intelligence_router.get(
    "/profiles",
    response_model=list[SectorESGProfileResponse],
    summary="List all NACE sector ESG risk profiles",
)
async def list_sector_profiles() -> list[SectorESGProfileResponse]:
    return [_profile_to_response(p) for p in all_profiles()]


@sector_intelligence_router.get(
    "/profile/nace/{nace_code}",
    response_model=SectorESGProfileResponse,
    summary="Get ESG risk profile for a NACE code (no database lookup required)",
)
async def get_profile_by_nace(nace_code: str) -> SectorESGProfileResponse:
    profile = get_profile(nace_code)
    return _profile_to_response(profile)


@sector_intelligence_router.get(
    "/{sector_id}/profile",
    response_model=SectorESGProfileResponse,
    summary="Get ESG risk profile for a sector entity",
)
async def get_sector_profile(
    sector_id: str,
    repo: SQLSectorRepository = Depends(get_sector_repo),
) -> SectorESGProfileResponse:
    sector = await repo.get_by_id(sector_id)
    if sector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sector not found")
    profile = get_profile(sector.nace_code)
    return _profile_to_response(profile)


@assessments_benchmark_router.get(
    "/{assessment_id}/benchmark",
    response_model=SectorBenchmarkResponse,
    summary="Benchmark an assessment against its sector ESG baseline and org peers",
)
async def benchmark_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    risk_repo: SQLRiskRepository = Depends(get_risk_repo),
    sector_repo: SQLSectorRepository = Depends(get_sector_repo),
) -> SectorBenchmarkResponse:
    # Load the target assessment
    assessment = await assessment_repo.get_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if (
        assessment.organization_id
        and current_user.organization_id
        and assessment.organization_id != current_user.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    # Load sector (if linked)
    sector = None
    if assessment.sector_id:
        sector = await sector_repo.get_by_id(assessment.sector_id)

    # Load findings and risks for the target assessment
    findings = await finding_repo.list_by_assessment(assessment_id)
    risks = await risk_repo.list_by_assessment(assessment_id)

    # Compute compliance coverage from assessment text
    texts = [
        assessment.description or "",
        assessment.methodology or "",
        *(f.description for f in findings),
        *(f.reasoning or "" for f in findings),
        *(r.description for r in risks),
        *(r.reasoning or "" for r in risks),
    ]
    coverage_report = compute_coverage(texts)
    mandatory_coverage = coverage_report.mandatory_coverage_ratio

    # Load org peers in the same sector (exclude this assessment)
    peers_data: list[tuple] = []
    if assessment.sector_id and assessment.organization_id:
        all_sector_assessments = await assessment_repo.list_by_sector(assessment.sector_id)
        for peer in all_sector_assessments:
            if peer.id == assessment_id:
                continue
            if peer.organization_id != assessment.organization_id:
                continue
            peer_findings = await finding_repo.list_by_assessment(peer.id)
            peers_data.append((peer, peer_findings))

    # Run the benchmark computation
    benchmark = compute_benchmark(
        assessment=assessment,
        sector=sector,
        findings=findings,
        risks=risks,
        mandatory_coverage=mandatory_coverage,
        peers=peers_data,
    )

    # Serialise to response
    return SectorBenchmarkResponse(
        assessment_id=benchmark.assessment_id,
        assessment_title=benchmark.assessment_title,
        sector_id=benchmark.sector_id,
        sector_nace_code=benchmark.sector_nace_code,
        sector_name=benchmark.sector_name,
        profile_nace_section=benchmark.profile_nace_section,
        finding_distribution=SeverityDistributionResponse(
            critical=benchmark.finding_distribution.critical,
            high=benchmark.finding_distribution.high,
            medium=benchmark.finding_distribution.medium,
            low=benchmark.finding_distribution.low,
            total=benchmark.finding_distribution.total,
            high_or_critical_count=benchmark.finding_distribution.high_or_critical_count,
        ),
        risk_distribution=SeverityDistributionResponse(
            critical=benchmark.risk_distribution.critical,
            high=benchmark.risk_distribution.high,
            medium=benchmark.risk_distribution.medium,
            low=benchmark.risk_distribution.low,
            total=benchmark.risk_distribution.total,
            high_or_critical_count=benchmark.risk_distribution.high_or_critical_count,
        ),
        quality_score=benchmark.quality_score,
        baseline_mandatory_coverage=benchmark.baseline_mandatory_coverage,
        expected_min_findings=benchmark.expected_min_findings,
        expected_min_risks=benchmark.expected_min_risks,
        environmental_risk=benchmark.environmental_risk,
        social_risk=benchmark.social_risk,
        governance_risk=benchmark.governance_risk,
        overall_sector_risk=benchmark.overall_sector_risk,
        key_risk_themes=benchmark.key_risk_themes,
        applicable_frameworks=benchmark.applicable_frameworks,
        esg_priority_categories=benchmark.esg_priority_categories,
        regulatory_exposure_notes=benchmark.regulatory_exposure_notes,
        mandatory_coverage=benchmark.mandatory_coverage,
        coverage_vs_baseline=benchmark.coverage_vs_baseline,
        coverage_rating=benchmark.coverage_rating,
        coverage_explanation=benchmark.coverage_explanation,
        finding_adequacy=benchmark.finding_adequacy,
        finding_explanation=benchmark.finding_explanation,
        key_themes_identified=benchmark.key_themes_identified,
        key_themes_not_addressed=benchmark.key_themes_not_addressed,
        peer_count=benchmark.peer_count,
        peers=[
            PeerSummaryResponse(
                assessment_id=p.assessment_id,
                title=p.title,
                quality_score=p.quality_score,
                finding_count=p.finding_count,
                risk_count=p.risk_count,
                high_critical_finding_count=p.high_critical_finding_count,
            )
            for p in benchmark.peers
        ],
        org_avg_quality_score=benchmark.org_avg_quality_score,
        org_avg_finding_count=benchmark.org_avg_finding_count,
        benchmark_rating=benchmark.benchmark_rating,
        benchmark_explanation=benchmark.benchmark_explanation,
    )
