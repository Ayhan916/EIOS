"""M47 + M47.1 — Regulatory Reporting Router.

G-012: XBRL/iXBRL Export  GET /disclosure/packages/{id}/export?format=xbrl
G-013: Audit Trail Export  GET /audit/events/export?format=csv
G-023: Regulatory Calendar GET /regulatory/calendar
G-037: GRI Export          GET /disclosure/packages/{id}/export?format=gri
G-038: TCFD Report         GET /executive/tcfd?reporting_year=...
G-039: SFDR PAI            GET /financial-esg/sfdr/pai
G-028: Framework Mapping   POST/GET/DELETE /controls/{id}/framework-mappings
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.user import User
from interfaces.api.deps import get_current_user, get_db, require_admin, require_analyst

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["M47 — Regulatory Reporting"])

_ANALYST = Depends(require_analyst)
_ADMIN = Depends(require_admin)

_MAX_AUDIT_ROWS = 50_000


# ── Schemas ───────────────────────────────────────────────────────────────────


class RegulatoryDeadlineResponse(BaseModel):
    id: str
    framework_code: str
    deadline_name: str
    deadline_date: date
    description: str
    jurisdiction: str
    entity_size: str
    is_mandatory: bool
    reporting_year: str | None
    organization_id: str | None

    model_config = {"from_attributes": True}


class FrameworkMappingCreate(BaseModel):
    framework_code: str = Field(min_length=1, max_length=30)
    framework_control_id: str = Field(min_length=1, max_length=100)
    framework_control_name: str = Field(default="", max_length=500)
    mapping_type: str = Field(default="direct", pattern="^(direct|partial|compensating)$")
    notes: str | None = None


class FrameworkMappingResponse(BaseModel):
    id: str
    control_id: str
    framework_code: str
    framework_control_id: str
    framework_control_name: str
    mapping_type: str
    notes: str | None
    organization_id: str
    created_by: str

    model_config = {"from_attributes": True}


# ── G-023: Regulatory Calendar ────────────────────────────────────────────────


@router.get(
    "/regulatory/calendar",
    response_model=list[RegulatoryDeadlineResponse],
    dependencies=[_ANALYST],
)
async def get_regulatory_calendar(
    jurisdiction: str | None = Query(default=None),
    framework_code: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=2020, le=2035),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[RegulatoryDeadlineResponse]:
    """Return regulatory reporting deadlines, filterable by jurisdiction/framework/year."""
    from infrastructure.persistence.models.regulatory_calendar import (
        RegulatoryDeadlineModel,  # noqa: PLC0415
    )

    stmt = select(RegulatoryDeadlineModel).where(
        (RegulatoryDeadlineModel.organization_id.is_(None))
        | (RegulatoryDeadlineModel.organization_id == current_user.organization_id)
    )
    if jurisdiction:
        stmt = stmt.where(RegulatoryDeadlineModel.jurisdiction == jurisdiction.upper())
    if framework_code:
        stmt = stmt.where(RegulatoryDeadlineModel.framework_code == framework_code.upper())
    if year:
        stmt = stmt.where(
            RegulatoryDeadlineModel.deadline_date.between(date(year, 1, 1), date(year, 12, 31))
        )
    stmt = stmt.order_by(RegulatoryDeadlineModel.deadline_date)
    result = await session.execute(stmt)
    return [RegulatoryDeadlineResponse.model_validate(d) for d in result.scalars().all()]


@router.post(
    "/regulatory/calendar",
    response_model=RegulatoryDeadlineResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def create_custom_deadline(
    body: RegulatoryDeadlineResponse,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RegulatoryDeadlineResponse:
    """Add a custom regulatory deadline for the organisation."""
    from infrastructure.persistence.models.regulatory_calendar import (
        RegulatoryDeadlineModel,  # noqa: PLC0415
    )

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")

    record = RegulatoryDeadlineModel(
        id=str(uuid.uuid4()),
        framework_code=body.framework_code,
        deadline_name=body.deadline_name,
        deadline_date=body.deadline_date,
        description=body.description,
        jurisdiction=body.jurisdiction,
        entity_size=body.entity_size,
        is_mandatory=body.is_mandatory,
        reporting_year=body.reporting_year,
        organization_id=current_user.organization_id,
    )
    session.add(record)
    await session.flush()
    return RegulatoryDeadlineResponse.model_validate(record)


# ── G-012: XBRL / GRI Export ─────────────────────────────────────────────────


@router.get(
    "/disclosure/packages/{package_id}/export",
    dependencies=[_ANALYST],
)
async def export_reporting_package(
    package_id: str,
    format: str = Query(default="xbrl", pattern="^(xbrl|gri|json)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export a reporting package as iXBRL, GRI-JSON, or plain JSON.

    - format=xbrl → iXBRL HTML (EFRAG ESRS Taxonomy 2023)
    - format=gri  → GRI Standards 2021 JSON
    - format=json → Raw report_data JSON
    """
    from infrastructure.persistence.models.disclosure import ReportingPackageModel  # noqa: PLC0415

    pkg = (
        await session.execute(
            select(ReportingPackageModel).where(
                ReportingPackageModel.id == package_id,
                ReportingPackageModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if pkg is None:
        raise HTTPException(status_code=404, detail="Reporting package not found")

    org_name = current_user.organization_id  # fallback — real impl loads org.name
    report_data = pkg.report_data or {}
    period_end = (
        pkg.publication_date.date() if hasattr(pkg.publication_date, "date") else date.today()
    )
    period_start = date(period_end.year, 1, 1)

    if format == "json":
        return Response(
            content=json.dumps(report_data, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="package_{package_id}.json"'},
        )

    if format == "xbrl":
        from application.reporting.xbrl_exporter import (  # noqa: PLC0415
            build_ixbrl,
            compute_document_hash,
        )

        ixbrl_bytes = build_ixbrl(
            organization_name=org_name,
            organization_id=current_user.organization_id or "",
            reporting_period_start=period_start,
            reporting_period_end=period_end,
            esrs_e1=report_data.get("esrs_e1"),
            esrs_e2=report_data.get("esrs_e2"),
            esrs_s1=report_data.get("esrs_s1"),
        )
        doc_hash = compute_document_hash(ixbrl_bytes)
        logger.info("xbrl_exported", package_id=package_id, hash=doc_hash[:16])
        return Response(
            content=ixbrl_bytes,
            media_type="application/xhtml+xml",
            headers={
                "Content-Disposition": f'attachment; filename="package_{package_id}_esrs.html"',
                "X-Document-Hash": doc_hash,
            },
        )

    # format=gri
    from application.reporting.gri_exporter import build_gri_report  # noqa: PLC0415

    gri_report = build_gri_report(
        organization_name=org_name,
        reporting_year=period_end.year,
        disclosures=report_data.get("disclosures", []),
        emissions=report_data.get("esrs_e1"),
        workforce=report_data.get("esrs_s1"),
    )
    return Response(
        content=json.dumps(gri_report, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="package_{package_id}_gri.json"'},
    )


# ── G-038: TCFD Report ───────────────────────────────────────────────────────


@router.get(
    "/executive/tcfd",
    dependencies=[_ANALYST],
)
async def get_tcfd_report(
    reporting_year: int = Query(default=2024, ge=2020, le=2035),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Generate a TCFD report from EIOS sustainability and risk data."""
    from application.reporting.tcfd_exporter import build_tcfd_report  # noqa: PLC0415
    from infrastructure.persistence.models.ghg import GHGCalculationModel  # noqa: PLC0415

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")

    # Aggregate GHG from this year's calculations
    year_start = datetime(reporting_year, 1, 1, tzinfo=UTC)
    year_end = datetime(reporting_year, 12, 31, 23, 59, 59, tzinfo=UTC)

    ghg_result = await session.execute(
        select(GHGCalculationModel).where(
            GHGCalculationModel.organization_id == current_user.organization_id,
            GHGCalculationModel.calculated_at.between(year_start, year_end),
        )
    )
    calculations = ghg_result.scalars().all()

    emissions: dict[str, float] = {}
    for calc in calculations:
        scope = calc.scope.upper()
        key = f"scope{scope[-1]}"
        emissions[key] = round((emissions.get(key) or 0.0) + calc.result_tco2e, 3)

    org_name = current_user.organization_id
    report = build_tcfd_report(
        organization_name=org_name,
        reporting_year=reporting_year,
        emissions=emissions if emissions else None,
    )
    return Response(
        content=json.dumps(report, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="tcfd_{reporting_year}.json"'},
    )


# ── G-039: SFDR PAI ──────────────────────────────────────────────────────────


@router.get(
    "/financial-esg/sfdr/pai",
    dependencies=[_ANALYST],
)
async def get_sfdr_pai(
    reference_year: int = Query(default=2024, ge=2020, le=2035),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Calculate SFDR PAI (14 mandatory + 2 opt-in) from EIOS data."""
    from application.reporting.sfdr_pai import calculate_pai  # noqa: PLC0415
    from infrastructure.persistence.models.ghg import GHGCalculationModel  # noqa: PLC0415

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")

    year_start = datetime(reference_year, 1, 1, tzinfo=UTC)
    year_end = datetime(reference_year, 12, 31, 23, 59, 59, tzinfo=UTC)

    ghg_rows = (
        (
            await session.execute(
                select(GHGCalculationModel).where(
                    GHGCalculationModel.organization_id == current_user.organization_id,
                    GHGCalculationModel.calculated_at.between(year_start, year_end),
                )
            )
        )
        .scalars()
        .all()
    )

    scope1 = scope2 = scope3 = None
    for r in ghg_rows:
        s = r.scope.upper()
        if s == "SCOPE1":
            scope1 = round((scope1 or 0.0) + r.result_tco2e, 3)
        elif s == "SCOPE2":
            scope2 = round((scope2 or 0.0) + r.result_tco2e, 3)
        elif s == "SCOPE3":
            scope3 = round((scope3 or 0.0) + r.result_tco2e, 3)

    org_name = current_user.organization_id
    pai_report = calculate_pai(
        organization_name=org_name,
        reference_period_start=f"{reference_year}-01-01",
        reference_period_end=f"{reference_year}-12-31",
        scope1_tco2e=scope1,
        scope2_tco2e=scope2,
        scope3_tco2e=scope3,
    )
    return Response(
        content=json.dumps(pai_report, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="sfdr_pai_{reference_year}.json"'},
    )


# ── G-013: Audit Trail Export ────────────────────────────────────────────────


@router.get(
    "/audit/events/export",
    dependencies=[_ADMIN],
)
async def export_audit_trail(
    format: str = Query(default="csv", pattern="^csv$"),
    start: str | None = Query(default=None, description="ISO date, e.g. 2024-01-01"),
    end: str | None = Query(default=None, description="ISO date, e.g. 2024-12-31"),
    entity_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream audit events as CSV.

    Scoped to the authenticated organization. Max 50,000 rows per export.
    For larger exports, trigger a background job (not yet implemented).
    """
    from application.reporting.audit_exporter import (  # noqa: PLC0415
        make_csv_filename,
        stream_audit_csv,
    )
    from infrastructure.persistence.models.audit_event import AuditEventModel  # noqa: PLC0415

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")

    # AuditEventModel.owner stores the organization_id (inherited from BaseModel)
    stmt = select(AuditEventModel).where(AuditEventModel.owner == current_user.organization_id)
    if start:
        try:
            dt_start = datetime.fromisoformat(start).replace(tzinfo=UTC)
            stmt = stmt.where(AuditEventModel.created_at >= dt_start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start date format")
    if end:
        try:
            dt_end = datetime.fromisoformat(end).replace(hour=23, minute=59, second=59, tzinfo=UTC)
            stmt = stmt.where(AuditEventModel.created_at <= dt_end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end date format")
    if entity_type:
        stmt = stmt.where(AuditEventModel.entity_type == entity_type)

    stmt = stmt.order_by(AuditEventModel.created_at.desc()).limit(_MAX_AUDIT_ROWS)
    result = await session.execute(stmt)
    events = result.scalars().all()

    event_dicts = [
        {
            "created_at": e.created_at,
            "action": e.action,
            "actor_email": e.actor_email,
            "actor_id": e.actor_id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "outcome": e.outcome,
            "detail": e.detail,
        }
        for e in events
    ]

    csv_content = stream_audit_csv(event_dicts)
    filename = make_csv_filename(start, end, entity_type)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── G-028: Control Framework Mapping ─────────────────────────────────────────


@router.post(
    "/controls/{control_id}/framework-mappings",
    response_model=FrameworkMappingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_framework_mapping(
    control_id: str,
    body: FrameworkMappingCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FrameworkMappingResponse:
    """Map a control to an external framework control (ISO14001, SOC2, ISO27001, GRC)."""
    from infrastructure.persistence.models.framework_mapping import (
        ControlFrameworkMappingModel,  # noqa: PLC0415
    )

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")

    mapping = ControlFrameworkMappingModel(
        id=str(uuid.uuid4()),
        control_id=control_id,
        framework_code=body.framework_code.upper(),
        framework_control_id=body.framework_control_id,
        framework_control_name=body.framework_control_name,
        mapping_type=body.mapping_type,
        notes=body.notes,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    try:
        session.add(mapping)
        await session.flush()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This control is already mapped to that framework control.",
        )
    logger.info("framework_mapping_created", mapping_id=mapping.id, control_id=control_id)
    return FrameworkMappingResponse.model_validate(mapping)


@router.get(
    "/controls/{control_id}/framework-mappings",
    response_model=list[FrameworkMappingResponse],
    dependencies=[_ANALYST],
)
async def list_framework_mappings(
    control_id: str,
    framework_code: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[FrameworkMappingResponse]:
    """List all framework mappings for a control."""
    from infrastructure.persistence.models.framework_mapping import (
        ControlFrameworkMappingModel,  # noqa: PLC0415
    )

    stmt = select(ControlFrameworkMappingModel).where(
        ControlFrameworkMappingModel.control_id == control_id,
        ControlFrameworkMappingModel.organization_id == current_user.organization_id,
    )
    if framework_code:
        stmt = stmt.where(ControlFrameworkMappingModel.framework_code == framework_code.upper())
    result = await session.execute(stmt.order_by(ControlFrameworkMappingModel.framework_code))
    return [FrameworkMappingResponse.model_validate(m) for m in result.scalars().all()]


@router.delete(
    "/controls/{control_id}/framework-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ANALYST],
)
async def delete_framework_mapping(
    control_id: str,
    mapping_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    from infrastructure.persistence.models.framework_mapping import (
        ControlFrameworkMappingModel,  # noqa: PLC0415
    )

    mapping = (
        await session.execute(
            select(ControlFrameworkMappingModel).where(
                ControlFrameworkMappingModel.id == mapping_id,
                ControlFrameworkMappingModel.control_id == control_id,
                ControlFrameworkMappingModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    await session.delete(mapping)
