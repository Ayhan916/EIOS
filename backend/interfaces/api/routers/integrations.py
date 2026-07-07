"""M48.1 — Enterprise Integrations API Router.

G-022: Teams/Slack notification test
G-047: JIRA/ServiceNow ticket creation from Finding
G-042: OFAC SDN scan trigger
G-049: SharePoint OAuth2 initiation
G-058: SBTi target validation
G-059: CDP report export
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from infrastructure.persistence.database import AsyncSessionFactory
from interfaces.api.deps import get_current_user, require_admin, require_analyst
from interfaces.api.schemas import UserResponse

router = APIRouter(tags=["integrations"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class TestWebhookRequest(BaseModel):
    channel: Literal["teams", "slack"]
    webhook_url: str = Field(..., min_length=10)


class CreateTicketRequest(BaseModel):
    system: Literal["jira", "servicenow"]
    project_key: str | None = None
    issue_type: str = "Bug"
    priority: str = "Medium"
    # JIRA
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    # ServiceNow
    servicenow_instance_url: str | None = None
    servicenow_username: str | None = None
    servicenow_password: str | None = None


class SBTiValidationRequest(BaseModel):
    target_id: str
    base_year: int = Field(..., ge=2010, le=2023)
    target_year: int = Field(..., ge=2025, le=2050)
    base_year_scope1_tco2e: float = Field(..., ge=0)
    base_year_scope2_tco2e: float = Field(..., ge=0)
    target_scope1_tco2e: float = Field(..., ge=0)
    target_scope2_tco2e: float = Field(..., ge=0)
    base_year_scope3_tco2e: float | None = None
    target_scope3_tco2e: float | None = None


class CDPReportRequest(BaseModel):
    reporting_year: int = Field(2024, ge=2020, le=2030)
    board_oversight: str = ""
    management_approach: str = ""
    science_based_target: bool = False
    net_zero_year: int | None = None
    total_energy_mwh: float | None = None
    renewable_energy_mwh: float | None = None
    scope1_tco2e: float | None = None
    scope2_market_tco2e: float | None = None
    scope2_location_tco2e: float | None = None
    scope3_tco2e: float | None = None


# ── G-022: Teams/Slack webhook test ──────────────────────────────────────────


@router.post(
    "/integrations/notifications/test",
    summary="G-022: Test Teams or Slack notification",
)
async def test_notification_webhook(
    body: TestWebhookRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    if body.channel == "teams":
        from application.notifications.teams_adapter import send_teams_notification

        ok = await send_teams_notification(
            webhook_url=body.webhook_url,
            title="EIOS Test Notification",
            body=f"Test from {current_user.email} at {datetime.now(UTC).isoformat()}",
            entity_type="integration_test",
        )
    else:
        from application.notifications.slack_adapter import send_slack_notification

        ok = await send_slack_notification(
            webhook_url=body.webhook_url,
            title="EIOS Test Notification",
            body=f"Test from {current_user.email} at {datetime.now(UTC).isoformat()}",
            entity_type="integration_test",
        )

    if not ok:
        raise HTTPException(
            status_code=502, detail="Webhook delivery failed — check URL and network access"
        )
    return {"status": "delivered", "channel": body.channel}


# ── G-047: JIRA/ServiceNow ticket ────────────────────────────────────────────


@router.post(
    "/findings/{finding_id}/create-ticket",
    summary="G-047: Create JIRA or ServiceNow ticket from finding",
)
async def create_finding_ticket(
    finding_id: str,
    body: CreateTicketRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.finding import FindingModel

    async with AsyncSessionFactory() as session:
        finding = await session.get(FindingModel, finding_id)
        if not finding or finding.owner != current_user.organization_id:
            raise HTTPException(status_code=404, detail="Finding not found")
        if finding.external_ticket_url:
            return {
                "ticket_url": finding.external_ticket_url,
                "ticket_id": finding.external_ticket_id,
                "system": finding.external_ticket_system,
                "created": False,
                "message": "Ticket already exists",
            }

        summary = f"[EIOS] {finding.title[:200]}"
        description = (
            f"Finding from EIOS ESG platform.\n\n"
            f"Category: {finding.category}\nSeverity: {finding.severity}\n\n"
            f"{finding.description[:2000]}"
        )

        if body.system == "jira":
            if not all(
                [body.jira_base_url, body.jira_email, body.jira_api_token, body.project_key]
            ):
                raise HTTPException(
                    status_code=422,
                    detail="jira_base_url, jira_email, jira_api_token, project_key required",
                )
            from application.integrations.jira_connector import create_jira_ticket

            result = await create_jira_ticket(
                base_url=body.jira_base_url,
                email=body.jira_email,
                api_token=body.jira_api_token,
                project_key=body.project_key,
                issue_type=body.issue_type,
                priority=body.priority,
                summary=summary,
                description=description,
                labels=["eios", "finding"],
            )
        else:
            if not all(
                [body.servicenow_instance_url, body.servicenow_username, body.servicenow_password]
            ):
                raise HTTPException(status_code=422, detail="ServiceNow credentials required")
            from application.integrations.jira_connector import create_servicenow_ticket

            result = await create_servicenow_ticket(
                instance_url=body.servicenow_instance_url,
                username=body.servicenow_username,
                password=body.servicenow_password,
                short_description=summary,
                description=description,
            )

        async with session.begin():
            finding.external_ticket_url = result.ticket_url
            finding.external_ticket_id = result.ticket_id
            finding.external_ticket_system = result.system

    return {
        "ticket_url": result.ticket_url,
        "ticket_id": result.ticket_id,
        "system": result.system,
        "created": True,
    }


# ── G-042: OFAC scan ─────────────────────────────────────────────────────────


@router.post(
    "/integrations/sanctions/ofac/scan",
    summary="G-042: Scan all suppliers against OFAC SDN list",
    dependencies=[Depends(require_admin)],
)
async def trigger_ofac_scan(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    fuzzy: bool = Query(False, description="Use fuzzy name matching (higher recall)"),
):
    """Download OFAC SDN list and match against org suppliers.

    Returns matches synchronously for small orgs. For large orgs (>500 suppliers),
    this should be offloaded to a Celery task.
    """
    from application.external_intelligence.connectors.ofac import (
        fetch_sdn_xml,
        match_supplier_against_sdn,
        parse_sdn_entries,
    )
    from infrastructure.persistence.models.supplier import SupplierModel

    xml_bytes = await fetch_sdn_xml()
    sdn_entries = parse_sdn_entries(xml_bytes)

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(SupplierModel)
            .where(
                SupplierModel.owner == current_user.organization_id,
                SupplierModel.status == "Active",
            )
            .limit(500)
        )
        suppliers = result.scalars().all()

    matches = []
    for supplier in suppliers:
        hits = match_supplier_against_sdn(supplier.name, sdn_entries, fuzzy=fuzzy)
        for hit in hits:
            matches.append(
                {
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name,
                    "sdn_uid": hit["uid"],
                    "sdn_name": hit["name"],
                    "sdn_type": hit["type"],
                    "programs": hit["programs"][:3],
                }
            )

    return {
        "scan_timestamp": datetime.now(UTC).isoformat(),
        "sdn_entries_checked": len(sdn_entries),
        "suppliers_scanned": len(suppliers),
        "matches_found": len(matches),
        "matches": matches[:50],
        "fuzzy": fuzzy,
    }


# ── G-042b: Per-supplier OFAC scan ───────────────────────────────────────────


@router.post(
    "/integrations/sanctions/ofac/scan/supplier/{supplier_id}",
    summary="G-042b: Scan a single supplier against OFAC SDN list",
    dependencies=[Depends(require_analyst)],
)
async def scan_single_supplier_ofac(
    supplier_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    fuzzy: bool = Query(False, description="Use fuzzy name matching"),
):
    from application.external_intelligence.connectors.ofac import (
        fetch_sdn_xml,
        match_supplier_against_sdn,
        parse_sdn_entries,
    )
    from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel
    from infrastructure.persistence.models.supplier import SupplierModel

    org_id = current_user.organization_id

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(SupplierModel).where(
                SupplierModel.id == supplier_id,
                SupplierModel.organization_id == org_id,
            )
        )
        supplier = result.scalar_one_or_none()

    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Download SDN list — gracefully handle network unavailability
    sdn_entries: list = []
    network_error: str | None = None
    try:
        xml_bytes = await fetch_sdn_xml()
        sdn_entries = parse_sdn_entries(xml_bytes)
    except Exception as exc:
        network_error = str(exc)

    if network_error:
        sanctions_exposure = "unavailable"
        matches: list = []
    else:
        hits = match_supplier_against_sdn(supplier.name, sdn_entries, fuzzy=fuzzy)
        matches = [
            {
                "sdn_uid": h["uid"],
                "sdn_name": h["name"],
                "sdn_type": h["type"],
                "programs": h["programs"][:3],
            }
            for h in hits
        ]
        sanctions_exposure = "high" if matches else "none"

    # Persist result so the supplier list shows the OFAC status
    async with AsyncSessionFactory() as session:
        enrichment_result = await session.execute(
            select(SupplierEnrichmentModel).where(
                SupplierEnrichmentModel.supplier_id == supplier_id,
                SupplierEnrichmentModel.organization_id == org_id,
            )
        )
        enrichment = enrichment_result.scalar_one_or_none()
        if enrichment:
            enrichment.sanctions_exposure = sanctions_exposure
            enrichment.enriched_at = datetime.now(UTC)
        else:
            session.add(
                SupplierEnrichmentModel(
                    supplier_id=supplier_id,
                    organization_id=org_id,
                    sanctions_exposure=sanctions_exposure,
                    enriched_at=datetime.now(UTC),
                )
            )
        await session.commit()

    return {
        "scan_timestamp": datetime.now(UTC).isoformat(),
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "sdn_entries_checked": len(sdn_entries),
        "matches_found": len(matches),
        "sanctions_exposure": sanctions_exposure,
        "matches": matches[:20],
        "fuzzy": fuzzy,
    }


# ── G-049: SharePoint OAuth2 ─────────────────────────────────────────────────


@router.get(
    "/integrations/sharepoint/auth",
    summary="G-049: Initiate SharePoint OAuth2 authorization flow",
)
async def sharepoint_auth_initiate(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    redirect_uri: str = Query(..., description="OAuth2 redirect URI registered in Azure AD"),
):
    from application.integrations.sharepoint_connector import build_auth_url
    from shared.config import settings

    client_id = settings.sharepoint_client_id if hasattr(settings, "sharepoint_client_id") else ""
    tenant_id = settings.sharepoint_tenant_id if hasattr(settings, "sharepoint_tenant_id") else ""
    if not client_id or not tenant_id:
        raise HTTPException(
            status_code=503,
            detail="SharePoint integration not configured — set SHAREPOINT_CLIENT_ID and SHAREPOINT_TENANT_ID",
        )
    auth_url = build_auth_url(
        client_id=client_id,
        tenant_id=tenant_id,
        redirect_uri=redirect_uri,
        state=current_user.organization_id,
    )
    return {"auth_url": auth_url}


@router.post(
    "/integrations/sharepoint/callback",
    summary="G-049: Handle SharePoint OAuth2 callback — exchange code for tokens",
)
async def sharepoint_auth_callback(
    code: str = Query(...),
    redirect_uri: str = Query(...),
    current_user: Annotated[UserResponse, Depends(get_current_user)] = None,
):
    from application.integrations.sharepoint_connector import exchange_code_for_tokens
    from shared.config import settings

    client_id = settings.sharepoint_client_id if hasattr(settings, "sharepoint_client_id") else ""
    tenant_id = settings.sharepoint_tenant_id if hasattr(settings, "sharepoint_tenant_id") else ""
    client_secret = (
        settings.sharepoint_client_secret if hasattr(settings, "sharepoint_client_secret") else ""
    )
    if not all([client_id, tenant_id, client_secret]):
        raise HTTPException(status_code=503, detail="SharePoint credentials not configured")
    tokens = await exchange_code_for_tokens(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        code=code,
        redirect_uri=redirect_uri,
    )
    return {
        "connected": True,
        "token_type": tokens.get("token_type"),
        "expires_in": tokens.get("expires_in"),
        "scope": tokens.get("scope"),
    }


@router.get(
    "/integrations/sharepoint/files",
    summary="G-049: List SharePoint site files (requires valid access token)",
)
async def sharepoint_list_files(
    access_token: str = Query(..., description="Bearer access token from SharePoint OAuth2 flow"),
    site_id: str = Query(...),
    folder_path: str = Query("/", description="Folder path relative to document library root"),
    current_user: Annotated[UserResponse, Depends(get_current_user)] = None,
):
    from application.integrations.sharepoint_connector import list_sharepoint_files

    files = await list_sharepoint_files(
        access_token=access_token,
        site_id=site_id,
        folder_path=folder_path,
    )
    return {"site_id": site_id, "folder_path": folder_path, "items": files}


# ── G-058: SBTi validation ───────────────────────────────────────────────────


@router.post(
    "/integrations/sbti/validate",
    summary="G-058: Validate emissions target against SBTi 1.5°C criteria",
)
async def validate_sbti_target(
    body: SBTiValidationRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from application.integrations.sbti_service import validate_sbti_target as _validate

    result = _validate(
        target_id=body.target_id,
        organization_name=current_user.organization_id,
        base_year=body.base_year,
        target_year=body.target_year,
        base_year_scope1_tco2e=body.base_year_scope1_tco2e,
        base_year_scope2_tco2e=body.base_year_scope2_tco2e,
        target_scope1_tco2e=body.target_scope1_tco2e,
        target_scope2_tco2e=body.target_scope2_tco2e,
        base_year_scope3_tco2e=body.base_year_scope3_tco2e,
        target_scope3_tco2e=body.target_scope3_tco2e,
    )
    return result.to_dict()


# ── G-059: CDP report ─────────────────────────────────────────────────────────


@router.post(
    "/integrations/cdp/report",
    summary="G-059: Generate CDP Climate Change questionnaire response package",
)
async def generate_cdp_report(
    body: CDPReportRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from application.integrations.cdp_service import build_cdp_climate_report

    return build_cdp_climate_report(
        organization_name=current_user.organization_id,
        reporting_year=body.reporting_year,
        board_oversight=body.board_oversight,
        management_approach=body.management_approach,
        science_based_target=body.science_based_target,
        net_zero_year=body.net_zero_year,
        total_energy_mwh=body.total_energy_mwh,
        renewable_energy_mwh=body.renewable_energy_mwh,
        scope1_tco2e=body.scope1_tco2e,
        scope2_market_tco2e=body.scope2_market_tco2e,
        scope2_location_tco2e=body.scope2_location_tco2e,
        scope3_tco2e=body.scope3_tco2e,
    )
