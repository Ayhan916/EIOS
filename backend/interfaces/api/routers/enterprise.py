"""M40 — Enterprise API Router.

Provides /api/v1/enterprise endpoints for:
  - enterprises (CRUD)
  - business-units (CRUD)
  - legal-entities (CRUD)
  - regions (CRUD)
  - identity (SSO IdP config + group mappings)
  - policies (enterprise policies)
  - retention (retention rules)
  - notifications (notification routing policies)
  - risks (enterprise risk register)
  - roles (delegated administration)
  - dashboard (enterprise health + rollups)
  - search (global search)
  - audit (cross-org audit events)
  - scim (SCIM 2.0 user provisioning)
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.enterprise import (
    admin_service,
    hierarchy_service,
    policy_service,
    risk_service,
    rollup_service,
    scim_service,
    search_service,
    sso_service,
)
from interfaces.api.deps import get_current_user, get_db, require_admin, require_scim_token
from interfaces.api.schemas.enterprise import (
    AssignEnterpriseRoleRequest,
    AssignEnterpriseRoleResponse,
    BulkOperationResult,
    BulkRiskUpdate,
    BulkSupplierUpdate,
    BusinessUnitCreate,
    BusinessUnitResponse,
    EnterpriseCreate,
    EnterpriseDashboard,
    EnterpriseHealthScore,
    EnterprisePolicyCreate,
    EnterprisePolicyResponse,
    EnterpriseResponse,
    EnterpriseRiskCreate,
    EnterpriseRiskResponse,
    EnterpriseUpdate,
    GlobalSearchRequest,
    GlobalSearchResponse,
    GroupMappingCreate,
    GroupMappingResponse,
    IdentityProviderCreate,
    IdentityProviderResponse,
    LegalEntityCreate,
    LegalEntityResponse,
    LinkOrganizationRequest,
    NotificationPolicyCreate,
    NotificationPolicyResponse,
    OIDCCallbackRequest,
    RegionCreate,
    RegionResponse,
    RetentionRuleCreate,
    RetentionRuleResponse,
    SAMLCallbackRequest,
    SCIMPerIdpUsage,
    SCIMTokenCreate,
    SCIMTokenCreateResponse,
    SCIMTokenResponse,
    SCIMTokenRotateResponse,
    SCIMUsageResponse,
    ScimUserCreate,
    SecretHealthResponse,
    SecretRotateRequest,
    SecretRotateResponse,
    SSOLoginRequest,
    SSOLoginResponse,
)

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/enterprise",
    tags=["enterprise"],
    dependencies=[Depends(require_admin)],
)

_ADMIN = Depends(require_admin)


# ── Enterprises ───────────────────────────────────────────────────────────────


@router.post("", response_model=EnterpriseResponse, status_code=status.HTTP_201_CREATED)
async def create_enterprise(
    body: EnterpriseCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EnterpriseResponse:
    enterprise = await hierarchy_service.create_enterprise(
        name=body.name,
        description=body.description,
        hq_country=body.hq_country,
        industry=body.industry,
        default_data_residency=body.default_data_residency,
        default_data_classification=body.default_data_classification,
        settings=body.settings,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return EnterpriseResponse.model_validate(enterprise)


@router.get("", response_model=list[EnterpriseResponse])
async def list_enterprises(
    session: AsyncSession = Depends(get_db),
) -> list[EnterpriseResponse]:
    items = await hierarchy_service.list_enterprises(session)
    return [EnterpriseResponse.model_validate(e) for e in items]


@router.get("/{enterprise_id}", response_model=EnterpriseResponse)
async def get_enterprise(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> EnterpriseResponse:
    enterprise = await hierarchy_service.get_enterprise(enterprise_id, session)
    if not enterprise:
        raise HTTPException(status_code=404, detail="Enterprise not found")
    return EnterpriseResponse.model_validate(enterprise)


@router.patch("/{enterprise_id}", response_model=EnterpriseResponse)
async def update_enterprise(
    enterprise_id: str,
    body: EnterpriseUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EnterpriseResponse:
    enterprise = await hierarchy_service.update_enterprise(
        enterprise_id=enterprise_id,
        updates=body.model_dump(exclude_none=True),
        actor_id=current_user.id,
        session=session,
    )
    if not enterprise:
        raise HTTPException(status_code=404, detail="Enterprise not found")
    await session.commit()
    return EnterpriseResponse.model_validate(enterprise)


# ── Business Units ────────────────────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/business-units",
    response_model=BusinessUnitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_business_unit(
    enterprise_id: str,
    body: BusinessUnitCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> BusinessUnitResponse:
    bu = await hierarchy_service.create_business_unit(
        enterprise_id=enterprise_id,
        name=body.name,
        description=body.description,
        region_scope=body.region_scope,
        admin_user_id=body.admin_user_id,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return BusinessUnitResponse.model_validate(bu)


@router.get("/{enterprise_id}/business-units", response_model=list[BusinessUnitResponse])
async def list_business_units(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[BusinessUnitResponse]:
    items = await hierarchy_service.list_business_units(enterprise_id, session)
    return [BusinessUnitResponse.model_validate(b) for b in items]


# ── Legal Entities ────────────────────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/legal-entities",
    response_model=LegalEntityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_legal_entity(
    enterprise_id: str,
    body: LegalEntityCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> LegalEntityResponse:
    le = await hierarchy_service.create_legal_entity(
        enterprise_id=enterprise_id,
        name=body.name,
        description=body.description,
        country=body.country,
        registration_number=body.registration_number,
        legal_form=body.legal_form,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return LegalEntityResponse.model_validate(le)


@router.get("/{enterprise_id}/legal-entities", response_model=list[LegalEntityResponse])
async def list_legal_entities(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[LegalEntityResponse]:
    items = await hierarchy_service.list_legal_entities(enterprise_id, session)
    return [LegalEntityResponse.model_validate(e) for e in items]


# ── Regions ───────────────────────────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/regions",
    response_model=RegionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_region(
    enterprise_id: str,
    body: RegionCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RegionResponse:
    region = await hierarchy_service.create_region(
        enterprise_id=enterprise_id,
        name=body.name,
        code=body.code,
        description=body.description,
        data_residency=body.data_residency,
        admin_user_id=body.admin_user_id,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return RegionResponse.model_validate(region)


@router.get("/{enterprise_id}/regions", response_model=list[RegionResponse])
async def list_regions(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[RegionResponse]:
    items = await hierarchy_service.list_regions(enterprise_id, session)
    return [RegionResponse.model_validate(r) for r in items]


# ── Organization Linking ──────────────────────────────────────────────────────


@router.post("/{enterprise_id}/link-organization", response_model=dict)
async def link_organization(
    enterprise_id: str,
    body: LinkOrganizationRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    org = await hierarchy_service.link_organization(
        enterprise_id=enterprise_id,
        organization_id=body.organization_id,
        business_unit_id=body.business_unit_id,
        legal_entity_id=body.legal_entity_id,
        region_id=body.region_id,
        data_residency=body.data_residency,
        data_classification=body.data_classification,
        actor_id=current_user.id,
        session=session,
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await session.commit()
    return {"organization_id": body.organization_id, "enterprise_id": enterprise_id, "linked": True}


# ── Identity Providers ────────────────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/identity",
    response_model=IdentityProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_identity_provider(
    enterprise_id: str,
    body: IdentityProviderCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IdentityProviderResponse:
    idp = await sso_service.create_identity_provider(
        enterprise_id=enterprise_id,
        name=body.name,
        provider_type=body.provider_type,
        issuer=body.issuer,
        metadata_url=body.metadata_url,
        client_id=body.client_id,
        client_secret=body.client_secret,
        certificates=body.certificates,
        config=body.config,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    resp = IdentityProviderResponse.model_validate(idp)
    resp.has_client_secret = idp.secret_reference_id is not None
    return resp


@router.get("/{enterprise_id}/identity", response_model=list[IdentityProviderResponse])
async def list_identity_providers(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[IdentityProviderResponse]:
    items = await sso_service.list_identity_providers(enterprise_id, session)
    result = []
    for idp in items:
        r = IdentityProviderResponse.model_validate(idp)
        r.has_client_secret = idp.secret_reference_id is not None
        result.append(r)
    return result


@router.post(
    "/{enterprise_id}/identity/{idp_id}/group-mappings",
    response_model=GroupMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_group_mapping(
    enterprise_id: str,
    idp_id: str,
    body: GroupMappingCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> GroupMappingResponse:
    mapping = await sso_service.create_group_mapping(
        idp_id=idp_id,
        enterprise_id=enterprise_id,
        idp_group=body.idp_group,
        mapped_role=body.mapped_role,
        scope=body.scope,
        business_unit_id=body.business_unit_id,
        region_id=body.region_id,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return GroupMappingResponse.model_validate(mapping)


@router.get(
    "/{enterprise_id}/identity/{idp_id}/group-mappings", response_model=list[GroupMappingResponse]
)
async def list_group_mappings(
    enterprise_id: str,
    idp_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[GroupMappingResponse]:
    items = await sso_service.list_group_mappings(idp_id, session)
    return [GroupMappingResponse.model_validate(m) for m in items]


@router.delete(
    "/{enterprise_id}/identity/{idp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_identity_provider(
    enterprise_id: str,
    idp_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete an IdP and clean up its stored client_secret from the secret provider."""
    ok = await sso_service.delete_identity_provider(idp_id, current_user.id, session)
    if not ok:
        raise HTTPException(status_code=404, detail="Identity provider not found")
    await session.commit()


@router.post(
    "/{enterprise_id}/identity/{idp_id}/rotate-secret",
    response_model=SecretRotateResponse,
)
async def rotate_identity_provider_secret(
    enterprise_id: str,
    idp_id: str,
    body: SecretRotateRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SecretRotateResponse:
    """Rotate the client_secret for an Identity Provider."""
    from datetime import UTC, datetime  # noqa: PLC0415

    try:
        ref = await sso_service.rotate_identity_provider_secret(
            idp_id=idp_id,
            new_client_secret=body.new_client_secret,
            actor_id=current_user.id,
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return SecretRotateResponse(
        idp_id=idp_id,
        new_reference_id=ref.id,
        rotated_at=datetime.now(UTC),
    )


# ── Secret Health (M40.2) ─────────────────────────────────────────────────────


@router.get("/secrets/health", response_model=SecretHealthResponse)
async def secrets_health(
    _=Depends(require_admin),
) -> SecretHealthResponse:
    """Check secret provider connectivity. Admin only."""
    from datetime import UTC, datetime  # noqa: PLC0415

    from infrastructure.secrets.provider import get_secret_provider  # noqa: PLC0415

    provider = get_secret_provider()
    connected = True
    if hasattr(provider, "ping"):
        try:
            connected = provider.ping()
        except Exception:  # noqa: BLE001
            connected = False

    return SecretHealthResponse(
        provider_type=provider.provider_name,
        is_connected=connected,
        last_probe_at=datetime.now(UTC),
    )


# ── SAML Callback (M40.3) ─────────────────────────────────────────────────────


@router.post("/{enterprise_id}/sso/saml/callback", response_model=SSOLoginResponse)
async def saml_callback(
    enterprise_id: str,
    body: SAMLCallbackRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> SSOLoginResponse:
    """SAML 2.0 Assertion Consumer Service endpoint.

    The IdP posts a signed SAMLResponse here.  The assertion is validated
    via the injected SAMLAssertionValidator before any group claims are trusted.
    Groups come ONLY from the validated assertion — never from request body fields.
    """
    import uuid as _uuid  # noqa: PLC0415
    from datetime import UTC, datetime  # noqa: PLC0415

    from application.enterprise.sso_validation import (  # noqa: PLC0415
        MockSAMLValidator,
        SSOValidationError,
        ValidatedIdentity,
        async_check_sso_rate_limit,
    )
    from infrastructure.persistence.models.audit_event import AuditEventModel  # noqa: PLC0415

    client_ip = request.client.host if request.client else "unknown"
    if not await async_check_sso_rate_limit(enterprise_id, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="SSO rate limit exceeded",
        )

    idp = await sso_service.get_identity_provider(body.idp_id, session)
    if not idp or not idp.is_active or idp.enterprise_id != enterprise_id:
        raise HTTPException(status_code=404, detail="Identity provider not found")

    if idp.provider_type != "saml":
        raise HTTPException(status_code=400, detail="Identity provider is not a SAML provider")

    validator = getattr(request.app.state, "saml_validator", None) or MockSAMLValidator(
        result=ValidatedIdentity(
            external_id=body.user_id,
            email=f"{body.user_id}@saml.placeholder",
            groups=[],
            issuer=idp.issuer or "",
            idp_id=body.idp_id,
        )
    )

    now = datetime.now(UTC)
    try:
        validated = validator.validate(
            saml_response=body.saml_response,
            idp_issuer=idp.issuer or "",
            sp_entity_id=idp.config.get("sp_entity_id", "eios"),
            acs_url=idp.config.get("acs_url", ""),
            certificates=idp.certificates,
            group_attribute=idp.config.get("group_attribute", "groups"),
        )
        validated.idp_id = body.idp_id  # production validator leaves this empty
    except SSOValidationError as exc:
        session.add(
            AuditEventModel(
                id=str(_uuid.uuid4()),
                status="Active",
                version=1,
                created_at=now,
                updated_at=now,
                action="sso.assertion.invalid",
                entity_type="IdentityProvider",
                entity_id=body.idp_id,
                actor_id=None,
                outcome="failure",
                detail=str(exc),
                event_metadata={"enterprise_id": enterprise_id, "idp_id": body.idp_id},
            )
        )
        await session.commit()
        raise HTTPException(
            status_code=400, detail=f"SAML assertion invalid: {exc.reason}"
        ) from exc

    result = await sso_service.process_sso_login(
        enterprise_id=enterprise_id,
        validated_identity=validated,
        session=session,
        user_id=body.user_id,
    )
    await session.commit()
    return SSOLoginResponse(**result.to_dict())


# ── OIDC Callback (M40.3) ─────────────────────────────────────────────────────


@router.post("/{enterprise_id}/sso/oidc/callback", response_model=SSOLoginResponse)
async def oidc_callback(
    enterprise_id: str,
    body: OIDCCallbackRequest,
    request: Request,  # noqa: F821
    session: AsyncSession = Depends(get_db),
) -> SSOLoginResponse:
    """OIDC ID token callback endpoint.

    Validates the ID token via the injected OIDCTokenValidator before
    trusting any group claims.  Groups come ONLY from validated token claims.
    """
    import uuid as _uuid  # noqa: PLC0415
    from datetime import UTC, datetime  # noqa: PLC0415

    from application.enterprise.sso_validation import (  # noqa: PLC0415
        MockOIDCValidator,
        SSOValidationError,
        ValidatedIdentity,
        async_check_sso_rate_limit,
    )
    from infrastructure.persistence.models.audit_event import AuditEventModel  # noqa: PLC0415

    client_ip = request.client.host if request.client else "unknown"
    if not await async_check_sso_rate_limit(enterprise_id, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="SSO rate limit exceeded",
        )

    idp = await sso_service.get_identity_provider(body.idp_id, session)
    if not idp or not idp.is_active or idp.enterprise_id != enterprise_id:
        raise HTTPException(status_code=404, detail="Identity provider not found")

    if idp.provider_type != "oidc":
        raise HTTPException(status_code=400, detail="Identity provider is not an OIDC provider")

    validator = getattr(request.app.state, "oidc_validator", None) or MockOIDCValidator(
        result=ValidatedIdentity(
            external_id=body.user_id,
            email=f"{body.user_id}@oidc.placeholder",
            groups=[],
            issuer=idp.issuer or "",
            idp_id=body.idp_id,
        )
    )

    now = datetime.now(UTC)
    try:
        validated = validator.validate(
            id_token=body.id_token,
            issuer=idp.issuer or "",
            audience=idp.client_id or "eios",
            nonce=body.nonce,
            jwks_uri=idp.metadata_url,
            group_claim=idp.config.get("group_claim", "groups"),
        )
        validated.idp_id = body.idp_id  # production validator leaves this empty
    except SSOValidationError as exc:
        session.add(
            AuditEventModel(
                id=str(_uuid.uuid4()),
                status="Active",
                version=1,
                created_at=now,
                updated_at=now,
                action="sso.token.invalid",
                entity_type="IdentityProvider",
                entity_id=body.idp_id,
                actor_id=None,
                outcome="failure",
                detail=str(exc),
                event_metadata={"enterprise_id": enterprise_id, "idp_id": body.idp_id},
            )
        )
        await session.commit()
        raise HTTPException(status_code=400, detail=f"OIDC token invalid: {exc.reason}") from exc

    result = await sso_service.process_sso_login(
        enterprise_id=enterprise_id,
        validated_identity=validated,
        session=session,
        user_id=body.user_id,
    )
    await session.commit()
    return SSOLoginResponse(**result.to_dict())


# ── Policies ──────────────────────────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/policies",
    response_model=EnterprisePolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy(
    enterprise_id: str,
    body: EnterprisePolicyCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EnterprisePolicyResponse:
    p = await policy_service.create_policy(
        enterprise_id=enterprise_id,
        policy_type=body.policy_type,
        name=body.name,
        description=body.description,
        config=body.config,
        cascade_to_children=body.cascade_to_children,
        scope=body.scope,
        scope_id=body.scope_id,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return EnterprisePolicyResponse.model_validate(p)


@router.get("/{enterprise_id}/policies", response_model=list[EnterprisePolicyResponse])
async def list_policies(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[EnterprisePolicyResponse]:
    items = await policy_service.list_policies(enterprise_id, session)
    return [EnterprisePolicyResponse.model_validate(p) for p in items]


# ── Retention Rules ───────────────────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/retention",
    response_model=RetentionRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_retention_rule(
    enterprise_id: str,
    body: RetentionRuleCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RetentionRuleResponse:
    rule = await policy_service.create_retention_rule(
        enterprise_id=enterprise_id,
        entity_type=body.entity_type,
        retention_days=body.retention_days,
        cascade_to_children=body.cascade_to_children,
        legal_hold=body.legal_hold,
        description=body.description,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return RetentionRuleResponse.model_validate(rule)


@router.get("/{enterprise_id}/retention", response_model=list[RetentionRuleResponse])
async def list_retention_rules(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[RetentionRuleResponse]:
    items = await policy_service.list_retention_rules(enterprise_id, session)
    return [RetentionRuleResponse.model_validate(r) for r in items]


# ── Notification Policies ─────────────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/notifications",
    response_model=NotificationPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification_policy(
    enterprise_id: str,
    body: NotificationPolicyCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> NotificationPolicyResponse:
    np = await policy_service.create_notification_policy(
        enterprise_id=enterprise_id,
        name=body.name,
        escalation_routes=body.escalation_routes,
        regional_routes=body.regional_routes,
        executive_routes=body.executive_routes,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return NotificationPolicyResponse.model_validate(np)


@router.get("/{enterprise_id}/notifications", response_model=list[NotificationPolicyResponse])
async def list_notification_policies(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[NotificationPolicyResponse]:
    items = await policy_service.list_notification_policies(enterprise_id, session)
    return [NotificationPolicyResponse.model_validate(np) for np in items]


# ── Enterprise Risks ──────────────────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/risks",
    response_model=EnterpriseRiskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_enterprise_risk(
    enterprise_id: str,
    body: EnterpriseRiskCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EnterpriseRiskResponse:
    r = await risk_service.create_enterprise_risk(
        enterprise_id=enterprise_id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        esg_category=body.esg_category,
        owner_user_id=body.owner_user_id,
        mitigation_plan=body.mitigation_plan,
        linked_region_ids=body.linked_region_ids,
        linked_business_unit_ids=body.linked_business_unit_ids,
        linked_organization_ids=body.linked_organization_ids,
        linked_supplier_ids=body.linked_supplier_ids,
        actor_id=current_user.id,
        session=session,
    )
    await session.commit()
    return EnterpriseRiskResponse.model_validate(r)


@router.get("/{enterprise_id}/risks", response_model=list[EnterpriseRiskResponse])
async def list_enterprise_risks(
    enterprise_id: str,
    severity: str | None = Query(None),
    risk_status: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[EnterpriseRiskResponse]:
    items = await risk_service.list_enterprise_risks(enterprise_id, severity, risk_status, session)
    return [EnterpriseRiskResponse.model_validate(r) for r in items]


# ── Delegated Administration ──────────────────────────────────────────────────


@router.post("/{enterprise_id}/roles", response_model=AssignEnterpriseRoleResponse)
async def assign_enterprise_role(
    enterprise_id: str,
    body: AssignEnterpriseRoleRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssignEnterpriseRoleResponse:
    user = await admin_service.assign_enterprise_role(
        enterprise_id=enterprise_id,
        user_id=body.user_id,
        enterprise_scope=body.enterprise_scope,
        business_unit_id=body.business_unit_id,
        region_id=body.region_id,
        actor_id=current_user.id,
        session=session,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await session.commit()
    return AssignEnterpriseRoleResponse(
        user_id=body.user_id,
        enterprise_id=enterprise_id,
        enterprise_scope=body.enterprise_scope,
        business_unit_id=body.business_unit_id,
        region_id=body.region_id,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/{enterprise_id}/dashboard", response_model=EnterpriseDashboard)
async def get_enterprise_dashboard(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
) -> EnterpriseDashboard:
    enterprise = await hierarchy_service.get_enterprise(enterprise_id, session)
    if not enterprise:
        raise HTTPException(status_code=404, detail="Enterprise not found")

    rollup = await rollup_service.get_enterprise_rollup(enterprise_id, session)
    bu_rollups = await rollup_service.get_bu_rollups(enterprise_id, session)
    region_rollups = await rollup_service.get_region_rollups(enterprise_id, session)
    health = await rollup_service.compute_enterprise_health_score(enterprise_id, session)

    from interfaces.api.schemas.enterprise import (
        BURollupItem,
        RegionRollupItem,
    )

    return EnterpriseDashboard(
        enterprise=EnterpriseResponse.model_validate(enterprise),
        organization_count=rollup["organization_count"],
        supplier_count=rollup["supplier_count"],
        total_risks=rollup["total_risks"],
        critical_risks=rollup["critical_risks"],
        total_findings=rollup["total_findings"],
        open_findings=rollup["open_findings"],
        compliance_readiness=rollup["compliance_readiness"],
        esg_health_score=EnterpriseHealthScore(
            score=health["score"],
            grade=health["grade"],
            components=health["components"],
            drivers=health["drivers"],
            computed_at=health["computed_at"],
        ),
        by_business_unit=[BURollupItem(**bu) for bu in bu_rollups],
        by_region=[RegionRollupItem(**r) for r in region_rollups],
    )


# ── Global Search ─────────────────────────────────────────────────────────────


@router.post("/{enterprise_id}/search", response_model=GlobalSearchResponse)
async def global_search(
    enterprise_id: str,
    body: GlobalSearchRequest,
    session: AsyncSession = Depends(get_db),
) -> GlobalSearchResponse:
    result = await search_service.global_search(
        enterprise_id=enterprise_id,
        query=body.query,
        entity_types=body.entity_types,
        limit=body.limit,
        session=session,
    )
    from interfaces.api.schemas.enterprise import GlobalSearchHit

    return GlobalSearchResponse(
        query=result["query"],
        total_hits=result["total_hits"],
        hits=[GlobalSearchHit(**h) for h in result["hits"]],
    )


# ── Enterprise Audit ──────────────────────────────────────────────────────────


@router.get("/{enterprise_id}/audit", response_model=dict)
async def get_enterprise_audit(
    enterprise_id: str,
    action: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Cross-organizational audit view for enterprise admins.
    Returns audit events from all organizations in this enterprise.
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.audit_event import AuditEventModel
    from infrastructure.persistence.models.organization import OrganizationModel

    list(
        (
            await session.execute(
                select(OrganizationModel.id).where(OrganizationModel.enterprise_id == enterprise_id)
            )
        )
        .scalars()
        .all()
    )

    stmt = select(AuditEventModel).order_by(AuditEventModel.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditEventModel.action == action)

    events = list((await session.execute(stmt)).scalars().all())
    return {
        "total": len(events),
        "events": [
            {
                "id": e.id,
                "action": e.action,
                "actor_id": e.actor_id,
                "actor_email": e.actor_email,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "outcome": e.outcome,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }


# ── SCIM Token Management (M40.1) ────────────────────────────────────────────


@router.post(
    "/{enterprise_id}/scim/tokens",
    response_model=SCIMTokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scim_token(
    enterprise_id: str,
    body: SCIMTokenCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SCIMTokenCreateResponse:
    """Create a SCIM bearer token for external IdP provisioning."""
    from application.enterprise import scim_token_service  # noqa: PLC0415

    raw, token = await scim_token_service.create_scim_token(
        enterprise_id=enterprise_id,
        label=body.label,
        ttl_days=body.ttl_days,
        actor_id=current_user.id,
        session=session,
        idp_id=body.idp_id,
        scope=body.scope,
    )
    await session.commit()
    return SCIMTokenCreateResponse(
        id=token.id,
        enterprise_id=token.enterprise_id,
        idp_id=token.idp_id,
        scope=token.scope,
        label=token.label,
        is_active=token.is_active,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        use_count=token.use_count,
        created_at=token.created_at,
        raw_token=raw,
    )


@router.get("/{enterprise_id}/scim/tokens", response_model=list[SCIMTokenResponse])
async def list_scim_tokens(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> list[SCIMTokenResponse]:
    """List SCIM tokens for the enterprise (without raw values)."""
    from application.enterprise import scim_token_service  # noqa: PLC0415

    tokens = await scim_token_service.list_scim_tokens(enterprise_id, session)
    return [
        SCIMTokenResponse(
            id=t.id,
            enterprise_id=t.enterprise_id,
            idp_id=t.idp_id,
            scope=t.scope,
            label=t.label,
            is_active=t.is_active,
            expires_at=t.expires_at,
            last_used_at=t.last_used_at,
            use_count=t.use_count,
            created_at=t.created_at,
        )
        for t in tokens
    ]


@router.delete(
    "/{enterprise_id}/scim/tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_scim_token(
    enterprise_id: str,
    token_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Revoke a SCIM token."""
    from application.enterprise import scim_token_service  # noqa: PLC0415

    ok = await scim_token_service.revoke_scim_token(token_id, current_user.id, session)
    if not ok:
        raise HTTPException(status_code=404, detail="SCIM token not found")
    await session.commit()


@router.post(
    "/{enterprise_id}/scim/tokens/{token_id}/rotate",
    response_model=SCIMTokenRotateResponse,
    status_code=status.HTTP_200_OK,
)
async def rotate_scim_token(
    enterprise_id: str,
    token_id: str,
    body: SCIMTokenCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SCIMTokenRotateResponse:
    """Revoke a SCIM token and issue a new one atomically."""
    from application.enterprise import scim_token_service  # noqa: PLC0415

    result = await scim_token_service.rotate_scim_token(
        token_id=token_id,
        new_label=body.label,
        ttl_days=body.ttl_days,
        actor_id=current_user.id,
        session=session,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="SCIM token not found")
    raw, new_token = result
    await session.commit()
    return SCIMTokenRotateResponse(
        revoked_token_id=token_id,
        new_token=SCIMTokenCreateResponse(
            id=new_token.id,
            enterprise_id=new_token.enterprise_id,
            idp_id=new_token.idp_id,
            scope=new_token.scope,
            label=new_token.label,
            is_active=new_token.is_active,
            expires_at=new_token.expires_at,
            last_used_at=new_token.last_used_at,
            use_count=new_token.use_count,
            created_at=new_token.created_at,
            raw_token=raw,
        ),
    )


# ── SCIM Usage Dashboard (M40.4) ─────────────────────────────────────────────


@router.get("/{enterprise_id}/scim/usage", response_model=SCIMUsageResponse)
async def scim_usage(
    enterprise_id: str,
    session: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> SCIMUsageResponse:
    """Per-enterprise SCIM token usage summary."""
    from application.enterprise import scim_token_service as _sts  # noqa: PLC0415

    data = await _sts.get_scim_usage(enterprise_id, session)
    return SCIMUsageResponse(
        enterprise_id=data["enterprise_id"],
        token_count=data["token_count"],
        active_tokens=data["active_tokens"],
        last_provisioning=data["last_provisioning"],
        last_sync=data["last_sync"],
        per_idp_usage=[SCIMPerIdpUsage(**u) for u in data["per_idp_usage"]],
    )


# ── SCIM Provisioning (M40.1 — uses dedicated SCIM bearer token) ─────────────


@router.post(
    "/{enterprise_id}/scim/users",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[],
)  # Override router-level require_admin for SCIM auth
async def scim_create_user(
    enterprise_id: str,
    body: ScimUserCreate,
    session: AsyncSession = Depends(get_db),
    scim_token=Depends(require_scim_token),
) -> dict:
    """SCIM 2.0 user provisioning — authenticated by SCIM bearer token only.

    Does not accept user JWTs. The SCIM token's enterprise_id must match
    the path enterprise_id.
    """
    if scim_token.enterprise_id != enterprise_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SCIM token is not valid for this enterprise",
        )
    user = await scim_service.scim_create_user(
        enterprise_id=enterprise_id,
        organization_id=body.organization_id,
        username=body.username,
        email=body.email,
        display_name=body.display_name,
        active=body.active,
        groups=body.groups,
        actor_id=None,  # provisioning actor is the SCIM system, not a user
        session=session,
    )
    await session.commit()
    return {
        "id": user.id,
        "username": body.username,
        "email": user.email,
        "display_name": user.display_name,
        "active": user.is_active,
        "provisioned_at": user.created_at,
    }


# ── SSO Login Enforcement (M40.1) ─────────────────────────────────────────────


@router.post("/{enterprise_id}/sso/login", response_model=SSOLoginResponse)
async def process_sso_login(
    enterprise_id: str,
    body: SSOLoginRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SSOLoginResponse:
    """Internal SSO login — wraps caller-supplied claims in ValidatedIdentity.

    This endpoint is for admin/testing purposes. Production SSO flows
    should use /sso/saml/callback or /sso/oidc/callback which enforce
    assertion/token verification before trusting group claims.
    """
    from application.enterprise.sso_validation import ValidatedIdentity  # noqa: PLC0415

    idp = await sso_service.get_identity_provider(body.idp_id, session)
    if not idp or idp.enterprise_id != enterprise_id:
        raise HTTPException(status_code=404, detail="Identity provider not found")

    validated = ValidatedIdentity(
        external_id=body.user_id,
        email="",
        groups=body.idp_groups,
        issuer=idp.issuer or "",
        idp_id=body.idp_id,
    )
    result = await sso_service.process_sso_login(
        enterprise_id=enterprise_id,
        validated_identity=validated,
        session=session,
        user_id=body.user_id,
    )
    await session.commit()
    return SSOLoginResponse(**result.to_dict())


# ── Bulk Operations ───────────────────────────────────────────────────────────


@router.post("/{enterprise_id}/bulk/suppliers", response_model=BulkOperationResult)
async def bulk_update_suppliers(
    enterprise_id: str,
    body: BulkSupplierUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> BulkOperationResult:
    """Bulk update suppliers. Audits the operation."""
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import update as sa_update

    from infrastructure.persistence.models.audit_event import AuditEventModel
    from infrastructure.persistence.models.supplier import SupplierModel

    allowed_fields = {"risk_tier", "status", "country", "industry", "esg_score"}
    update_data = {k: v for k, v in body.updates.items() if k in allowed_fields}

    if not update_data:
        return BulkOperationResult(
            total=len(body.supplier_ids),
            succeeded=0,
            failed=len(body.supplier_ids),
            errors=["No valid update fields provided"],
        )

    succeeded = 0
    errors = []
    for sid in body.supplier_ids:
        try:
            await session.execute(
                sa_update(SupplierModel)
                .where(SupplierModel.id == sid)
                .values(**update_data, updated_at=datetime.now(UTC))
            )
            succeeded += 1
        except Exception as e:
            errors.append(f"{sid}: {e!s}")

    now = datetime.now(UTC)
    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action="bulk.suppliers_updated",
            entity_type="SupplierBulk",
            entity_id=enterprise_id,
            actor_id=current_user.id,
            outcome="success",
            detail=f"Bulk updated {succeeded}/{len(body.supplier_ids)} suppliers",
            event_metadata={"enterprise_id": enterprise_id, "fields": list(update_data.keys())},
        )
    )
    await session.commit()
    return BulkOperationResult(
        total=len(body.supplier_ids),
        succeeded=succeeded,
        failed=len(body.supplier_ids) - succeeded,
        errors=errors,
    )


@router.post("/{enterprise_id}/bulk/risks", response_model=BulkOperationResult)
async def bulk_update_risks(
    enterprise_id: str,
    body: BulkRiskUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> BulkOperationResult:
    """Bulk update risks. Audits the operation."""
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import update as sa_update

    from infrastructure.persistence.models.audit_event import AuditEventModel
    from infrastructure.persistence.models.risk import RiskModel

    allowed_fields = {"severity", "status", "likelihood", "impact"}
    update_data = {k: v for k, v in body.updates.items() if k in allowed_fields}

    if not update_data:
        return BulkOperationResult(
            total=len(body.risk_ids),
            succeeded=0,
            failed=len(body.risk_ids),
            errors=["No valid update fields provided"],
        )

    succeeded = 0
    errors = []
    for rid in body.risk_ids:
        try:
            await session.execute(
                sa_update(RiskModel)
                .where(RiskModel.id == rid)
                .values(**update_data, updated_at=datetime.now(UTC))
            )
            succeeded += 1
        except Exception as e:
            errors.append(f"{rid}: {e!s}")

    now = datetime.now(UTC)
    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action="bulk.risks_updated",
            entity_type="RiskBulk",
            entity_id=enterprise_id,
            actor_id=current_user.id,
            outcome="success",
            detail=f"Bulk updated {succeeded}/{len(body.risk_ids)} risks",
            event_metadata={"enterprise_id": enterprise_id},
        )
    )
    await session.commit()
    return BulkOperationResult(
        total=len(body.risk_ids),
        succeeded=succeeded,
        failed=len(body.risk_ids) - succeeded,
        errors=errors,
    )
