"""M40 — Enterprise Multi-Tenant Scale & Global Operations.

Creates 10 new tables for the enterprise layer:

  enterprises               — top-level enterprise entity
  business_units            — subdivision of an enterprise
  legal_entities            — legal entity within an enterprise
  enterprise_regions        — operational region within an enterprise
  identity_providers        — SSO IdP config (SAML 2.0 / OIDC)
  group_mappings            — IdP group → role mapping
  enterprise_policies       — enterprise governance policies
  retention_rules           — data retention rules
  notification_policies     — notification routing policies
  enterprise_risks          — cross-organizational enterprise risk register

Also adds M40 columns to organizations and users tables for enterprise hierarchy
membership and delegated administration.

Revision ID: 041
Revises: 040
Create Date: 2026-06-20
"""

import sqlalchemy as sa

from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None

_COMMON = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def upgrade() -> None:
    # ── 1. enterprises ───────────────────────────────────────────────────────
    op.create_table(
        "enterprises",
        *_COMMON,
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("hq_country", sa.String(10), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("default_data_residency", sa.String(10), nullable=False, server_default="EU"),
        sa.Column(
            "default_data_classification", sa.String(20), nullable=False, server_default="INTERNAL"
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("settings", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_enterprise_name", "enterprises", ["name"])
    op.create_index("ix_enterprise_active", "enterprises", ["is_active"])

    # ── 2. business_units ────────────────────────────────────────────────────
    op.create_table(
        "business_units",
        *_COMMON,
        sa.Column("enterprise_id", sa.String(36), sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("region_scope", sa.String(100), nullable=True),
        sa.Column("admin_user_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_bu_enterprise", "business_units", ["enterprise_id"])
    op.create_index("ix_bu_active", "business_units", ["is_active"])

    # ── 3. legal_entities ────────────────────────────────────────────────────
    op.create_table(
        "legal_entities",
        *_COMMON,
        sa.Column("enterprise_id", sa.String(36), sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("country", sa.String(10), nullable=True),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column("legal_form", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_le_enterprise", "legal_entities", ["enterprise_id"])
    op.create_index("ix_le_country", "legal_entities", ["country"])

    # ── 4. enterprise_regions ────────────────────────────────────────────────
    op.create_table(
        "enterprise_regions",
        *_COMMON,
        sa.Column("enterprise_id", sa.String(36), sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("data_residency", sa.String(10), nullable=False, server_default="EU"),
        sa.Column("admin_user_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_region_enterprise", "enterprise_regions", ["enterprise_id"])
    op.create_index("ix_region_code", "enterprise_regions", ["code"])

    # ── 5. identity_providers ────────────────────────────────────────────────
    op.create_table(
        "identity_providers",
        *_COMMON,
        sa.Column("enterprise_id", sa.String(36), sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("issuer", sa.String(500), nullable=True),
        sa.Column("metadata_url", sa.String(500), nullable=True),
        sa.Column("client_id", sa.String(500), nullable=True),
        sa.Column("client_secret_encrypted", sa.Text, nullable=True),
        sa.Column(
            "certificates", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column("config", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_idp_enterprise", "identity_providers", ["enterprise_id"])
    op.create_index("ix_idp_type", "identity_providers", ["provider_type"])
    op.create_index("ix_idp_active", "identity_providers", ["is_active"])

    # ── 6. group_mappings ────────────────────────────────────────────────────
    op.create_table(
        "group_mappings",
        *_COMMON,
        sa.Column("idp_id", sa.String(36), sa.ForeignKey("identity_providers.id"), nullable=False),
        sa.Column("enterprise_id", sa.String(36), nullable=False),
        sa.Column("idp_group", sa.String(500), nullable=False),
        sa.Column("mapped_role", sa.String(100), nullable=False),
        sa.Column("scope", sa.String(50), nullable=True),
        sa.Column("business_unit_id", sa.String(36), nullable=True),
        sa.Column("region_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_gm_idp", "group_mappings", ["idp_id"])
    op.create_index("ix_gm_enterprise", "group_mappings", ["enterprise_id"])
    op.create_index("ix_gm_active", "group_mappings", ["is_active"])

    # ── 7. enterprise_policies ───────────────────────────────────────────────
    op.create_table(
        "enterprise_policies",
        *_COMMON,
        sa.Column("enterprise_id", sa.String(36), sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("policy_type", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("config", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("cascade_to_children", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("scope", sa.String(50), nullable=False, server_default="all"),
        sa.Column("scope_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_epolicy_enterprise", "enterprise_policies", ["enterprise_id"])
    op.create_index("ix_epolicy_type", "enterprise_policies", ["policy_type"])
    op.create_index("ix_epolicy_active", "enterprise_policies", ["is_active"])

    # ── 8. retention_rules ───────────────────────────────────────────────────
    op.create_table(
        "retention_rules",
        *_COMMON,
        sa.Column("enterprise_id", sa.String(36), sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False, server_default="365"),
        sa.Column("cascade_to_children", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("legal_hold", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_ret_enterprise", "retention_rules", ["enterprise_id"])
    op.create_index("ix_ret_entity_type", "retention_rules", ["entity_type"])
    op.create_index("ix_ret_legal_hold", "retention_rules", ["legal_hold"])

    # ── 9. notification_policies ─────────────────────────────────────────────
    op.create_table(
        "notification_policies",
        *_COMMON,
        sa.Column("enterprise_id", sa.String(36), sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "escalation_routes", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "regional_routes", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"
        ),
        sa.Column(
            "executive_routes", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_notifpol_enterprise", "notification_policies", ["enterprise_id"])
    op.create_index("ix_notifpol_active", "notification_policies", ["is_active"])

    # ── 10. enterprise_risks ─────────────────────────────────────────────────
    op.create_table(
        "enterprise_risks",
        *_COMMON,
        sa.Column("enterprise_id", sa.String(36), sa.ForeignKey("enterprises.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("risk_status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("esg_category", sa.String(50), nullable=True),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("mitigation_plan", sa.Text, nullable=True),
        sa.Column(
            "linked_region_ids", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_business_unit_ids",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "linked_organization_ids",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "linked_supplier_ids", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
    )
    op.create_index("ix_erisk_enterprise", "enterprise_risks", ["enterprise_id"])
    op.create_index("ix_erisk_severity", "enterprise_risks", ["severity"])
    op.create_index("ix_erisk_status", "enterprise_risks", ["risk_status"])
    op.create_index("ix_erisk_esg_category", "enterprise_risks", ["esg_category"])
    op.create_index("ix_erisk_owner", "enterprise_risks", ["owner_user_id"])

    # ── organizations: add enterprise hierarchy columns ───────────────────────
    op.add_column("organizations", sa.Column("enterprise_id", sa.String(36), nullable=True))
    op.add_column("organizations", sa.Column("business_unit_id", sa.String(36), nullable=True))
    op.add_column("organizations", sa.Column("legal_entity_id", sa.String(36), nullable=True))
    op.add_column("organizations", sa.Column("region_id", sa.String(36), nullable=True))
    op.add_column("organizations", sa.Column("data_residency", sa.String(10), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("data_classification", sa.String(20), nullable=True, server_default="INTERNAL"),
    )
    op.create_index("ix_org_enterprise", "organizations", ["enterprise_id"])
    op.create_index("ix_org_business_unit", "organizations", ["business_unit_id"])
    op.create_index("ix_org_region", "organizations", ["region_id"])

    # ── users: add enterprise scope columns ───────────────────────────────────
    op.add_column("users", sa.Column("enterprise_scope", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("enterprise_id", sa.String(36), nullable=True))
    op.add_column("users", sa.Column("business_unit_id", sa.String(36), nullable=True))
    op.add_column("users", sa.Column("region_id", sa.String(36), nullable=True))
    op.create_index("ix_user_enterprise", "users", ["enterprise_id"])
    op.create_index("ix_user_enterprise_scope", "users", ["enterprise_scope"])


def downgrade() -> None:
    # Remove user columns
    op.drop_index("ix_user_enterprise_scope", "users")
    op.drop_index("ix_user_enterprise", "users")
    op.drop_column("users", "region_id")
    op.drop_column("users", "business_unit_id")
    op.drop_column("users", "enterprise_id")
    op.drop_column("users", "enterprise_scope")

    # Remove organization columns
    op.drop_index("ix_org_region", "organizations")
    op.drop_index("ix_org_business_unit", "organizations")
    op.drop_index("ix_org_enterprise", "organizations")
    op.drop_column("organizations", "data_classification")
    op.drop_column("organizations", "data_residency")
    op.drop_column("organizations", "region_id")
    op.drop_column("organizations", "legal_entity_id")
    op.drop_column("organizations", "business_unit_id")
    op.drop_column("organizations", "enterprise_id")

    # Drop enterprise tables (reverse dependency order)
    for table in [
        "enterprise_risks",
        "notification_policies",
        "retention_rules",
        "enterprise_policies",
        "group_mappings",
        "identity_providers",
        "enterprise_regions",
        "legal_entities",
        "business_units",
        "enterprises",
    ]:
        op.drop_table(table)
