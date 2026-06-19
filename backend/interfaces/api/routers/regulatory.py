"""
M31 Regulatory Intelligence & Compliance Mapping API

Routes:
  GET    /compliance/dashboard                     — org compliance status
  GET    /compliance/regulations                   — list all frameworks
  GET    /compliance/regulations/{code}            — framework detail + requirements
  GET    /compliance/requirements                  — list requirements (filterable)
  POST   /compliance/mappings                      — create requirement mapping
  GET    /compliance/mappings                      — list org's mappings
  DELETE /compliance/mappings/{id}                 — remove a mapping
  POST   /compliance/mappings/auto                 — rule-based auto-map an entity
  GET    /compliance/gaps                          — list org's compliance gaps
  GET    /compliance/gaps/summary                  — gap counts by severity / type / framework
  POST   /compliance/gaps/recalculate              — recompute gaps for the org
  PATCH  /compliance/gaps/{id}/resolve             — mark a gap resolved
  GET    /compliance/suppliers/{supplier_id}       — supplier compliance view
  GET    /compliance/assessments/{assessment_id}   — assessment compliance detail
  GET    /compliance/reports                       — list stored compliance reports
  GET    /compliance/reports/{report_id}/download  — download historical report from snapshot
  GET    /compliance/reports/csrd-gap              — generate CSRD Gap Report PDF
  GET    /compliance/reports/esrs-readiness        — generate ESRS Readiness Report PDF
  GET    /compliance/reports/csddd-due-diligence   — generate CSDDD Due Diligence Report PDF
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

from application.compliance.entity_ownership import resolve_entity_org_id
from application.compliance.gap_engine import compute_gaps
from application.compliance.mapping_engine import auto_map_entity, create_manual_mapping
from application.compliance.org_status import compute_framework_status, compute_org_status
from domain.compliance_report import ComplianceReport
from domain.enums import EntityStatus
from domain.user import User
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.repositories.regulatory import (
    SQLComplianceGapRepository,
    SQLComplianceReportRepository,
    SQLRegulationRepository,
    SQLRegulationRequirementRepository,
    SQLRequirementMappingRepository,
)
from infrastructure.reporting.compliance_pdf_renderer import (
    render_csddd_due_diligence_report,
    render_csrd_gap_report,
    render_esrs_readiness_report,
)
from interfaces.api.deps import (
    get_current_user,
    get_db,
    require_analyst,
    require_executive,
    scope_gate,
)
from interfaces.api.schemas.regulatory import (
    AssessmentComplianceDetailResponse,
    ComplianceDashboardResponse,
    ComplianceGapResponse,
    ComplianceReportResponse,
    ComplianceReportSummary,
    CreateMappingRequest,
    FrameworkStatusResponse,
    GapSummary,
    RegulationRequirementResponse,
    RegulationResponse,
    RequirementMappingResponse,
    SupplierComplianceResponse,
)

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/compliance",
    tags=["regulatory"],
    dependencies=[
        Depends(require_analyst),
        Depends(scope_gate("compliance:read", "compliance:write")),
    ],
)

# Active entity statuses: findings/risks that are still open compliance issues
_OPEN_STATUSES = frozenset({"Active", "Draft", "Created", "Validated", "Reviewed", "Approved"})
_CLOSED_STATUSES = frozenset({"Archived", "Deleted", "Suspended"})


# ── Dependency helpers ────────────────────────────────────────────────────────


def _assert_org(user: User) -> str:
    if not user.organization_id:
        raise HTTPException(status_code=403, detail="No organisation context")
    return user.organization_id


# ── Serialisation helpers ─────────────────────────────────────────────────────


def _req_to_resp(req: object) -> RegulationRequirementResponse:
    return RegulationRequirementResponse(
        id=req.id,
        regulation_id=req.regulation_id,
        code=req.code,
        reference=req.reference,
        title=req.title,
        description=req.description,
        category=req.category,
        pillar=req.pillar,
        severity=req.severity,
        obligation_type=req.obligation_type,
    )


def _mapping_to_resp(
    mapping: object, req_by_id: dict | None = None
) -> RequirementMappingResponse:
    req_by_id = req_by_id or {}
    req = req_by_id.get(mapping.regulation_requirement_id)
    return RequirementMappingResponse(
        id=mapping.id,
        organization_id=mapping.organization_id,
        regulation_requirement_id=mapping.regulation_requirement_id,
        requirement_code=req.code if req else "",
        requirement_title=req.title if req else "",
        entity_type=mapping.entity_type,
        entity_id=mapping.entity_id,
        confidence=mapping.confidence,
        rationale=mapping.rationale,
        mapping_method=mapping.mapping_method,
        mapping_version=mapping.mapping_version,
        regulation_version_at_mapping=mapping.regulation_version_at_mapping,
        mapped_at=mapping.mapped_at.isoformat(),
        supplier_id=mapping.supplier_id,
        assessment_id=mapping.assessment_id,
    )


def _gap_to_resp(gap: object, req_by_id: dict | None = None) -> ComplianceGapResponse:
    req_by_id = req_by_id or {}
    req = req_by_id.get(gap.regulation_requirement_id)
    return ComplianceGapResponse(
        id=gap.id,
        organization_id=gap.organization_id,
        regulation_requirement_id=gap.regulation_requirement_id,
        requirement_code=req.code if req else "",
        requirement_title=req.title if req else "",
        supplier_id=gap.supplier_id,
        gap_type=gap.gap_type,
        severity=gap.severity,
        description=gap.description,
        source_entity_type=gap.source_entity_type,
        source_entity_id=gap.source_entity_id,
        calculated_at=gap.calculated_at.isoformat(),
        calculation_version=gap.calculation_version,
        regulation_version_at_calculation=gap.regulation_version_at_calculation,
        is_resolved=gap.is_resolved,
    )


def _fw_status_to_resp(fs: object) -> FrameworkStatusResponse:
    return FrameworkStatusResponse(
        regulation_code=fs.regulation_code,
        regulation_name=fs.regulation_name,
        status=fs.status,
        total_requirements=fs.total_requirements,
        covered_requirements=fs.covered_requirements,
        coverage_ratio=fs.coverage_ratio,
        open_gap_count=fs.open_gap_count,
        critical_gap_count=fs.critical_gap_count,
        high_gap_count=fs.high_gap_count,
        medium_gap_count=fs.medium_gap_count,
        low_gap_count=fs.low_gap_count,
        explanation=fs.explanation,
        top_gap_requirement_codes=fs.top_gap_requirement_codes,
    )


def _report_to_summary(report: object) -> ComplianceReportSummary:
    return ComplianceReportSummary(
        id=report.id,
        organization_id=report.organization_id,
        report_type=report.report_type,
        framework_code=report.framework_code,
        framework_version=report.framework_version,
        generated_at=report.generated_at.isoformat(),
        generated_by=report.generated_by,
        report_hash=report.report_hash,
    )


# ── Regulations ───────────────────────────────────────────────────────────────


@router.get("/regulations", response_model=list[RegulationResponse])
async def list_regulations(
    session: AsyncSession = Depends(get_db),
) -> list[RegulationResponse]:
    """List all active regulatory frameworks with requirement counts."""
    reg_repo = SQLRegulationRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)

    regulations = await reg_repo.list_active()
    all_reqs = await req_repo.list_all_active()
    req_counts: dict[str, int] = {}
    for r in all_reqs:
        req_counts[r.regulation_id] = req_counts.get(r.regulation_id, 0) + 1

    return [
        RegulationResponse(
            id=reg.id,
            code=reg.code,
            name=reg.name,
            jurisdiction=reg.jurisdiction,
            reg_version=reg.reg_version,
            reg_status=reg.reg_status,
            description=reg.description,
            requirement_count=req_counts.get(reg.id, 0),
        )
        for reg in regulations
    ]


@router.get("/regulations/{code}", response_model=RegulationResponse)
async def get_regulation(
    code: str,
    session: AsyncSession = Depends(get_db),
) -> RegulationResponse:
    reg_repo = SQLRegulationRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)

    reg = await reg_repo.get_by_code(code.upper())
    if reg is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    reqs = await req_repo.list_for_regulation(reg.id)
    return RegulationResponse(
        id=reg.id,
        code=reg.code,
        name=reg.name,
        jurisdiction=reg.jurisdiction,
        reg_version=reg.reg_version,
        reg_status=reg.reg_status,
        description=reg.description,
        requirement_count=len(reqs),
    )


@router.get("/requirements", response_model=list[RegulationRequirementResponse])
async def list_requirements(
    regulation_code: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    obligation_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[RegulationRequirementResponse]:
    """List regulation requirements, optionally filtered by framework."""
    reg_repo = SQLRegulationRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)

    if regulation_code:
        reg = await reg_repo.get_by_code(regulation_code.upper())
        if reg is None:
            return []
        reqs = await req_repo.list_for_regulation(reg.id)
    else:
        reqs = await req_repo.list_all_active()

    if category:
        reqs = [r for r in reqs if r.category.lower() == category.lower()]
    if severity:
        reqs = [r for r in reqs if r.severity.lower() == severity.lower()]
    if obligation_type:
        reqs = [r for r in reqs if r.obligation_type.lower() == obligation_type.lower()]

    return [_req_to_resp(r) for r in reqs]


# ── Requirement Mappings ──────────────────────────────────────────────────────


@router.post("/mappings", response_model=RequirementMappingResponse, status_code=201)
async def create_mapping(
    body: CreateMappingRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RequirementMappingResponse:
    """Manually map a Finding, Risk, or Recommendation to a regulation requirement."""
    org_id = _assert_org(current_user)

    req_repo = SQLRegulationRequirementRepository(session)
    reg_repo = SQLRegulationRepository(session)
    mapping_repo = SQLRequirementMappingRepository(session)

    req = await req_repo.get_by_id(body.regulation_requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")

    # ── M31.1: Entity ownership validation ───────────────────────────────────
    entity_org_id = await resolve_entity_org_id(session, body.entity_type, body.entity_id)
    if entity_org_id is None or entity_org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail=(
                "Entity ownership could not be verified for this organisation. "
                "Ensure the entity exists and belongs to your organisation."
            ),
        )

    # Idempotency: don't create duplicate mappings
    if await mapping_repo.exists(
        organization_id=org_id,
        regulation_requirement_id=body.regulation_requirement_id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
    ):
        raise HTTPException(
            status_code=409,
            detail="A mapping from this entity to this requirement already exists.",
        )

    # Capture current regulation version for traceability
    regulation = await reg_repo.get_by_id(req.regulation_id)
    reg_version = regulation.reg_version if regulation else "1.0"

    mapping = create_manual_mapping(
        organization_id=org_id,
        regulation_requirement_id=body.regulation_requirement_id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        rationale=body.rationale,
        confidence=body.confidence,
        supplier_id=body.supplier_id,
        assessment_id=body.assessment_id,
        created_by=current_user.id,
        regulation_version=reg_version,
    )
    saved = await mapping_repo.save(mapping)
    log.info(
        "requirement_mapping_created",
        mapping_id=saved.id,
        entity_type=body.entity_type,
        org_id=org_id,
        regulation_version=reg_version,
    )
    return _mapping_to_resp(saved, {req.id: req})


@router.get("/mappings", response_model=list[RequirementMappingResponse])
async def list_mappings(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    requirement_id: str | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    assessment_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[RequirementMappingResponse]:
    org_id = _assert_org(current_user)
    mapping_repo = SQLRequirementMappingRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)

    mappings = await mapping_repo.list_for_org(
        organization_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        requirement_id=requirement_id,
        supplier_id=supplier_id,
        assessment_id=assessment_id,
    )
    req_ids = {m.regulation_requirement_id for m in mappings}
    req_by_id: dict = {}
    for rid in req_ids:
        r = await req_repo.get_by_id(rid)
        if r:
            req_by_id[rid] = r
    return [_mapping_to_resp(m, req_by_id) for m in mappings]


@router.delete("/mappings/{mapping_id}", status_code=204)
async def delete_mapping(
    mapping_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    org_id = _assert_org(current_user)
    mapping_repo = SQLRequirementMappingRepository(session)

    mapping = await mapping_repo.get_by_id(mapping_id)
    if mapping is None or mapping.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Mapping not found")
    await mapping_repo.delete(mapping_id)


@router.post("/mappings/auto", response_model=list[RequirementMappingResponse], status_code=201)
async def auto_map(
    entity_type: str = Query(..., pattern="^(finding|risk|recommendation)$"),
    entity_id: str = Query(...),
    entity_text: str = Query(..., max_length=4000),
    supplier_id: str | None = Query(default=None),
    assessment_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[RequirementMappingResponse]:
    """Rule-based auto-mapping: scan entity text against all requirement keywords."""
    org_id = _assert_org(current_user)

    req_repo = SQLRegulationRequirementRepository(session)
    reg_repo = SQLRegulationRepository(session)
    mapping_repo = SQLRequirementMappingRepository(session)

    # ── M31.1: Entity ownership validation ───────────────────────────────────
    entity_org_id = await resolve_entity_org_id(session, entity_type, entity_id)
    if entity_org_id is None or entity_org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail=(
                "Entity ownership could not be verified for this organisation. "
                "Ensure the entity exists and belongs to your organisation."
            ),
        )

    requirements = await req_repo.list_all_active()

    # Build regulation version map for traceability
    regulations = await reg_repo.list_active()
    reg_version_by_id = {r.id: r.reg_version for r in regulations}

    candidates = auto_map_entity(
        organization_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_text=entity_text,
        requirements=requirements,
        supplier_id=supplier_id,
        assessment_id=assessment_id,
        regulation_version_by_id=reg_version_by_id,
    )

    saved_mappings = []
    req_by_id: dict = {}
    for mapping in candidates:
        already = await mapping_repo.exists(
            organization_id=org_id,
            regulation_requirement_id=mapping.regulation_requirement_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if not already:
            saved = await mapping_repo.save(mapping)
            saved_mappings.append(saved)
            req = await req_repo.get_by_id(mapping.regulation_requirement_id)
            if req:
                req_by_id[req.id] = req

    log.info(
        "auto_mapping_complete",
        entity_type=entity_type,
        entity_id=entity_id,
        org_id=org_id,
        new_mappings=len(saved_mappings),
    )
    return [_mapping_to_resp(m, req_by_id) for m in saved_mappings]


# ── Compliance Gaps ───────────────────────────────────────────────────────────


@router.get("/gaps", response_model=list[ComplianceGapResponse])
async def list_gaps(
    supplier_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    gap_type: str | None = Query(default=None),
    requirement_id: str | None = Query(default=None),
    include_resolved: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ComplianceGapResponse]:
    org_id = _assert_org(current_user)
    gap_repo = SQLComplianceGapRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)

    gaps = await gap_repo.list_for_org(
        organization_id=org_id,
        supplier_id=supplier_id,
        severity=severity,
        gap_type=gap_type,
        requirement_id=requirement_id,
        include_resolved=include_resolved,
        limit=limit,
    )
    req_ids = {g.regulation_requirement_id for g in gaps}
    req_by_id: dict = {}
    for rid in req_ids:
        r = await req_repo.get_by_id(rid)
        if r:
            req_by_id[rid] = r
    return [_gap_to_resp(g, req_by_id) for g in gaps]


@router.get("/gaps/summary", response_model=GapSummary)
async def get_gap_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GapSummary:
    org_id = _assert_org(current_user)
    gap_repo = SQLComplianceGapRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)

    gaps = await gap_repo.list_for_org(organization_id=org_id, include_resolved=False, limit=500)

    req_ids = {g.regulation_requirement_id for g in gaps}
    req_by_id: dict = {}
    for rid in req_ids:
        r = await req_repo.get_by_id(rid)
        if r:
            req_by_id[rid] = r

    by_gap_type: dict[str, int] = {}
    by_framework: dict[str, int] = {}
    for g in gaps:
        by_gap_type[g.gap_type] = by_gap_type.get(g.gap_type, 0) + 1
        req = req_by_id.get(g.regulation_requirement_id)
        if req:
            fw = req.code.split("-")[0]
            by_framework[fw] = by_framework.get(fw, 0) + 1

    return GapSummary(
        total=len(gaps),
        critical=sum(1 for g in gaps if g.severity == "Critical"),
        high=sum(1 for g in gaps if g.severity == "High"),
        medium=sum(1 for g in gaps if g.severity == "Medium"),
        low=sum(1 for g in gaps if g.severity == "Low"),
        by_gap_type=by_gap_type,
        by_framework=by_framework,
    )


@router.post("/gaps/recalculate", status_code=202)
async def recalculate_gaps(
    current_user: User = Depends(require_executive),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Recompute compliance gaps for the organisation.

    Rebuilds all gap types (missing_evidence, missing_disclosure,
    unresolved_finding, missing_control).  Resolved gaps are preserved.
    """
    org_id = _assert_org(current_user)

    req_repo = SQLRegulationRequirementRepository(session)
    reg_repo = SQLRegulationRepository(session)
    mapping_repo = SQLRequirementMappingRepository(session)
    gap_repo = SQLComplianceGapRepository(session)

    requirements = await req_repo.list_all_active()
    covered_ids = await mapping_repo.get_covered_requirement_ids(org_id)

    # ── Build regulation version map ──────────────────────────────────────────
    regulations = await reg_repo.list_active()
    regulation_versions = {r.id: r.reg_version for r in regulations}

    # ── Build open entity dictionaries ────────────────────────────────────────
    # Get finding-type and risk-type mappings for this org
    finding_mappings = await mapping_repo.list_for_org(
        organization_id=org_id, entity_type="finding"
    )
    risk_mappings = await mapping_repo.list_for_org(
        organization_id=org_id, entity_type="risk"
    )

    # Group entity_ids by requirement
    req_to_finding_ids: dict[str, list[str]] = {}
    for m in finding_mappings:
        req_to_finding_ids.setdefault(m.regulation_requirement_id, []).append(m.entity_id)

    req_to_risk_ids: dict[str, list[str]] = {}
    for m in risk_mappings:
        req_to_risk_ids.setdefault(m.regulation_requirement_id, []).append(m.entity_id)

    # Batch-load open findings (not Archived or Deleted)
    open_finding_by_requirement: dict[str, list[dict]] = {}
    all_finding_ids = {fid for ids in req_to_finding_ids.values() for fid in ids}
    if all_finding_ids:
        finding_rows = (
            await session.execute(
                select(FindingModel).where(
                    FindingModel.id.in_(all_finding_ids),
                    FindingModel.status.notin_(list(_CLOSED_STATUSES)),
                )
            )
        ).scalars().all()
        open_by_id = {f.id: f for f in finding_rows}
        for req_id, fids in req_to_finding_ids.items():
            entries = []
            for fid in fids:
                f = open_by_id.get(fid)
                if f:
                    entries.append({
                        "id": f.id,
                        "severity": f.severity,
                        "description": (f.description or "")[:200],
                    })
            if entries:
                open_finding_by_requirement[req_id] = entries

    # Batch-load open risks (not Archived or Deleted)
    open_risk_by_requirement: dict[str, list[dict]] = {}
    all_risk_ids = {rid for ids in req_to_risk_ids.values() for rid in ids}
    if all_risk_ids:
        risk_rows = (
            await session.execute(
                select(RiskModel).where(
                    RiskModel.id.in_(all_risk_ids),
                    RiskModel.status.notin_(list(_CLOSED_STATUSES)),
                )
            )
        ).scalars().all()
        open_risks_by_id = {r.id: r for r in risk_rows}
        for req_id, rids in req_to_risk_ids.items():
            entries = []
            for rid in rids:
                r = open_risks_by_id.get(rid)
                if r:
                    entries.append({
                        "id": r.id,
                        "severity": r.risk_level,
                        "description": (r.description or "")[:200],
                    })
            if entries:
                open_risk_by_requirement[req_id] = entries

    new_gaps = compute_gaps(
        requirements=requirements,
        covered_requirement_ids=covered_ids,
        open_finding_by_requirement=open_finding_by_requirement,
        open_risk_by_requirement=open_risk_by_requirement,
        organization_id=org_id,
        regulation_versions=regulation_versions,
    )

    deleted = await gap_repo.delete_unresolved_for_org(org_id)
    for gap in new_gaps:
        await gap_repo.save(gap)

    log.info(
        "gaps_recalculated",
        org_id=org_id,
        deleted=deleted,
        created=len(new_gaps),
        finding_gaps=sum(1 for g in new_gaps if g.gap_type == "unresolved_finding"),
        risk_gaps=sum(1 for g in new_gaps if g.gap_type == "missing_control"),
    )
    return {
        "status": "recalculated",
        "gaps_deleted": deleted,
        "gaps_created": len(new_gaps),
    }


@router.patch("/gaps/{gap_id}/resolve", response_model=ComplianceGapResponse)
async def resolve_gap(
    gap_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComplianceGapResponse:
    org_id = _assert_org(current_user)
    gap_repo = SQLComplianceGapRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)

    gap = await gap_repo.get_by_id(gap_id)
    if gap is None or gap.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Gap not found")
    if gap.is_resolved:
        raise HTTPException(status_code=409, detail="Gap is already resolved")

    gap.is_resolved = True
    gap.resolved_at = datetime.now(UTC)
    gap.resolved_by = current_user.id
    saved = await gap_repo.save(gap)

    req_by_id: dict = {}
    r = await req_repo.get_by_id(saved.regulation_requirement_id)
    if r:
        req_by_id[r.id] = r
    return _gap_to_resp(saved, req_by_id)


# ── Compliance Dashboard ──────────────────────────────────────────────────────


@router.get("/dashboard", response_model=ComplianceDashboardResponse)
async def get_compliance_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComplianceDashboardResponse:
    """Organisation-wide compliance status across all frameworks."""
    org_id = _assert_org(current_user)

    reg_repo = SQLRegulationRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)
    mapping_repo = SQLRequirementMappingRepository(session)
    gap_repo = SQLComplianceGapRepository(session)

    regulations = await reg_repo.list_active()
    covered_ids = await mapping_repo.get_covered_requirement_ids(org_id)
    open_gaps = await gap_repo.list_for_org(
        organization_id=org_id, include_resolved=False, limit=500
    )

    requirements_by_regulation: dict[str, tuple[str, list]] = {}
    for reg in regulations:
        reqs = await req_repo.list_for_regulation(reg.id)
        requirements_by_regulation[reg.id] = (reg.code, reqs)

    org_status = compute_org_status(
        organization_id=org_id,
        requirements_by_regulation=requirements_by_regulation,
        covered_ids=covered_ids,
        open_gaps=open_gaps,
    )

    return ComplianceDashboardResponse(
        organization_id=org_id,
        overall_coverage_ratio=org_status.overall_coverage_ratio,
        total_open_gaps=org_status.total_open_gaps,
        total_critical_gaps=org_status.total_critical_gaps,
        frameworks=[_fw_status_to_resp(f) for f in org_status.frameworks],
    )


# ── Supplier Compliance View ──────────────────────────────────────────────────


@router.get("/suppliers/{supplier_id}", response_model=SupplierComplianceResponse)
async def get_supplier_compliance(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupplierComplianceResponse:
    org_id = _assert_org(current_user)

    reg_repo = SQLRegulationRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)
    mapping_repo = SQLRequirementMappingRepository(session)
    gap_repo = SQLComplianceGapRepository(session)

    mappings = await mapping_repo.list_for_org(
        organization_id=org_id, supplier_id=supplier_id
    )
    gaps = await gap_repo.list_for_org(
        organization_id=org_id, supplier_id=supplier_id, include_resolved=False
    )

    req_ids = {m.regulation_requirement_id for m in mappings} | {
        g.regulation_requirement_id for g in gaps
    }
    req_by_id: dict = {}
    for rid in req_ids:
        r = await req_repo.get_by_id(rid)
        if r:
            req_by_id[rid] = r

    covered_ids = {m.regulation_requirement_id for m in mappings}
    regulations = await reg_repo.list_active()
    fw_statuses = []
    for reg in regulations:
        reqs = await req_repo.list_for_regulation(reg.id)
        if not reqs:
            continue
        supplier_gaps = [g for g in gaps if g.regulation_requirement_id in {r.id for r in reqs}]
        fs = compute_framework_status(
            regulation_code=reg.code,
            regulation_name=reg.name,
            requirements=reqs,
            covered_ids=covered_ids,
            open_gaps=supplier_gaps,
        )
        fw_statuses.append(_fw_status_to_resp(fs))

    return SupplierComplianceResponse(
        supplier_id=supplier_id,
        mappings=[_mapping_to_resp(m, req_by_id) for m in mappings],
        gaps=[_gap_to_resp(g, req_by_id) for g in gaps],
        framework_statuses=fw_statuses,
        total_mappings=len(mappings),
        total_open_gaps=len(gaps),
    )


# ── Assessment Compliance Detail ──────────────────────────────────────────────


@router.get("/assessments/{assessment_id}", response_model=AssessmentComplianceDetailResponse)
async def get_assessment_compliance_detail(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AssessmentComplianceDetailResponse:
    org_id = _assert_org(current_user)

    reg_repo = SQLRegulationRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)
    mapping_repo = SQLRequirementMappingRepository(session)

    mappings = await mapping_repo.list_for_org(
        organization_id=org_id, assessment_id=assessment_id
    )

    req_ids = {m.regulation_requirement_id for m in mappings}
    req_by_id: dict = {}
    for rid in req_ids:
        r = await req_repo.get_by_id(rid)
        if r:
            req_by_id[rid] = r

    all_reqs = await req_repo.list_all_active()
    covered_ids = {m.regulation_requirement_id for m in mappings}
    coverage_ratio = len(covered_ids) / len(all_reqs) if all_reqs else 0.0

    regulations = await reg_repo.list_active()
    fw_coverage = []
    for reg in regulations:
        reqs = await req_repo.list_for_regulation(reg.id)
        if not reqs:
            continue
        req_id_set = {r.id for r in reqs}
        covered_in_fw = len(req_id_set & covered_ids)
        fw_coverage.append({
            "framework": reg.code,
            "total": len(reqs),
            "covered": covered_in_fw,
            "ratio": covered_in_fw / len(reqs),
        })

    return AssessmentComplianceDetailResponse(
        assessment_id=assessment_id,
        mappings=[_mapping_to_resp(m, req_by_id) for m in mappings],
        covered_requirement_codes=[req_by_id[rid].code for rid in covered_ids if rid in req_by_id],
        coverage_ratio=coverage_ratio,
        framework_coverage=fw_coverage,
    )


# ── Compliance PDF Reports ────────────────────────────────────────────────────


async def _build_report_snapshot(
    org_id: str,
    session: AsyncSession,
) -> tuple[list[dict], list[dict], dict[str, str]]:
    """Return (fw_dicts, gap_dicts, framework_versions) from current DB state."""
    reg_repo = SQLRegulationRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)
    mapping_repo = SQLRequirementMappingRepository(session)
    gap_repo = SQLComplianceGapRepository(session)

    regulations = await reg_repo.list_active()
    covered_ids = await mapping_repo.get_covered_requirement_ids(org_id)
    open_gaps = await gap_repo.list_for_org(
        organization_id=org_id, include_resolved=False, limit=500
    )

    req_by_id: dict = {}
    fw_dicts: list[dict] = []
    framework_versions: dict[str, str] = {}

    for reg in regulations:
        reqs = await req_repo.list_for_regulation(reg.id)
        for r in reqs:
            req_by_id[r.id] = r
        fw_gaps = [g for g in open_gaps if g.regulation_requirement_id in {r.id for r in reqs}]
        fs = compute_framework_status(
            regulation_code=reg.code,
            regulation_name=reg.name,
            requirements=reqs,
            covered_ids=covered_ids,
            open_gaps=fw_gaps,
        )
        fw_dicts.append({
            "regulation_code": fs.regulation_code,
            "regulation_name": fs.regulation_name,
            "status": fs.status,
            "total_requirements": fs.total_requirements,
            "covered_requirements": fs.covered_requirements,
            "coverage_ratio": fs.coverage_ratio,
            "open_gap_count": fs.open_gap_count,
            "critical_gap_count": fs.critical_gap_count,
        })
        framework_versions[reg.code] = reg.reg_version

    gap_dicts: list[dict] = []
    for g in open_gaps:
        req = req_by_id.get(g.regulation_requirement_id)
        gap_dicts.append({
            "requirement_code": req.code if req else "",
            "requirement_title": req.title if req else "",
            "gap_type": g.gap_type,
            "severity": g.severity,
            "description": g.description,
        })

    return fw_dicts, gap_dicts, framework_versions


async def _persist_report(
    *,
    session: AsyncSession,
    org_id: str,
    report_type: str,
    framework_code: str,
    framework_versions: dict[str, str],
    fw_dicts: list[dict],
    gap_dicts: list[dict],
    pdf_bytes: bytes,
    generated_by: str,
) -> ComplianceReport:
    """Freeze report snapshot and persist it.  Returns the saved ComplianceReport."""
    report_repo = SQLComplianceReportRepository(session)
    report_hash = hashlib.sha256(pdf_bytes).hexdigest()
    fw_version = framework_versions.get(framework_code, "1.0")

    report = ComplianceReport(
        organization_id=org_id,
        report_type=report_type,
        framework_code=framework_code,
        framework_version=fw_version,
        generated_at=datetime.now(UTC),
        generated_by=generated_by,
        report_data={
            "meta": {
                "report_type": report_type,
                "org_id": org_id,
                "generated_by": generated_by,
                "framework_code": framework_code,
                "framework_versions": framework_versions,
            },
            "frameworks": fw_dicts,
            "gaps": gap_dicts,
        },
        report_hash=report_hash,
        status=EntityStatus.ACTIVE,
    )
    return await report_repo.save(report)


# ── Stored report history & download ─────────────────────────────────────────


@router.get("/reports", response_model=list[ComplianceReportSummary])
async def list_compliance_reports(
    report_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ComplianceReportSummary]:
    """List previously generated compliance reports for this organisation."""
    org_id = _assert_org(current_user)
    report_repo = SQLComplianceReportRepository(session)
    reports = await report_repo.list_for_org(
        organization_id=org_id, report_type=report_type, limit=limit
    )
    return [_report_to_summary(r) for r in reports]


@router.get("/reports/{report_id}", response_model=ComplianceReportResponse)
async def get_compliance_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComplianceReportResponse:
    """Retrieve a stored compliance report with its full snapshot."""
    org_id = _assert_org(current_user)
    report_repo = SQLComplianceReportRepository(session)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return ComplianceReportResponse(
        id=report.id,
        organization_id=report.organization_id,
        report_type=report.report_type,
        framework_code=report.framework_code,
        framework_version=report.framework_version,
        generated_at=report.generated_at.isoformat(),
        generated_by=report.generated_by,
        report_hash=report.report_hash,
        report_data=report.report_data,
    )


@router.get("/reports/{report_id}/download")
async def download_historical_report(
    report_id: str,
    current_user: User = Depends(require_executive),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Render and download a previously generated report from its frozen snapshot.

    The PDF is always rendered from the stored report_data, never from live DB
    state.  This guarantees reproducibility regardless of subsequent changes to
    mappings, gaps, or framework metadata.
    """
    org_id = _assert_org(current_user)
    report_repo = SQLComplianceReportRepository(session)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Report not found")

    fw_dicts = report.report_data.get("frameworks", [])
    gap_dicts = report.report_data.get("gaps", [])
    org_name = report.report_data.get("meta", {}).get("org_id", org_id)

    _renderers = {
        "csrd_gap": render_csrd_gap_report,
        "esrs_readiness": render_esrs_readiness_report,
        "csddd_due_diligence": render_csddd_due_diligence_report,
    }
    renderer = _renderers.get(report.report_type)
    if renderer is None:
        raise HTTPException(status_code=422, detail="Unknown report type in stored record")

    pdf_bytes = renderer(org_name=org_name, frameworks=fw_dicts, gaps=gap_dicts)

    filename = f"{report.report_type}-{report_id[:8]}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-ID": report_id,
            "X-Report-Hash": report.report_hash,
            "X-Framework-Version": report.framework_version,
        },
    )


# ── Report generation endpoints ───────────────────────────────────────────────


@router.get("/reports/csrd-gap")
async def download_csrd_gap_report(
    current_user: User = Depends(require_executive),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    org_id = _assert_org(current_user)
    fw_dicts, gap_dicts, framework_versions = await _build_report_snapshot(org_id, session)

    pdf_bytes = render_csrd_gap_report(
        org_name=org_id,
        frameworks=fw_dicts,
        gaps=gap_dicts,
    )
    saved = await _persist_report(
        session=session,
        org_id=org_id,
        report_type="csrd_gap",
        framework_code="CSRD",
        framework_versions=framework_versions,
        fw_dicts=fw_dicts,
        gap_dicts=gap_dicts,
        pdf_bytes=pdf_bytes,
        generated_by=current_user.id,
    )
    log.info("compliance_report_generated", report_id=saved.id, report_type="csrd_gap", org_id=org_id)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="csrd-gap-report.pdf"',
            "X-Report-ID": saved.id,
            "X-Report-Hash": saved.report_hash,
        },
    )


@router.get("/reports/esrs-readiness")
async def download_esrs_readiness_report(
    current_user: User = Depends(require_executive),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    org_id = _assert_org(current_user)
    fw_dicts, gap_dicts, framework_versions = await _build_report_snapshot(org_id, session)

    pdf_bytes = render_esrs_readiness_report(
        org_name=org_id,
        frameworks=fw_dicts,
        gaps=gap_dicts,
    )
    saved = await _persist_report(
        session=session,
        org_id=org_id,
        report_type="esrs_readiness",
        framework_code="ESRS",
        framework_versions=framework_versions,
        fw_dicts=fw_dicts,
        gap_dicts=gap_dicts,
        pdf_bytes=pdf_bytes,
        generated_by=current_user.id,
    )
    log.info("compliance_report_generated", report_id=saved.id, report_type="esrs_readiness", org_id=org_id)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="esrs-readiness-report.pdf"',
            "X-Report-ID": saved.id,
            "X-Report-Hash": saved.report_hash,
        },
    )


@router.get("/reports/csddd-due-diligence")
async def download_csddd_report(
    current_user: User = Depends(require_executive),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    org_id = _assert_org(current_user)
    fw_dicts, gap_dicts, framework_versions = await _build_report_snapshot(org_id, session)

    pdf_bytes = render_csddd_due_diligence_report(
        org_name=org_id,
        frameworks=fw_dicts,
        gaps=gap_dicts,
    )
    saved = await _persist_report(
        session=session,
        org_id=org_id,
        report_type="csddd_due_diligence",
        framework_code="CSDDD",
        framework_versions=framework_versions,
        fw_dicts=fw_dicts,
        gap_dicts=gap_dicts,
        pdf_bytes=pdf_bytes,
        generated_by=current_user.id,
    )
    log.info("compliance_report_generated", report_id=saved.id, report_type="csddd_due_diligence", org_id=org_id)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="csddd-due-diligence-report.pdf"',
            "X-Report-ID": saved.id,
            "X-Report-Hash": saved.report_hash,
        },
    )
