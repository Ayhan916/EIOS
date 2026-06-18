"""
M27 Suppliers API

Supplier is the primary subject of ESG due diligence in EIOS.
All endpoints enforce tenant isolation — users only see their own org's suppliers.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import application.audit as audit_events
from domain.enums import EntityStatus, SupplierStatus, SupplierTier
from domain.supplier import Supplier
from domain.user import User
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLSupplierRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_audit_event_repo,
    get_current_user,
    get_db,
    get_supplier_repo,
    require_analyst,
    require_admin,
)
from interfaces.api.schemas.pagination import Page, PaginationParams
from interfaces.api.schemas.supplier import (
    SupplierCreate,
    SupplierResponse,
    SupplierRiskProfile,
    SupplierUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[Depends(get_current_user)],
)


def _assert_org_access(supplier_org_id: str, user_org_id: str | None) -> None:
    if user_org_id is None or supplier_org_id != user_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")


# ── CRUD ──────────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_supplier(
    body: SupplierCreate,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> SupplierResponse:
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    # Application-layer uniqueness guard (DB constraint is the safety net for races)
    existing = await supplier_repo.get_by_name_and_org(body.name, current_user.organization_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A supplier named '{body.name}' already exists in this organization.",
        )

    supplier = Supplier(
        organization_id=current_user.organization_id,
        name=body.name,
        legal_name=body.legal_name,
        country=body.country,
        industry=body.industry,
        nace_code=body.nace_code,
        website=body.website,
        supplier_tier=body.supplier_tier,
        supplier_status=SupplierStatus.ACTIVE,
        notes=body.notes,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    try:
        saved = await supplier_repo.save(supplier)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A supplier named '{body.name}' already exists in this organization.",
        )
    await audit_repo.save(
        audit_events.supplier_created(
            supplier_id=saved.id,
            supplier_name=saved.name,
            actor_id=current_user.id,
            actor_email=current_user.email,
            organization_id=current_user.organization_id,
        )
    )
    logger.info("supplier_created", supplier_id=saved.id, name=saved.name)
    return SupplierResponse.model_validate(saved)


@router.get("/", response_model=Page[SupplierResponse])
async def list_suppliers(
    pagination: PaginationParams = Depends(),
    filter_status: str | None = Query(default=None, alias="status"),
    country: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    supplier_tier: str | None = Query(default=None),
    search: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
) -> Page[SupplierResponse]:
    if not current_user.organization_id:
        return Page(items=[], total=0, page=pagination.page, page_size=pagination.page_size)
    items, total = await supplier_repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=filter_status,
        country=country,
        industry=industry,
        supplier_tier=supplier_tier,
        search=search,
    )
    return Page(
        items=[SupplierResponse.model_validate(s) for s in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
) -> SupplierResponse:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)
    return SupplierResponse.model_validate(supplier)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    body: SupplierUpdate,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> SupplierResponse:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    changes: dict = {}
    if body.name is not None and body.name != supplier.name:
        existing = await supplier_repo.get_by_name_and_org(body.name, current_user.organization_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"A supplier named '{body.name}' already exists in this organization.",
            )
        changes["name"] = body.name
        supplier.name = body.name
    if body.legal_name is not None:
        changes["legal_name"] = body.legal_name
        supplier.legal_name = body.legal_name
    if body.country is not None:
        changes["country"] = body.country
        supplier.country = body.country
    if body.industry is not None:
        changes["industry"] = body.industry
        supplier.industry = body.industry
    if body.nace_code is not None:
        changes["nace_code"] = body.nace_code
        supplier.nace_code = body.nace_code
    if body.website is not None:
        changes["website"] = body.website
        supplier.website = body.website
    if body.supplier_tier is not None:
        changes["supplier_tier"] = body.supplier_tier.value
        supplier.supplier_tier = body.supplier_tier
    if body.supplier_status is not None:
        changes["supplier_status"] = body.supplier_status.value
        supplier.supplier_status = body.supplier_status
    if body.notes is not None:
        changes["notes"] = body.notes
        supplier.notes = body.notes

    supplier.updated_by = current_user.id
    supplier.updated_at = datetime.now(UTC)
    saved = await supplier_repo.save(supplier)

    await audit_repo.save(
        audit_events.supplier_updated(
            supplier_id=saved.id,
            supplier_name=saved.name,
            actor_id=current_user.id,
            actor_email=current_user.email,
            changes=changes,
        )
    )
    return SupplierResponse.model_validate(saved)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_supplier(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> None:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    supplier.supplier_status = SupplierStatus.INACTIVE
    supplier.status = EntityStatus.ARCHIVED
    supplier.updated_by = current_user.id
    supplier.updated_at = datetime.now(UTC)
    await supplier_repo.save(supplier)

    await audit_repo.save(
        audit_events.supplier_archived(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    )
    logger.info("supplier_archived", supplier_id=supplier_id)


# ── Sub-resources ─────────────────────────────────────────────────────────────


@router.get("/{supplier_id}/assessments", response_model=Page[dict])
async def list_supplier_assessments(
    supplier_id: str,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    session: AsyncSession = Depends(get_db),
) -> Page[dict]:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    stmt = (
        select(AssessmentModel)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
        .order_by(AssessmentModel.created_at.desc())
    )
    from interfaces.api.schemas.assessment import AssessmentResponse  # noqa: PLC0415

    items_raw, total = await assessment_repo._execute_paged(stmt, pagination.page, pagination.page_size)
    return Page(
        items=[AssessmentResponse.model_validate(a).model_dump() for a in items_raw],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{supplier_id}/risk-profile", response_model=SupplierRiskProfile)
async def get_supplier_risk_profile(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    session: AsyncSession = Depends(get_db),
) -> SupplierRiskProfile:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    now = datetime.now(UTC)

    # ── Assessment counts ─────────────────────────────────────────────────────
    assessment_agg = await session.execute(
        select(
            func.count(AssessmentModel.id).label("total"),
            func.max(AssessmentModel.created_at).label("last_date"),
        ).where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
    )
    agg = assessment_agg.one()
    total_assessments = agg.total or 0
    last_assessment_date = agg.last_date.isoformat() if agg.last_date else None

    approved_row = await session.execute(
        select(func.count(AssessmentModel.id)).where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.review_status == "Approved",
        )
    )
    approved_assessments = approved_row.scalar() or 0

    in_review_row = await session.execute(
        select(func.count(AssessmentModel.id)).where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.review_status == "InReview",
        )
    )
    assessments_in_review = in_review_row.scalar() or 0

    # ── Findings by severity ──────────────────────────────────────────────────
    finding_rows = await session.execute(
        select(
            FindingModel.severity,
            func.count(FindingModel.id).label("cnt"),
        )
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(FindingModel.severity)
    )
    findings_by_severity: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    total_findings = 0
    for row in finding_rows:
        findings_by_severity[row.severity] = row.cnt
        total_findings += row.cnt

    # ── Risks by severity ─────────────────────────────────────────────────────
    risk_rows = await session.execute(
        select(
            RiskModel.risk_level,
            func.count(RiskModel.id).label("cnt"),
        )
        .join(AssessmentModel, RiskModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(RiskModel.risk_level)
    )
    risks_by_severity: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    total_risks = 0
    for row in risk_rows:
        risks_by_severity[row.risk_level] = row.cnt
        total_risks += row.cnt

    # ── Recommendations / actions ─────────────────────────────────────────────
    _CLOSED = ("resolved", "verified")
    rec_rows = await session.execute(
        select(
            RecommendationModel.action_status,
            func.count(RecommendationModel.id).label("cnt"),
        )
        .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(RecommendationModel.action_status)
    )
    action_counts: dict[str, int] = {}
    for row in rec_rows:
        action_counts[row.action_status] = row.cnt

    open_recommendations = sum(
        v for k, v in action_counts.items() if k not in _CLOSED
    )
    open_actions = action_counts.get("open", 0) + action_counts.get("in_progress", 0)

    overdue_row = await session.execute(
        select(func.count(RecommendationModel.id))
        .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
            RecommendationModel.due_date < now,
            RecommendationModel.action_status.notin_(list(_CLOSED)),
        )
    )
    overdue_actions = overdue_row.scalar() or 0

    return SupplierRiskProfile(
        supplier_id=supplier_id,
        supplier_name=supplier.name,
        total_assessments=total_assessments,
        approved_assessments=approved_assessments,
        assessments_in_review=assessments_in_review,
        last_assessment_date=last_assessment_date,
        total_findings=total_findings,
        findings_by_severity=findings_by_severity,
        total_risks=total_risks,
        risks_by_severity=risks_by_severity,
        open_recommendations=open_recommendations,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
    )
