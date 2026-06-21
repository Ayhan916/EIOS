"""M40 — Enterprise Multi-Tenant Scale API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Enums (string literals used throughout) ───────────────────────────────────

DATA_RESIDENCY_VALUES = ("EU", "UK", "US", "APAC")
DATA_CLASSIFICATION_VALUES = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED")
PROVIDER_TYPE_VALUES = ("saml", "oidc")
POLICY_TYPE_VALUES = (
    "retention",
    "evidence_requirements",
    "supplier_onboarding",
    "risk_acceptance",
    "custom",
)
ENTERPRISE_RISK_SEVERITY_VALUES = ("critical", "high", "medium", "low")
ENTERPRISE_SCOPE_VALUES = ("enterprise", "business_unit", "region", "organization")


# ── Enterprise ────────────────────────────────────────────────────────────────


class EnterpriseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    hq_country: str | None = Field(None, max_length=10)
    industry: str | None = None
    default_data_residency: str = Field("EU", pattern="^(EU|UK|US|APAC)$")
    default_data_classification: str = Field(
        "INTERNAL", pattern="^(PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED)$"
    )
    settings: dict[str, Any] = Field(default_factory=dict)


class EnterpriseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    hq_country: str | None = None
    industry: str | None = None
    default_data_residency: str | None = None
    default_data_classification: str | None = None
    settings: dict[str, Any] | None = None
    is_active: bool | None = None


class EnterpriseResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    hq_country: str | None = None
    industry: str | None = None
    default_data_residency: str
    default_data_classification: str
    is_active: bool
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── BusinessUnit ──────────────────────────────────────────────────────────────


class BusinessUnitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    region_scope: str | None = None
    admin_user_id: str | None = None


class BusinessUnitResponse(BaseModel):
    id: str
    enterprise_id: str
    name: str
    description: str | None = None
    region_scope: str | None = None
    admin_user_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── LegalEntity ───────────────────────────────────────────────────────────────


class LegalEntityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    country: str | None = Field(None, max_length=10)
    registration_number: str | None = None
    legal_form: str | None = None


class LegalEntityResponse(BaseModel):
    id: str
    enterprise_id: str
    name: str
    description: str | None = None
    country: str | None = None
    registration_number: str | None = None
    legal_form: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Region ────────────────────────────────────────────────────────────────────


class RegionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    description: str | None = None
    data_residency: str = Field("EU", pattern="^(EU|UK|US|APAC)$")
    admin_user_id: str | None = None


class RegionResponse(BaseModel):
    id: str
    enterprise_id: str
    name: str
    code: str
    description: str | None = None
    data_residency: str
    admin_user_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── IdentityProvider ──────────────────────────────────────────────────────────


class IdentityProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider_type: str = Field(..., pattern="^(saml|oidc)$")
    issuer: str | None = None
    metadata_url: str | None = None
    client_id: str | None = None
    # client_secret accepted on create/update but NEVER returned in responses
    client_secret: str | None = None
    certificates: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class IdentityProviderResponse(BaseModel):
    id: str
    enterprise_id: str
    name: str
    provider_type: str
    issuer: str | None = None
    metadata_url: str | None = None
    client_id: str | None = None
    # client_secret intentionally omitted — never returned
    has_client_secret: bool = False
    certificates: list[str]
    config: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── GroupMapping ──────────────────────────────────────────────────────────────


class GroupMappingCreate(BaseModel):
    idp_group: str = Field(..., min_length=1, max_length=500)
    mapped_role: str = Field(..., min_length=1, max_length=100)
    scope: str | None = None
    business_unit_id: str | None = None
    region_id: str | None = None


class GroupMappingResponse(BaseModel):
    id: str
    idp_id: str
    enterprise_id: str
    idp_group: str
    mapped_role: str
    scope: str | None = None
    business_unit_id: str | None = None
    region_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── EnterprisePolicy ──────────────────────────────────────────────────────────


class EnterprisePolicyCreate(BaseModel):
    policy_type: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    cascade_to_children: bool = True
    scope: str = "all"
    scope_id: str | None = None


class EnterprisePolicyResponse(BaseModel):
    id: str
    enterprise_id: str
    policy_type: str
    name: str
    description: str | None = None
    config: dict[str, Any]
    cascade_to_children: bool
    scope: str
    scope_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── RetentionRule ─────────────────────────────────────────────────────────────


class RetentionRuleCreate(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=100)
    retention_days: int = Field(..., ge=1, le=36500)
    cascade_to_children: bool = True
    legal_hold: bool = False
    description: str | None = None


class RetentionRuleResponse(BaseModel):
    id: str
    enterprise_id: str
    entity_type: str
    retention_days: int
    cascade_to_children: bool
    legal_hold: bool
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── NotificationPolicy ────────────────────────────────────────────────────────


class NotificationPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    escalation_routes: list[dict[str, Any]] = Field(default_factory=list)
    regional_routes: dict[str, Any] = Field(default_factory=dict)
    executive_routes: list[dict[str, Any]] = Field(default_factory=list)


class NotificationPolicyResponse(BaseModel):
    id: str
    enterprise_id: str
    name: str
    escalation_routes: list[dict[str, Any]]
    regional_routes: dict[str, Any]
    executive_routes: list[dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── EnterpriseRisk ────────────────────────────────────────────────────────────


class EnterpriseRiskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    severity: str = Field("medium", pattern="^(critical|high|medium|low)$")
    esg_category: str | None = None
    owner_user_id: str | None = None
    mitigation_plan: str | None = None
    linked_region_ids: list[str] = Field(default_factory=list)
    linked_business_unit_ids: list[str] = Field(default_factory=list)
    linked_organization_ids: list[str] = Field(default_factory=list)
    linked_supplier_ids: list[str] = Field(default_factory=list)


class EnterpriseRiskResponse(BaseModel):
    id: str
    enterprise_id: str
    title: str
    description: str | None = None
    severity: str
    risk_status: str
    esg_category: str | None = None
    owner_user_id: str | None = None
    mitigation_plan: str | None = None
    linked_region_ids: list[str]
    linked_business_unit_ids: list[str]
    linked_organization_ids: list[str]
    linked_supplier_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── SCIM ──────────────────────────────────────────────────────────────────────


class ScimUserCreate(BaseModel):
    username: str
    email: str
    display_name: str
    organization_id: str
    active: bool = True
    groups: list[str] = Field(default_factory=list)


class ScimUserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    active: bool
    provisioned_at: datetime

    model_config = {"from_attributes": True}


# ── SCIM Tokens (M40.1 / M40.4) ──────────────────────────────────────────────

SCIM_SCOPE_VALUES = ("READ_ONLY", "PROVISIONING", "FULL_ADMIN")


class SCIMTokenCreate(BaseModel):
    label: str | None = None
    ttl_days: int = Field(365, ge=0, description="0 = no expiry")
    # M40.4: bind to a specific IdP; None = enterprise-wide (backward compat)
    idp_id: str | None = None
    # M40.4: scope of operations this token may perform
    scope: str = Field("FULL_ADMIN", pattern="^(READ_ONLY|PROVISIONING|FULL_ADMIN)$")


class SCIMTokenResponse(BaseModel):
    id: str
    enterprise_id: str
    idp_id: str | None = None
    scope: str = "FULL_ADMIN"
    label: str | None = None
    is_active: bool
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    use_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SCIMTokenCreateResponse(SCIMTokenResponse):
    """Returned only on token creation — raw_token never returned again."""
    raw_token: str


class SCIMTokenRotateResponse(BaseModel):
    revoked_token_id: str
    new_token: SCIMTokenCreateResponse


# ── SCIM Usage Dashboard (M40.4) ──────────────────────────────────────────────


class SCIMPerIdpUsage(BaseModel):
    idp_id: str | None = None
    token_count: int = 0
    active_count: int = 0
    last_used_at: datetime | None = None


class SCIMUsageResponse(BaseModel):
    enterprise_id: str
    token_count: int = 0
    active_tokens: int = 0
    last_provisioning: datetime | None = None
    last_sync: datetime | None = None
    per_idp_usage: list[SCIMPerIdpUsage] = Field(default_factory=list)


# ── SSO Login (M40.1) ─────────────────────────────────────────────────────────


class SSOLoginRequest(BaseModel):
    idp_id: str
    user_id: str
    idp_groups: list[str] = Field(default_factory=list)


class SSOLoginResponse(BaseModel):
    user_id: str
    applied_role: str
    enterprise_scope: str | None = None
    enterprise_id: str | None = None
    business_unit_id: str | None = None
    region_id: str | None = None
    matched_groups: list[str]


# ── SAML / OIDC Callbacks (M40.3) ────────────────────────────────────────────


class SAMLCallbackRequest(BaseModel):
    """Posted by the IdP to the SAML ACS endpoint."""
    idp_id: str
    user_id: str
    # base64-encoded SAMLResponse from the IdP
    saml_response: str = Field(..., min_length=1)
    relay_state: str | None = None


class OIDCCallbackRequest(BaseModel):
    """Posted after the OIDC authorization code exchange."""
    idp_id: str
    user_id: str
    # ID token returned by the OIDC token endpoint
    id_token: str = Field(..., min_length=1)
    nonce: str | None = None


# ── Secret Rotation (M40.2) ───────────────────────────────────────────────────


class SecretRotateRequest(BaseModel):
    new_client_secret: str = Field(..., min_length=1)


class SecretRotateResponse(BaseModel):
    idp_id: str
    new_reference_id: str
    rotated_at: datetime


# ── Secret Health (M40.2) ─────────────────────────────────────────────────────


class SecretHealthResponse(BaseModel):
    provider_type: str
    is_connected: bool
    last_probe_at: datetime


# ── SecretReference (M40.1) ───────────────────────────────────────────────────


class SecretReferenceResponse(BaseModel):
    id: str
    provider: str
    label: str | None = None
    reference_created_at: datetime

    model_config = {"from_attributes": True}


# ── Enterprise Rollup / Dashboard ─────────────────────────────────────────────


class OrgRollupItem(BaseModel):
    organization_id: str
    organization_name: str
    supplier_count: int = 0
    risk_count: int = 0
    finding_count: int = 0
    assessment_count: int = 0
    compliance_readiness: float = 0.0
    data_residency: str | None = None
    data_classification: str = "INTERNAL"


class BURollupItem(BaseModel):
    business_unit_id: str
    business_unit_name: str
    organization_count: int = 0
    supplier_count: int = 0
    risk_count: int = 0
    compliance_readiness: float = 0.0


class RegionRollupItem(BaseModel):
    region_id: str
    region_name: str
    region_code: str
    data_residency: str
    organization_count: int = 0
    supplier_count: int = 0
    risk_count: int = 0


class EnterpriseHealthScore(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0)
    grade: str  # A / B / C / D / F
    components: dict[str, float] = Field(default_factory=dict)
    # Explainability: which factors drove the score
    drivers: list[str] = Field(default_factory=list)
    computed_at: datetime


class EnterpriseDashboard(BaseModel):
    enterprise: EnterpriseResponse
    organization_count: int = 0
    supplier_count: int = 0
    total_risks: int = 0
    critical_risks: int = 0
    total_findings: int = 0
    open_findings: int = 0
    compliance_readiness: float = 0.0
    esg_health_score: EnterpriseHealthScore | None = None
    by_business_unit: list[BURollupItem] = Field(default_factory=list)
    by_region: list[RegionRollupItem] = Field(default_factory=list)
    due_diligence_coverage: float = 0.0
    supplier_concentration_top5_pct: float = 0.0


# ── Global Search ─────────────────────────────────────────────────────────────


class GlobalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    entity_types: list[str] = Field(
        default_factory=lambda: ["suppliers", "risks", "findings", "actions", "reports"]
    )
    limit: int = Field(20, ge=1, le=100)


class GlobalSearchHit(BaseModel):
    entity_type: str
    entity_id: str
    organization_id: str
    title: str
    snippet: str | None = None
    score: float = 1.0


class GlobalSearchResponse(BaseModel):
    query: str
    total_hits: int
    hits: list[GlobalSearchHit]


# ── Bulk Operations ───────────────────────────────────────────────────────────


class BulkSupplierUpdate(BaseModel):
    supplier_ids: list[str] = Field(..., min_length=1, max_length=500)
    updates: dict[str, Any]


class BulkRiskUpdate(BaseModel):
    risk_ids: list[str] = Field(..., min_length=1, max_length=500)
    updates: dict[str, Any]


class BulkOperationResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    errors: list[str] = Field(default_factory=list)


# ── Export ────────────────────────────────────────────────────────────────────


class ExportRequest(BaseModel):
    entity_type: str = Field(..., pattern="^(suppliers|risks|findings|assessments|reports)$")
    format: str = Field("csv", pattern="^(csv|xlsx)$")
    filters: dict[str, Any] = Field(default_factory=dict)


# ── Assign Enterprise Role ────────────────────────────────────────────────────


class AssignEnterpriseRoleRequest(BaseModel):
    user_id: str
    # enterprise_admin | bu_admin | regional_admin
    enterprise_scope: str = Field(..., pattern="^(enterprise_admin|bu_admin|regional_admin)$")
    business_unit_id: str | None = None
    region_id: str | None = None


class AssignEnterpriseRoleResponse(BaseModel):
    user_id: str
    enterprise_id: str
    enterprise_scope: str
    business_unit_id: str | None = None
    region_id: str | None = None


# ── Enterprise Audit ──────────────────────────────────────────────────────────


class EnterpriseAuditEntry(BaseModel):
    id: str
    action: str
    actor_id: str | None = None
    actor_email: str | None = None
    entity_type: str
    entity_id: str
    outcome: str
    organization_id: str | None = None
    created_at: datetime


class EnterpriseAuditResponse(BaseModel):
    total: int
    events: list[EnterpriseAuditEntry]


# ── Link Organization to Enterprise ──────────────────────────────────────────


class LinkOrganizationRequest(BaseModel):
    organization_id: str
    business_unit_id: str | None = None
    legal_entity_id: str | None = None
    region_id: str | None = None
    data_residency: str | None = Field(None, pattern="^(EU|UK|US|APAC)$")
    data_classification: str | None = Field(
        None, pattern="^(PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED)$"
    )
