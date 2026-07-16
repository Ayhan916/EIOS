"""M48.2 — Commercial Readiness API Router.

G-018: Board Report PPTX Export
G-034: Board Portal Share-Link (time-limited read-only)
G-032: Supplier Benchmarking
G-060: Custom Role Builder
G-055: White-Labeling settings
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from infrastructure.persistence.database import AsyncSessionFactory
from interfaces.api.deps import get_current_user, require_admin
from interfaces.api.schemas import UserResponse

router = APIRouter(tags=["commercial"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class ShareLinkRequest(BaseModel):
    expires_in_hours: int = Field(168, ge=1, le=720)
    allowed_sections: list[str] = Field(default_factory=list)
    shared_with_email: str | None = None


class ShareLinkResponse(BaseModel):
    token: str
    expires_at: datetime
    report_id: str
    board_url: str


class CustomRoleCreate(BaseModel):
    role_name: str = Field(..., min_length=2, max_length=100)
    description: str = ""
    permissions: list[dict] = Field(default_factory=list)
    base_template: str | None = None


class OrgSettingsUpdate(BaseModel):
    company_name_override: str | None = None
    logo_url: str | None = Field(None, max_length=2000)
    primary_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    favicon_url: str | None = Field(None, max_length=2000)
    teams_webhook_url: str | None = None
    slack_webhook_url: str | None = None
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    servicenow_instance_url: str | None = None
    servicenow_username: str | None = None


# ── G-018: PPTX Export ───────────────────────────────────────────────────────


@router.get(
    "/executive/reports/{report_id}/export",
    summary="G-018: Export board report as PPTX",
    response_class=Response,
)
async def export_report_pptx(
    report_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    format: str = Query("pptx", pattern="^pptx$"),
):
    from sqlalchemy import select

    from application.executive.pptx_exporter import build_board_report_pptx
    from infrastructure.persistence.models.board_report import BoardReportModel
    from infrastructure.persistence.models.recommendation import RecommendationModel
    from infrastructure.persistence.models.risk import RiskModel

    async with AsyncSessionFactory() as session:
        report = await session.get(BoardReportModel, report_id)
        if not report or report.owner != current_user.organization_id:
            raise HTTPException(status_code=404, detail="Report not found")

        risks_res = await session.execute(
            select(RiskModel)
            .where(
                RiskModel.owner == current_user.organization_id,
                RiskModel.status == "Active",
            )
            .order_by(RiskModel.updated_at.desc())
            .limit(10)
        )
        risks = [
            {
                "title": r.title,
                "severity": r.severity,
                "status": r.status,
                "owner": r.owner or "",
            }
            for r in risks_res.scalars().all()
        ]

        recs_res = await session.execute(
            select(RecommendationModel)
            .where(
                RecommendationModel.owner == current_user.organization_id,
                RecommendationModel.status == "Open",
            )
            .limit(8)
        )
        recs = [
            {
                "title": r.title,
                "priority": r.priority,
                "due_date": str(r.due_date) if r.due_date else "TBD",
            }
            for r in recs_res.scalars().all()
        ]

    kpi_data = report.summary_data or {} if hasattr(report, "summary_data") else {}
    kpis = [{"label": k, "value": str(v), "unit": ""} for k, v in list(kpi_data.items())[:8]]

    pptx_bytes = build_board_report_pptx(
        organization_name=current_user.organization_id,
        report_title=report.title if hasattr(report, "title") else "Board Report",
        executive_summary=report.executive_summary if hasattr(report, "executive_summary") else "",
        kpi_highlights=kpis,
        risks=risks,
        recommendations=recs,
    )

    filename = f"eios_board_report_{report_id[:8]}.pptx"
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── G-034: Board Portal Share-Link ───────────────────────────────────────────


@router.post(
    "/executive/reports/{report_id}/share-link",
    response_model=ShareLinkResponse,
    summary="G-034: Create time-limited read-only board portal link",
)
async def create_share_link(
    report_id: str,
    body: ShareLinkRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from application.commercial.board_portal import create_board_token, hash_token
    from infrastructure.persistence.models.board_access_token import BoardAccessTokenModel
    from infrastructure.persistence.models.board_report import BoardReportModel

    async with AsyncSessionFactory() as session:
        report = await session.get(BoardReportModel, report_id)
        if not report or report.owner != current_user.organization_id:
            raise HTTPException(status_code=404, detail="Report not found")

    token, expires_at = create_board_token(
        report_id=report_id,
        organization_id=current_user.organization_id,
        expires_in_hours=body.expires_in_hours,
        allowed_sections=body.allowed_sections,
    )
    token_hash = hash_token(token)

    bat = BoardAccessTokenModel(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        report_id=report_id,
        token_hash=token_hash,
        allowed_sections=json.dumps(body.allowed_sections),
        expires_at=expires_at,
        revoked=False,
        created_by=current_user.id,
        shared_with_email=body.shared_with_email,
    )

    async with AsyncSessionFactory() as session, session.begin():
        session.add(bat)

    # In production, this would be the frontend board portal URL
    board_url = f"/board/{token}"

    return ShareLinkResponse(
        token=token,
        expires_at=expires_at,
        report_id=report_id,
        board_url=board_url,
    )


@router.post(
    "/board/tokens/{token_hash}/revoke",
    summary="G-034: Revoke a board portal access token",
    dependencies=[Depends(require_admin)],
)
async def revoke_board_token(
    token_hash: str,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from sqlalchemy import update

    from infrastructure.persistence.models.board_access_token import BoardAccessTokenModel

    async with AsyncSessionFactory() as session, session.begin():
        await session.execute(
            update(BoardAccessTokenModel)
            .where(
                BoardAccessTokenModel.token_hash == token_hash,
                BoardAccessTokenModel.organization_id == current_user.organization_id,
            )
            .values(revoked=True)
        )
    return {"revoked": True, "token_hash": token_hash}


# ── M50: Board Portal Public Data Endpoint ───────────────────────────────────


@router.get(
    "/board/{token}",
    summary="M50: Read board report data via share-link token (public, no auth)",
)
async def get_board_portal_data(token: str):
    """Returns board report data for a valid, non-expired, non-revoked share token.

    This endpoint is intentionally public (no auth dependency) — access is
    controlled by the time-limited signed JWT token.
    """
    from datetime import UTC as _UTC
    from datetime import datetime as _dt

    import jwt

    from application.commercial.board_portal import decode_board_token, hash_token
    from infrastructure.persistence.models.board_access_token import BoardAccessTokenModel
    from infrastructure.persistence.models.board_report import BoardReportModel

    # Decode and verify the JWT
    try:
        payload = decode_board_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=410, detail="Board portal link has expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid board portal token")

    report_id = payload["report_id"]
    token_hash = hash_token(token)

    async with AsyncSessionFactory() as session:
        # Verify token not revoked in DB
        await session.get(BoardAccessTokenModel, token_hash)
        # Try looking up by token_hash field directly
        from sqlalchemy import select as _select

        bat_row = (
            await session.execute(
                _select(BoardAccessTokenModel).where(BoardAccessTokenModel.token_hash == token_hash)
            )
        ).scalar_one_or_none()

        if bat_row is None:
            raise HTTPException(status_code=401, detail="Token not found")
        if bat_row.revoked:
            raise HTTPException(status_code=410, detail="Board portal link has been revoked")
        now = _dt.now(_UTC)
        if bat_row.expires_at.replace(tzinfo=_UTC) < now:
            raise HTTPException(status_code=410, detail="Board portal link has expired")

        # Load the board report
        report = await session.get(BoardReportModel, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Board report not found")

        import json as _json

        allowed_sections = _json.loads(bat_row.allowed_sections or "[]")

        def _section(key: str, data: dict) -> dict | None:
            if allowed_sections and key not in allowed_sections:
                return None
            return data.get(key)

        report_data = report.report_data or {}
        return {
            "report_id": report.id,
            "title": report.title,
            "period_start": str(report.period_start),
            "period_end": str(report.period_end),
            "generated_at": report.created_at.isoformat() if report.created_at else None,
            "report_version": report.report_version,
            "executive_summary": report.executive_summary,
            "allowed_sections": allowed_sections,
            "expires_at": bat_row.expires_at.isoformat(),
            "shared_with_email": bat_row.shared_with_email,
            "supplier_snapshot": report.supplier_snapshot
            if not allowed_sections or "portfolio" in allowed_sections
            else None,
            "sections": {
                "portfolio": _section("portfolio_summary", report_data),
                "esg": _section("esg_summary", report_data),
                "governance": _section("governance_summary", report_data),
                "risk": _section("action_summary", report_data),
                "sustainability": _section("sustainability_summary", report_data),
                "financial": _section("financial_summary", report_data),
            },
        }


# ── G-032: Supplier Benchmarking ─────────────────────────────────────────────


@router.get(
    "/suppliers/{supplier_id}/benchmark",
    summary="G-032: Benchmark supplier against sector peers",
)
async def get_supplier_benchmark(
    supplier_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from sqlalchemy import select

    from application.commercial.benchmarking import compute_benchmark
    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.supplier_score import SupplierScoreModel

    async with AsyncSessionFactory() as session:
        supplier = await session.get(SupplierModel, supplier_id)
        if not supplier or supplier.owner != current_user.organization_id:
            raise HTTPException(status_code=404, detail="Supplier not found")

        # Fetch scores for this supplier
        score_res = await session.execute(
            select(SupplierScoreModel)
            .where(SupplierScoreModel.supplier_id == supplier_id)
            .order_by(SupplierScoreModel.created_at.desc())
            .limit(1)
        )
        score_row = score_res.scalar_one_or_none()
        supplier_scores = {}
        if score_row:
            supplier_scores = {
                "overall_esg_score": score_row.overall_esg_score,
                "environmental_score": score_row.environmental_score,
                "social_score": score_row.social_score,
                "governance_score": score_row.governance_score,
            }

        # Peer suppliers: same industry, same org
        peer_query = select(SupplierModel).where(
            SupplierModel.owner == current_user.organization_id,
            SupplierModel.id != supplier_id,
            SupplierModel.status == "Active",
        )
        if supplier.industry:
            peer_query = peer_query.where(SupplierModel.industry == supplier.industry)
        peer_res = await session.execute(peer_query.limit(200))
        peer_suppliers = peer_res.scalars().all()

        # Fetch peer scores
        peer_score_rows = []
        for ps in peer_suppliers:
            ps_score = await session.execute(
                select(SupplierScoreModel)
                .where(SupplierScoreModel.supplier_id == ps.id)
                .order_by(SupplierScoreModel.created_at.desc())
                .limit(1)
            )
            row = ps_score.scalar_one_or_none()
            if row:
                peer_score_rows.append(
                    {
                        "overall_esg_score": row.overall_esg_score,
                        "environmental_score": row.environmental_score,
                        "social_score": row.social_score,
                        "governance_score": row.governance_score,
                    }
                )

    result = compute_benchmark(
        supplier_id=supplier_id,
        supplier_name=supplier.name,
        organization_id=current_user.organization_id,
        supplier_scores=supplier_scores,
        peers=peer_score_rows,
        peer_industry=supplier.industry,
    )
    return result.to_dict()


# ── G-060: Custom Roles ──────────────────────────────────────────────────────


@router.post(
    "/roles/custom",
    summary="G-060: Create a custom RBAC role",
    dependencies=[Depends(require_admin)],
)
async def create_custom_role(
    body: CustomRoleCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.custom_role import CustomRoleModel

    role = CustomRoleModel(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        role_name=body.role_name,
        description=body.description,
        permissions=json.dumps(body.permissions),
        base_template=body.base_template,
        is_system=False,
        created_by=current_user.id,
    )
    async with AsyncSessionFactory() as session, session.begin():
        session.add(role)

    return {
        "id": role.id,
        "role_name": role.role_name,
        "description": role.description,
        "permissions": body.permissions,
        "base_template": role.base_template,
    }


@router.get(
    "/roles/custom",
    summary="G-060: List custom roles for the organization",
)
async def list_custom_roles(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from sqlalchemy import select

    from infrastructure.persistence.models.custom_role import ROLE_TEMPLATES, CustomRoleModel

    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(CustomRoleModel).where(
                CustomRoleModel.organization_id == current_user.organization_id
            )
        )
        roles = res.scalars().all()

    return {
        "items": [
            {
                "id": r.id,
                "role_name": r.role_name,
                "description": r.description,
                "permissions": json.loads(r.permissions),
                "base_template": r.base_template,
                "is_system": r.is_system,
            }
            for r in roles
        ],
        "templates": list(ROLE_TEMPLATES.keys()),
    }


@router.delete(
    "/roles/custom/{role_id}",
    summary="G-060: Delete a custom role",
    dependencies=[Depends(require_admin)],
)
async def delete_custom_role(
    role_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.custom_role import CustomRoleModel

    async with AsyncSessionFactory() as session, session.begin():
        role = await session.get(CustomRoleModel, role_id)
        if not role or role.organization_id != current_user.organization_id:
            raise HTTPException(status_code=404, detail="Role not found")
        if role.is_system:
            raise HTTPException(status_code=403, detail="System roles cannot be deleted")
        await session.delete(role)

    return {"deleted": True, "id": role_id}


@router.get(
    "/roles/custom/templates",
    summary="G-060: List available role templates",
)
async def list_role_templates(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.custom_role import ROLE_TEMPLATES

    return {"templates": ROLE_TEMPLATES}


# ── G-055: White-Labeling / Org Settings ─────────────────────────────────────


@router.get(
    "/organizations/me/settings",
    summary="G-055: Get organization branding and integration settings",
)
async def get_org_settings(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

    async with AsyncSessionFactory() as session:
        settings_row = await session.get(OrganizationSettingsModel, current_user.organization_id)

    if not settings_row:
        return {
            "organization_id": current_user.organization_id,
            "company_name_override": None,
            "logo_url": None,
            "primary_color": None,
            "favicon_url": None,
            "integrations_configured": [],
        }

    integrations = []
    if settings_row.teams_webhook_url:
        integrations.append("teams")
    if settings_row.slack_webhook_url:
        integrations.append("slack")
    if settings_row.jira_base_url:
        integrations.append("jira")
    if settings_row.servicenow_instance_url:
        integrations.append("servicenow")
    if settings_row.sharepoint_site_id:
        integrations.append("sharepoint")

    return {
        "organization_id": current_user.organization_id,
        "company_name_override": settings_row.company_name_override,
        "logo_url": settings_row.logo_url,
        "primary_color": settings_row.primary_color,
        "favicon_url": settings_row.favicon_url,
        "integrations_configured": integrations,
    }


@router.put(
    "/organizations/me/settings",
    summary="G-055: Update organization branding and integration settings",
    dependencies=[Depends(require_admin)],
)
async def update_org_settings(
    body: OrgSettingsUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

    async with AsyncSessionFactory() as session, session.begin():
        settings_row = await session.get(OrganizationSettingsModel, current_user.organization_id)
        if not settings_row:
            settings_row = OrganizationSettingsModel(organization_id=current_user.organization_id)
            session.add(settings_row)

        update_data = body.model_dump(exclude_none=True)
        # Store JIRA token as a reference, not raw value (in prod, use SecretRef)
        if "jira_api_token" in update_data:
            settings_row.jira_api_token_ref = update_data.pop("jira_api_token")
        for key, value in update_data.items():
            if hasattr(settings_row, key):
                setattr(settings_row, key, value)

    return {"updated": True, "organization_id": current_user.organization_id}


# ── LLM Model Settings ────────────────────────────────────────────────────────

ALLOWED_MODELS = {
    "anthropic:claude-sonnet-4-6",
    "anthropic:claude-haiku-4-5-20251001",
    "groq:llama-3.3-70b-versatile",
    "groq:llama-3.1-8b-instant",
}

ALLOWED_JOBS = {"extraction", "classification", "analysis", "copilot", "cross_source", "twin"}


@router.get("/organizations/me/llm-models")
async def get_llm_model_settings(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.org_settings import OrganizationSettingsModel
    from infrastructure.llm.deps import JOB_DEFAULTS

    async with AsyncSessionFactory() as session:
        row = await session.get(OrganizationSettingsModel, current_user.organization_id)

    stored = (row.llm_model_settings or {}) if row else {}
    return {job: stored.get(job, JOB_DEFAULTS.get(job)) for job in ALLOWED_JOBS}


@router.put("/organizations/me/llm-models")
async def update_llm_model_settings(
    body: dict,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

    for job, model in body.items():
        if job not in ALLOWED_JOBS:
            raise HTTPException(status_code=400, detail=f"Unknown job: {job}")
        if model not in ALLOWED_MODELS:
            raise HTTPException(status_code=400, detail=f"Unknown model: {model}")

    async with AsyncSessionFactory() as session, session.begin():
        row = await session.get(OrganizationSettingsModel, current_user.organization_id)
        if not row:
            row = OrganizationSettingsModel(organization_id=current_user.organization_id)
            session.add(row)
        current = dict(row.llm_model_settings or {})
        current.update(body)
        row.llm_model_settings = current

    return {"updated": True, "settings": current}


# ── Pipeline Quality Settings ─────────────────────────────────────────────────

PIPELINE_DEFAULTS = {
    "parse_engine":           "docling",
    "ocr_enabled":            False,
    "extract_tables":         "markdown",
    "chunk_size":             800,
    "chunk_overlap":          80,
    "chunk_strategy":         "sliding_window",
    "retrieval_mode":         "dense",
    "similarity_threshold":   0.25,
    "top_k":                  8,
}

PIPELINE_ALLOWED_KEYS = set(PIPELINE_DEFAULTS.keys())


@router.get("/organizations/me/pipeline-settings")
async def get_pipeline_settings(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

    async with AsyncSessionFactory() as session:
        row = await session.get(OrganizationSettingsModel, current_user.organization_id)

    stored = (row.pipeline_settings or {}) if row else {}
    return {k: stored.get(k, v) for k, v in PIPELINE_DEFAULTS.items()}


@router.put("/organizations/me/pipeline-settings")
async def update_pipeline_settings(
    body: dict,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

    unknown = set(body.keys()) - PIPELINE_ALLOWED_KEYS
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown keys: {unknown}")

    async with AsyncSessionFactory() as session, session.begin():
        row = await session.get(OrganizationSettingsModel, current_user.organization_id)
        if not row:
            row = OrganizationSettingsModel(organization_id=current_user.organization_id)
            session.add(row)
        current = dict(row.pipeline_settings or PIPELINE_DEFAULTS)
        current.update(body)
        row.pipeline_settings = current

    return {"updated": True, "settings": current}
