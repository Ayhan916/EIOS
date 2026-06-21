"""M40 / M40.1 — Enterprise Multi-Tenant Scale & Identity Hardening ORM Models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class EnterpriseModel(BaseModel):
    """Top-level enterprise entity — parent of all organizations."""

    __tablename__ = "enterprises"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ISO 3166-1 alpha-2 headquarters country
    hq_country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # EU / UK / US / APAC — default residency for new orgs
    default_data_residency: Mapped[str] = mapped_column(String(10), nullable=False, default="EU")
    # PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED
    default_data_classification: Mapped[str] = mapped_column(
        String(20), nullable=False, default="INTERNAL"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # JSON bag for enterprise-level settings
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    business_units: Mapped[list[BusinessUnitModel]] = relationship(back_populates="enterprise")
    legal_entities: Mapped[list[LegalEntityModel]] = relationship(back_populates="enterprise")
    regions: Mapped[list[RegionModel]] = relationship(back_populates="enterprise")
    identity_providers: Mapped[list[IdentityProviderModel]] = relationship(
        back_populates="enterprise"
    )
    policies: Mapped[list[EnterprisePolicyModel]] = relationship(back_populates="enterprise")
    retention_rules: Mapped[list[RetentionRuleModel]] = relationship(back_populates="enterprise")
    notification_policies: Mapped[list[NotificationPolicyModel]] = relationship(
        back_populates="enterprise"
    )
    enterprise_risks: Mapped[list[EnterpriseRiskModel]] = relationship(back_populates="enterprise")


class BusinessUnitModel(BaseModel):
    """Subdivision of an Enterprise — may contain many Organizations."""

    __tablename__ = "business_units"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # e.g. EMEA, APAC, Americas
    region_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # admin user id
    admin_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    enterprise: Mapped[EnterpriseModel] = relationship(back_populates="business_units")


class LegalEntityModel(BaseModel):
    """Legal entity within an Enterprise (subsidiary, branch, holding company)."""

    __tablename__ = "legal_entities"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ISO 3166-1 alpha-2
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    enterprise: Mapped[EnterpriseModel] = relationship(back_populates="legal_entities")


class RegionModel(BaseModel):
    """Operational region within an Enterprise (EU, UK, US, APAC, custom)."""

    __tablename__ = "enterprise_regions"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Data residency zone for this region
    data_residency: Mapped[str] = mapped_column(String(10), nullable=False, default="EU")
    admin_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    enterprise: Mapped[EnterpriseModel] = relationship(back_populates="regions")


class IdentityProviderModel(BaseModel):
    """SSO Identity Provider configuration (SAML 2.0 / OpenID Connect)."""

    __tablename__ = "identity_providers"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # saml / oidc
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # OIDC client_id (non-secret)
    client_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # FK to secret_references — raw value never stored in this table
    secret_reference_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("secret_references.id"), nullable=True
    )
    # JSON list of PEM certificates for signature verification
    certificates: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # JSON: attribute_mapping, role_claim, group_claim, etc.
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    enterprise: Mapped[EnterpriseModel] = relationship(back_populates="identity_providers")
    group_mappings: Mapped[list[GroupMappingModel]] = relationship(back_populates="idp")


class GroupMappingModel(BaseModel):
    """Map an IdP group to a role, scope, business unit, or region."""

    __tablename__ = "group_mappings"

    idp_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("identity_providers.id"), nullable=False
    )
    enterprise_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # IdP group name / claim value
    idp_group: Mapped[str] = mapped_column(String(500), nullable=False)
    # Target RBAC role
    mapped_role: Mapped[str] = mapped_column(String(100), nullable=False)
    # Optional scope narrowing
    scope: Mapped[str | None] = mapped_column(String(50), nullable=True)
    business_unit_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    region_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    idp: Mapped[IdentityProviderModel] = relationship(back_populates="group_mappings")


class EnterprisePolicyModel(BaseModel):
    """Enterprise-level governance policy that may cascade to child orgs."""

    __tablename__ = "enterprise_policies"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    # retention | evidence_requirements | supplier_onboarding | risk_acceptance | custom
    policy_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Policy body as JSON
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Whether the policy cascades to child organizations
    cascade_to_children: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Optional scope: all | business_unit | legal_entity | region
    scope: Mapped[str] = mapped_column(String(50), nullable=False, default="all")
    scope_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    enterprise: Mapped[EnterpriseModel] = relationship(back_populates="policies")


class RetentionRuleModel(BaseModel):
    """Data retention rule for a specific entity type."""

    __tablename__ = "retention_rules"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    # audit_events | reports | evidence | messages | assessments | findings
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Number of days to retain
    retention_days: Mapped[int] = mapped_column(nullable=False, default=365)
    # Whether rule cascades to all organizations in hierarchy
    cascade_to_children: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Legal hold: never delete regardless of retention_days
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    enterprise: Mapped[EnterpriseModel] = relationship(back_populates="retention_rules")


class NotificationPolicyModel(BaseModel):
    """Enterprise notification routing policy."""

    __tablename__ = "notification_policies"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Escalation routing: JSON list of {severity, route_to_role, delay_hours}
    escalation_routes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Regional routing: JSON map of region_code → email/role
    regional_routes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Executive routing: JSON list of {trigger, route_to_role}
    executive_routes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    enterprise: Mapped[EnterpriseModel] = relationship(back_populates="notification_policies")


class EnterpriseRiskModel(BaseModel):
    """Cross-organizational strategic risk in the enterprise risk register."""

    __tablename__ = "enterprise_risks"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # critical | high | medium | low
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # open | mitigating | closed
    risk_status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    # JSON lists of linked entity IDs
    linked_region_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    linked_business_unit_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    linked_organization_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    linked_supplier_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # ESG category: environmental | social | governance
    esg_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Mitigation plan
    mitigation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)

    enterprise: Mapped[EnterpriseModel] = relationship(back_populates="enterprise_risks")


class SecretReferenceModel(BaseModel):
    """Pointer to a secret stored in an external secret provider.

    The database stores (provider_name, identifier) only.
    The raw secret value is never persisted here — it lives in the
    configured SecretProvider (env var, KMS, Vault, etc.).
    """

    __tablename__ = "secret_references"

    # Short name of the provider that holds this secret (e.g. "environment", "aws_kms")
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # Provider-specific key/identifier used to retrieve the secret
    secret_identifier: Mapped[str] = mapped_column(String(500), nullable=False)
    # Human-readable label (e.g. "IdP client_secret for Azure AD")
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # ISO-8601 timestamp of when the reference was created
    reference_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class SCIMTokenModel(BaseModel):
    """SCIM 2.0 bearer token for external IdP provisioning calls.

    Raw token is returned ONCE on creation and never stored.
    Only the SHA-256 hash is persisted.

    M40.4: idp_id binds the token to a specific IdentityProvider.
           scope controls what operations the token may perform.
    """

    __tablename__ = "scim_tokens"

    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=False
    )
    # M40.4: FK to identity_providers — nullable for backward compat with pre-M40.4 tokens
    idp_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("identity_providers.id"), nullable=True
    )
    # M40.4: READ_ONLY | PROVISIONING | FULL_ADMIN
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="FULL_ADMIN")
    # SHA-256 hex digest of the raw token
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Optional human label ("Azure AD SCIM connector")
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # How many times this token has been used (audit metric)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    enterprise: Mapped[EnterpriseModel] = relationship("EnterpriseModel")
