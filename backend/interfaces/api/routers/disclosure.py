"""
M32 Sustainability Reporting & Disclosure Management API

Routes:
  GET    /reporting/frameworks                              — list disclosure frameworks
  GET    /reporting/frameworks/{framework_id}              — framework detail + requirements
  GET    /reporting/frameworks/{framework_id}/requirements — list requirements
  GET    /reporting/dashboard                              — org-level disclosure dashboard
  GET    /reporting/responses                              — list org's disclosure responses
  POST   /reporting/responses                              — create a disclosure response
  GET    /reporting/responses/{response_id}               — response detail
  PATCH  /reporting/responses/{response_id}               — update narrative text
  POST   /reporting/responses/{response_id}/submit        — Draft → In Review
  POST   /reporting/responses/{response_id}/approve       — In Review → Approved
  POST   /reporting/responses/{response_id}/reject        — In Review → Draft
  POST   /reporting/responses/{response_id}/recalculate   — recompute coverage + readiness
  GET    /reporting/workspace/{requirement_id}            — requirement + all linked context
  GET    /reporting/suppliers/{supplier_id}/contribution  — supplier → disclosure impact
  GET    /reporting/assessments/{assessment_id}/disclosures — assessment → disclosure mapping
  GET    /reporting/packages                              — list published packages
  POST   /reporting/packages/generate                     — generate + publish a package
  GET    /reporting/packages/{package_id}                 — package detail with snapshot
  GET    /reporting/packages/{package_id}/download        — download as PDF
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from io import BytesIO

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.disclosure.coverage_engine import compute_coverage
from application.disclosure.readiness_engine import determine_readiness
from application.disclosure.workflow import transition_disclosure
from domain.disclosure import DisclosureResponse
from domain.enums import EntityStatus
from domain.reporting_package import ReportingPackage as ReportingPackageDomain
from domain.user import User
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.repositories.disclosure import (
    SQLDisclosureFrameworkRepository,
    SQLDisclosureRequirementRepository,
    SQLDisclosureResponseRepository,
    SQLReportingPackageRepository,
)
from infrastructure.persistence.repositories.regulatory import (
    SQLComplianceGapRepository,
    SQLRequirementMappingRepository,
)
from infrastructure.persistence.repositories.evidence import SQLEvidenceRepository
from interfaces.api.deps import (
    get_current_user,
    get_db,
    require_analyst,
    require_reviewer,
    require_executive,
    scope_gate,
)
from interfaces.api.schemas.disclosure import (
    ApproveDisclosureRequest,
    AssessmentDisclosureMapping,
    CreateDisclosureResponseRequest,
    DisclosureDashboardResponse,
    DisclosureFrameworkDetailResponse,
    DisclosureFrameworkResponse,
    DisclosureRequirementResponse,
    DisclosureResponseDetail,
    DisclosureResponseSummary,
    DisclosureWorkspaceResponse,
    FrameworkDisclosureSummary,
    GeneratePackageRequest,
    LinkedEntitySummary,
    RejectDisclosureRequest,
    ReportingPackageDetail,
    ReportingPackageSummary,
    SupplierDisclosureContribution,
    UpdateDisclosureResponseRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/reporting",
    tags=["Sustainability Reporting"],
    dependencies=[Depends(scope_gate("reporting:read", "reporting:write"))],
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fw_to_schema(fw) -> DisclosureFrameworkResponse:
    return DisclosureFrameworkResponse(
        id=fw.id,
        code=fw.code,
        name=fw.name,
        fw_version=fw.fw_version,
        jurisdiction=fw.jurisdiction,
        effective_date=str(fw.effective_date) if fw.effective_date else None,
        description=fw.description,
        status=fw.status.value,
    )


def _req_to_schema(req) -> DisclosureRequirementResponse:
    return DisclosureRequirementResponse(
        id=req.id,
        framework_id=req.framework_id,
        reference=req.reference,
        title=req.title,
        description=req.description,
        category=req.category,
        status=req.status.value,
    )


def _resp_to_detail(resp) -> DisclosureResponseDetail:
    return DisclosureResponseDetail(
        id=resp.id,
        organization_id=resp.organization_id,
        requirement_id=resp.requirement_id,
        disclosure_status=resp.disclosure_status,
        narrative_text=resp.narrative_text,
        evidence_coverage=resp.evidence_coverage,
        coverage_category=resp.coverage_category,
        coverage_rationale=resp.coverage_rationale,
        readiness_status=resp.readiness_status,
        readiness_rationale=resp.readiness_rationale,
        reviewed_by=resp.reviewed_by,
        approved_by=resp.approved_by,
        published_at=resp.published_at.isoformat() if resp.published_at else None,
        created_at=resp.created_at.isoformat(),
        updated_at=resp.updated_at.isoformat(),
    )


def _resp_to_summary(resp) -> DisclosureResponseSummary:
    return DisclosureResponseSummary(
        id=resp.id,
        organization_id=resp.organization_id,
        requirement_id=resp.requirement_id,
        disclosure_status=resp.disclosure_status,
        evidence_coverage=resp.evidence_coverage,
        coverage_category=resp.coverage_category,
        readiness_status=resp.readiness_status,
        updated_at=resp.updated_at.isoformat(),
    )


def _pkg_to_summary(pkg) -> ReportingPackageSummary:
    return ReportingPackageSummary(
        id=pkg.id,
        organization_id=pkg.organization_id,
        framework_id=pkg.framework_id,
        framework_code=pkg.framework_code,
        framework_version=pkg.framework_version,
        package_type=pkg.package_type,
        publication_date=pkg.publication_date.isoformat(),
        published_by=pkg.published_by,
        report_hash=pkg.report_hash,
        status=pkg.status.value,
    )


def _pkg_to_detail(pkg) -> ReportingPackageDetail:
    return ReportingPackageDetail(
        id=pkg.id,
        organization_id=pkg.organization_id,
        framework_id=pkg.framework_id,
        framework_code=pkg.framework_code,
        framework_version=pkg.framework_version,
        package_type=pkg.package_type,
        publication_date=pkg.publication_date.isoformat(),
        published_by=pkg.published_by,
        report_hash=pkg.report_hash,
        report_data=pkg.report_data,
        status=pkg.status.value,
    )


async def _recompute_and_save(
    response: DisclosureResponse,
    session: AsyncSession,
) -> DisclosureResponse:
    """Recompute coverage + readiness and persist the updated response."""
    mapping_repo = SQLRequirementMappingRepository(session)
    gap_repo = SQLComplianceGapRepository(session)
    evidence_repo = SQLEvidenceRepository(session)

    # Pull requirement mappings for this requirement scoped to the org
    mappings = await mapping_repo.list_for_org(
        organization_id=response.organization_id,
        requirement_id=response.requirement_id,
    )
    mapping_confidences = [m.confidence for m in mappings]

    # Pull evidence for all mapped entities (findings + risks)
    entity_ids = list({m.entity_id for m in mappings})
    evidence_items: list[dict] = []
    if entity_ids:
        evidences = await evidence_repo.list_for_org(response.organization_id, limit=500)
        evidence_items = [
            {"reliability_score": e.reliability_score, "evidence_type": e.evidence_type}
            for e in evidences
        ]

    coverage_result = compute_coverage(
        evidence_items=evidence_items,
        mapping_confidences=mapping_confidences,
    )

    # Count open critical compliance gaps for this requirement
    gaps = await gap_repo.list_for_org(
        organization_id=response.organization_id,
        requirement_id=response.requirement_id,
        severity="Critical",
    )
    critical_gap_count = len(gaps)

    readiness_status, readiness_rationale = determine_readiness(
        disclosure_status=response.disclosure_status,
        narrative_text=response.narrative_text,
        evidence_coverage=coverage_result.score,
        critical_gap_count=critical_gap_count,
    )

    response.evidence_coverage = coverage_result.score
    response.coverage_category = coverage_result.category
    response.coverage_rationale = coverage_result.factors
    response.readiness_status = readiness_status
    response.readiness_rationale = readiness_rationale
    response.updated_at = datetime.now(UTC)

    resp_repo = SQLDisclosureResponseRepository(session)
    await resp_repo.save(response)
    return response


# ── Frameworks ────────────────────────────────────────────────────────────────


@router.get("/frameworks", response_model=list[DisclosureFrameworkResponse])
async def list_frameworks(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> list[DisclosureFrameworkResponse]:
    fw_repo = SQLDisclosureFrameworkRepository(session)
    frameworks = await fw_repo.list_active()
    return [_fw_to_schema(fw) for fw in frameworks]


@router.get("/frameworks/{framework_id}", response_model=DisclosureFrameworkDetailResponse)
async def get_framework(
    framework_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DisclosureFrameworkDetailResponse:
    fw_repo = SQLDisclosureFrameworkRepository(session)
    req_repo = SQLDisclosureRequirementRepository(session)

    fw = await fw_repo.get_by_id(framework_id)
    if fw is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    requirements = await req_repo.list_for_framework(framework_id)
    return DisclosureFrameworkDetailResponse(
        framework=_fw_to_schema(fw),
        requirements=[_req_to_schema(r) for r in requirements],
        total_requirements=len(requirements),
    )


@router.get(
    "/frameworks/{framework_id}/requirements",
    response_model=list[DisclosureRequirementResponse],
)
async def list_requirements(
    framework_id: str,
    category: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> list[DisclosureRequirementResponse]:
    fw_repo = SQLDisclosureFrameworkRepository(session)
    req_repo = SQLDisclosureRequirementRepository(session)

    if not await fw_repo.get_by_id(framework_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    reqs = await req_repo.list_for_framework(framework_id)
    if category:
        reqs = [r for r in reqs if r.category.lower() == category.lower()]
    return [_req_to_schema(r) for r in reqs]


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DisclosureDashboardResponse)
async def disclosure_dashboard(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DisclosureDashboardResponse:
    org_id = current_user.organization_id
    fw_repo = SQLDisclosureFrameworkRepository(session)
    req_repo = SQLDisclosureRequirementRepository(session)
    resp_repo = SQLDisclosureResponseRepository(session)
    pkg_repo = SQLReportingPackageRepository(session)

    frameworks = await fw_repo.list_active()
    packages = await pkg_repo.list_for_org(org_id)

    fw_summaries: list[FrameworkDisclosureSummary] = []
    total_req = total_pub = total_appr = total_draft = total_ns = 0

    for fw in frameworks:
        reqs = await req_repo.list_for_framework(fw.id)
        req_ids = {r.id for r in reqs}
        responses = await resp_repo.list_for_org(org_id, framework_id=fw.id)

        counts = {
            "Not Started": 0, "Draft": 0, "In Review": 0, "Approved": 0, "Published": 0
        }
        for resp in responses:
            counts[resp.disclosure_status] = counts.get(resp.disclosure_status, 0) + 1
        # Requirements with no response are "Not Started"
        responded_req_ids = {r.requirement_id for r in responses}
        counts["Not Started"] += len(req_ids - responded_req_ids)

        n_total = len(reqs)
        n_pub = counts["Published"]
        n_appr = counts["Approved"]
        completion_pct = (n_pub / n_total * 100) if n_total else 0.0
        avg_cov = (
            sum(r.evidence_coverage for r in responses) / len(responses)
            if responses else 0.0
        )
        critical_blockers = sum(
            1 for r in responses if r.readiness_status == "Blocked"
        )

        fw_summaries.append(FrameworkDisclosureSummary(
            framework_id=fw.id,
            framework_code=fw.code,
            framework_name=fw.name,
            fw_version=fw.fw_version,
            total_requirements=n_total,
            not_started=counts["Not Started"],
            draft=counts["Draft"],
            in_review=counts["In Review"],
            approved=counts["Approved"],
            published=counts["Published"],
            completion_pct=round(completion_pct, 1),
            avg_coverage=round(avg_cov, 4),
            critical_blockers=critical_blockers,
        ))

        total_req += n_total
        total_pub += n_pub
        total_appr += n_appr
        total_draft += counts["Draft"]
        total_ns += counts["Not Started"]

    overall_pct = (total_pub / total_req * 100) if total_req else 0.0

    return DisclosureDashboardResponse(
        organization_id=org_id,
        frameworks=fw_summaries,
        total_requirements=total_req,
        total_published=total_pub,
        total_approved=total_appr,
        total_draft=total_draft,
        total_not_started=total_ns,
        overall_completion_pct=round(overall_pct, 1),
        packages_published=len(packages),
    )


# ── Disclosure Responses ──────────────────────────────────────────────────────


@router.get("/responses", response_model=list[DisclosureResponseSummary])
async def list_responses(
    framework_id: str | None = Query(None),
    disclosure_status: str | None = Query(None),
    readiness_status: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> list[DisclosureResponseSummary]:
    resp_repo = SQLDisclosureResponseRepository(session)
    responses = await resp_repo.list_for_org(
        organization_id=current_user.organization_id,
        framework_id=framework_id,
        disclosure_status=disclosure_status,
        readiness_status=readiness_status,
    )
    return [_resp_to_summary(r) for r in responses]


@router.post("/responses", response_model=DisclosureResponseDetail, status_code=201)
async def create_response(
    body: CreateDisclosureResponseRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DisclosureResponseDetail:
    req_repo = SQLDisclosureRequirementRepository(session)
    resp_repo = SQLDisclosureResponseRepository(session)

    req = await req_repo.get_by_id(body.requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")

    existing = await resp_repo.get_for_requirement(
        current_user.organization_id, body.requirement_id
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Disclosure response already exists for this requirement")

    resp = DisclosureResponse(
        organization_id=current_user.organization_id,
        requirement_id=body.requirement_id,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    await resp_repo.save(resp)
    return _resp_to_detail(resp)


@router.get("/responses/{response_id}", response_model=DisclosureResponseDetail)
async def get_response(
    response_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DisclosureResponseDetail:
    resp_repo = SQLDisclosureResponseRepository(session)
    resp = await resp_repo.get_by_id(response_id)
    if resp is None or resp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Disclosure response not found")
    return _resp_to_detail(resp)


@router.patch("/responses/{response_id}", response_model=DisclosureResponseDetail)
async def update_response(
    response_id: str,
    body: UpdateDisclosureResponseRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DisclosureResponseDetail:
    resp_repo = SQLDisclosureResponseRepository(session)
    resp = await resp_repo.get_by_id(response_id)
    if resp is None or resp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Disclosure response not found")
    if resp.disclosure_status == "Published":
        raise HTTPException(status_code=409, detail="Cannot edit a published disclosure")

    if body.narrative_text is not None:
        resp.narrative_text = body.narrative_text
        if resp.disclosure_status == "Not Started":
            resp.disclosure_status = "Draft"

    resp.updated_by = current_user.id
    resp = await _recompute_and_save(resp, session)
    return _resp_to_detail(resp)


@router.post("/responses/{response_id}/submit", response_model=DisclosureResponseDetail)
async def submit_for_review(
    response_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DisclosureResponseDetail:
    resp_repo = SQLDisclosureResponseRepository(session)
    resp = await resp_repo.get_by_id(response_id)
    if resp is None or resp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Disclosure response not found")

    try:
        updates = transition_disclosure(
            current_status=resp.disclosure_status,
            to_status="In Review",
            narrative_text=resp.narrative_text,
            actor_id=current_user.id,
            reviewed_by=resp.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    resp.disclosure_status = updates["disclosure_status"]
    resp.reviewed_by = updates["reviewed_by"]
    resp.updated_by = current_user.id
    resp = await _recompute_and_save(resp, session)
    return _resp_to_detail(resp)


@router.post("/responses/{response_id}/approve", response_model=DisclosureResponseDetail)
async def approve_disclosure(
    response_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_reviewer),
) -> DisclosureResponseDetail:
    resp_repo = SQLDisclosureResponseRepository(session)
    resp = await resp_repo.get_by_id(response_id)
    if resp is None or resp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Disclosure response not found")

    try:
        updates = transition_disclosure(
            current_status=resp.disclosure_status,
            to_status="Approved",
            narrative_text=resp.narrative_text,
            actor_id=current_user.id,
            reviewed_by=resp.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    resp.disclosure_status = updates["disclosure_status"]
    resp.approved_by = updates["approved_by"]
    resp.updated_by = current_user.id
    resp = await _recompute_and_save(resp, session)
    return _resp_to_detail(resp)


@router.post("/responses/{response_id}/reject", response_model=DisclosureResponseDetail)
async def reject_disclosure(
    response_id: str,
    body: RejectDisclosureRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_reviewer),
) -> DisclosureResponseDetail:
    resp_repo = SQLDisclosureResponseRepository(session)
    resp = await resp_repo.get_by_id(response_id)
    if resp is None or resp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Disclosure response not found")

    try:
        updates = transition_disclosure(
            current_status=resp.disclosure_status,
            to_status="Draft",
            narrative_text=resp.narrative_text,
            actor_id=current_user.id,
            reviewed_by=resp.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    resp.disclosure_status = updates["disclosure_status"]
    resp.reviewed_by = updates["reviewed_by"]
    if body.rationale:
        resp.readiness_rationale = f"Rejected: {body.rationale}"
    resp.updated_by = current_user.id
    resp = await _recompute_and_save(resp, session)
    return _resp_to_detail(resp)


@router.post("/responses/{response_id}/recalculate", response_model=DisclosureResponseDetail)
async def recalculate_coverage(
    response_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DisclosureResponseDetail:
    resp_repo = SQLDisclosureResponseRepository(session)
    resp = await resp_repo.get_by_id(response_id)
    if resp is None or resp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Disclosure response not found")

    resp = await _recompute_and_save(resp, session)
    return _resp_to_detail(resp)


# ── Disclosure Workspace ──────────────────────────────────────────────────────


@router.get("/workspace/{requirement_id}", response_model=DisclosureWorkspaceResponse)
async def disclosure_workspace(
    requirement_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> DisclosureWorkspaceResponse:
    org_id = current_user.organization_id
    req_repo = SQLDisclosureRequirementRepository(session)
    resp_repo = SQLDisclosureResponseRepository(session)
    mapping_repo = SQLRequirementMappingRepository(session)
    gap_repo = SQLComplianceGapRepository(session)
    evidence_repo = SQLEvidenceRepository(session)

    req = await req_repo.get_by_id(requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")

    resp = await resp_repo.get_for_requirement(org_id, requirement_id)

    # Compliance gaps linked to this disclosure requirement
    # Match by requirement reference code against regulation requirement codes
    gaps = await gap_repo.list_for_org(org_id, requirement_id=None)
    # Filter to gaps whose requirement code starts with the disclosure ref prefix
    ref_prefix = req.reference.split("-")[0] if req.reference else ""
    open_gaps: list[LinkedEntitySummary] = []
    for gap in gaps:
        open_gaps.append(LinkedEntitySummary(
            id=gap.id,
            entity_type="compliance_gap",
            title=gap.description[:80] if gap.description else gap.gap_type,
            severity=gap.severity,
        ))

    # Requirement mappings for this org (for coverage purposes)
    mappings = await mapping_repo.list_for_org(org_id)
    mapping_confidences = [m.confidence for m in mappings]

    # Evidence linked to the org
    evidences = await evidence_repo.list_for_org(org_id, limit=200)
    evidence_items = [
        {"reliability_score": e.reliability_score, "evidence_type": e.evidence_type}
        for e in evidences
    ]

    coverage_result = compute_coverage(
        evidence_items=evidence_items,
        mapping_confidences=mapping_confidences,
    )

    # Linked findings from mappings
    finding_ids = {m.entity_id for m in mappings if m.entity_type == "finding"}
    risk_ids = {m.entity_id for m in mappings if m.entity_type == "risk"}

    linked_findings: list[LinkedEntitySummary] = []
    if finding_ids:
        from sqlalchemy import select as _select  # noqa: PLC0415
        from infrastructure.persistence.models.finding import FindingModel as _FM  # noqa: PLC0415
        rows = (await session.execute(
            _select(_FM).where(_FM.id.in_(finding_ids), _FM.organization_id == org_id)
        )).scalars().all()
        linked_findings = [
            LinkedEntitySummary(id=r.id, entity_type="finding", title=r.title, severity=r.severity, status=r.status)
            for r in rows
        ]

    linked_risks: list[LinkedEntitySummary] = []
    if risk_ids:
        from sqlalchemy import select as _select  # noqa: PLC0415
        from infrastructure.persistence.models.risk import RiskModel as _RM  # noqa: PLC0415
        rows = (await session.execute(
            _select(_RM).where(_RM.id.in_(risk_ids), _RM.organization_id == org_id)
        )).scalars().all()
        linked_risks = [
            LinkedEntitySummary(id=r.id, entity_type="risk", title=r.title, severity=r.severity, status=r.status)
            for r in rows
        ]

    linked_evidence = [
        LinkedEntitySummary(
            id=e.id,
            entity_type="evidence",
            title=e.title,
            status=e.status.value if hasattr(e.status, "value") else str(e.status),
        )
        for e in evidences[:20]
    ]

    return DisclosureWorkspaceResponse(
        requirement=_req_to_schema(req),
        response=_resp_to_detail(resp) if resp else None,
        linked_findings=linked_findings,
        linked_risks=linked_risks,
        linked_evidence=linked_evidence,
        open_compliance_gaps=open_gaps[:20],
        coverage_factors=coverage_result.factors,
    )


# ── Supplier Disclosure Contribution ─────────────────────────────────────────


@router.get(
    "/suppliers/{supplier_id}/contribution",
    response_model=SupplierDisclosureContribution,
)
async def supplier_disclosure_contribution(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> SupplierDisclosureContribution:
    org_id = current_user.organization_id

    supplier_row = (await session.execute(
        select(SupplierModel).where(
            SupplierModel.id == supplier_id,
            SupplierModel.organization_id == org_id,
        )
    )).scalar_one_or_none()
    if supplier_row is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    mapping_repo = SQLRequirementMappingRepository(session)
    gap_repo = SQLComplianceGapRepository(session)

    supplier_mappings = await mapping_repo.list_for_org(org_id, supplier_id=supplier_id)
    evidence_count = len({m.entity_id for m in supplier_mappings if m.entity_type == "evidence"})
    req_ids_impacted = {m.regulation_requirement_id for m in supplier_mappings}

    supplier_gaps = await gap_repo.list_for_org(org_id, supplier_id=supplier_id)
    open_gaps = len([g for g in supplier_gaps if not g.is_resolved])

    readiness_impact = "Low" if open_gaps == 0 else "High" if open_gaps >= 3 else "Medium"

    return SupplierDisclosureContribution(
        supplier_id=supplier_id,
        supplier_name=supplier_row.name,
        disclosures_impacted=len(req_ids_impacted),
        evidence_contributed=evidence_count,
        open_compliance_gaps=open_gaps,
        readiness_impact=readiness_impact,
    )


# ── Assessment Disclosure Mapping ─────────────────────────────────────────────


@router.get(
    "/assessments/{assessment_id}/disclosures",
    response_model=AssessmentDisclosureMapping,
)
async def assessment_disclosure_mapping(
    assessment_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> AssessmentDisclosureMapping:
    org_id = current_user.organization_id

    assessment_row = (await session.execute(
        select(AssessmentModel).where(
            AssessmentModel.id == assessment_id,
            AssessmentModel.organization_id == org_id,
        )
    )).scalar_one_or_none()
    if assessment_row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    mapping_repo = SQLRequirementMappingRepository(session)
    req_repo = SQLDisclosureRequirementRepository(session)
    gap_repo = SQLComplianceGapRepository(session)

    assessment_mappings = await mapping_repo.list_for_org(org_id, assessment_id=assessment_id)
    mapped_reg_req_ids = {m.regulation_requirement_id for m in assessment_mappings}

    # Find disclosure requirements whose reference matches regulation requirement codes
    # by checking all disclosure frameworks' requirements
    fw_repo = SQLDisclosureFrameworkRepository(session)
    frameworks = await fw_repo.list_active()
    matched_requirements = []
    for fw in frameworks:
        reqs = await req_repo.list_for_framework(fw.id)
        for req in reqs:
            matched_requirements.append(req)

    avg_confidence = (
        sum(m.confidence for m in assessment_mappings) / len(assessment_mappings)
        if assessment_mappings else 0.0
    )

    gaps = await gap_repo.list_for_org(org_id, severity="Critical")
    critical_blockers = len(gaps)

    return AssessmentDisclosureMapping(
        assessment_id=assessment_id,
        assessment_title=assessment_row.title,
        disclosure_requirements_impacted=[_req_to_schema(r) for r in matched_requirements[:10]],
        coverage_contribution=round(avg_confidence, 4),
        unresolved_blockers=critical_blockers,
    )


# ── Reporting Packages ────────────────────────────────────────────────────────


@router.get("/packages", response_model=list[ReportingPackageSummary])
async def list_packages(
    framework_code: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> list[ReportingPackageSummary]:
    pkg_repo = SQLReportingPackageRepository(session)
    packages = await pkg_repo.list_for_org(
        organization_id=current_user.organization_id,
        framework_code=framework_code,
    )
    return [_pkg_to_summary(p) for p in packages]


@router.post("/packages/generate", response_model=ReportingPackageSummary, status_code=201)
async def generate_package(
    body: GeneratePackageRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_executive),
) -> ReportingPackageSummary:
    org_id = current_user.organization_id
    fw_repo = SQLDisclosureFrameworkRepository(session)
    req_repo = SQLDisclosureRequirementRepository(session)
    resp_repo = SQLDisclosureResponseRepository(session)
    pkg_repo = SQLReportingPackageRepository(session)

    fw = await fw_repo.get_by_code(body.framework_code)
    if fw is None:
        raise HTTPException(status_code=404, detail=f"Framework '{body.framework_code}' not found")

    reqs = await req_repo.list_for_framework(fw.id)
    responses = await resp_repo.list_for_org(org_id, framework_id=fw.id)
    resp_by_req = {r.requirement_id: r for r in responses}

    # Build snapshot
    req_snapshots = []
    for req in reqs:
        resp = resp_by_req.get(req.id)
        req_snapshots.append({
            "requirement_id": req.id,
            "reference": req.reference,
            "title": req.title,
            "category": req.category,
            "disclosure_status": resp.disclosure_status if resp else "Not Started",
            "narrative_text": resp.narrative_text if resp else "",
            "evidence_coverage": resp.evidence_coverage if resp else 0.0,
            "coverage_category": resp.coverage_category if resp else "Weak",
            "readiness_status": resp.readiness_status if resp else "Not Started",
        })

    published_count = sum(1 for r in responses if r.disclosure_status == "Published")
    approved_count = sum(1 for r in responses if r.disclosure_status == "Approved")

    report_data = {
        "meta": {
            "framework_code": fw.code,
            "framework_name": fw.name,
            "fw_version": fw.fw_version,
            "package_type": body.package_type,
            "organization_id": org_id,
            "generated_by": current_user.id,
            "generated_at": datetime.now(UTC).isoformat(),
            "total_requirements": len(reqs),
            "published_count": published_count,
            "approved_count": approved_count,
        },
        "requirements": req_snapshots,
    }

    import json  # noqa: PLC0415
    snapshot_bytes = json.dumps(report_data, sort_keys=True, default=str).encode()
    report_hash = hashlib.sha256(snapshot_bytes).hexdigest()

    pkg = ReportingPackageDomain(
        organization_id=org_id,
        framework_id=fw.id,
        framework_code=fw.code,
        framework_version=fw.fw_version,
        package_type=body.package_type,
        publication_date=datetime.now(UTC),
        published_by=current_user.id,
        report_data=report_data,
        report_hash=report_hash,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    await pkg_repo.save(pkg)

    logger.info(
        "reporting_package_generated",
        org_id=org_id,
        framework_code=fw.code,
        package_id=pkg.id,
        hash=report_hash[:12],
    )
    return _pkg_to_summary(pkg)


@router.get("/packages/{package_id}", response_model=ReportingPackageDetail)
async def get_package(
    package_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> ReportingPackageDetail:
    pkg_repo = SQLReportingPackageRepository(session)
    pkg = await pkg_repo.get_by_id(package_id)
    if pkg is None or pkg.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Reporting package not found")
    return _pkg_to_detail(pkg)


@router.get("/packages/{package_id}/download")
async def download_package(
    package_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
) -> StreamingResponse:
    pkg_repo = SQLReportingPackageRepository(session)
    pkg = await pkg_repo.get_by_id(package_id)
    if pkg is None or pkg.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Reporting package not found")

    from infrastructure.reporting.disclosure_pdf_renderer import render_reporting_package  # noqa: PLC0415

    pdf_bytes = render_reporting_package(
        org_name=current_user.organization_id,
        package=pkg.report_data,
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="reporting-package-{package_id[:8]}.pdf"',
            "X-Package-ID": pkg.id,
            "X-Package-Hash": pkg.report_hash,
            "X-Framework-Version": pkg.framework_version,
        },
    )
