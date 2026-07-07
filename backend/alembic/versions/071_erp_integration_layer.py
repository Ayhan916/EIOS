"""ERP Integration Layer — M6

Three new tables:
  erp_connectors      — connector registry (SAP / Oracle / REST / CSV)
  erp_sync_jobs       — per-run audit log (inbound/outbound)
  erp_field_mappings  — per-connector field translation rules

Revision ID: 071
Revises: 070
Create Date: 2026-06-29
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ERP external_ref to existing Material and Product tables
    op.add_column("materials", sa.Column("external_ref", sa.String(200), nullable=True))
    op.create_index("ix_materials_external_ref", "materials", ["external_ref"])
    op.add_column("products", sa.Column("external_ref", sa.String(200), nullable=True))
    op.create_index("ix_products_external_ref", "products", ["external_ref"])

    op.create_table(
        "erp_connectors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("adapter_type", sa.String(30), nullable=False),
        sa.Column("base_url", sa.Text, nullable=True),
        sa.Column("secret_reference_id", sa.String(36), nullable=True),
        sa.Column("auth_scheme", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("connector_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(20), nullable=True),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="30"),
        sa.Column("config_json", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("organization_id", "name", name="uq_erp_connectors_org_name"),
    )
    op.create_index("ix_erp_connectors_org", "erp_connectors", ["organization_id"])
    op.create_index("ix_erp_connectors_status", "erp_connectors", ["connector_status"])

    op.create_table(
        "erp_sync_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("connector_id", sa.String(36), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("job_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("trigger_source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("records_fetched", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_details_json", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("runtime_seconds", sa.String(20), nullable=True),
        sa.Column("initiated_by", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_erp_sync_jobs_connector", "erp_sync_jobs", ["connector_id"])
    op.create_index("ix_erp_sync_jobs_status", "erp_sync_jobs", ["job_status"])
    op.create_index("ix_erp_sync_jobs_started", "erp_sync_jobs", ["started_at"])
    op.create_index("ix_erp_sync_jobs_org", "erp_sync_jobs", ["organization_id"])

    op.create_table(
        "erp_field_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("connector_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("erp_field", sa.String(300), nullable=False),
        sa.Column("eios_field", sa.String(300), nullable=False),
        sa.Column("transform_fn", sa.String(50), nullable=True),
        sa.Column("is_required", sa.String(5), nullable=False, server_default="False"),
        sa.Column("default_value", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "connector_id",
            "entity_type",
            "erp_field",
            name="uq_erp_field_mapping_connector_entity_field",
        ),
    )
    op.create_index("ix_erp_field_mappings_connector", "erp_field_mappings", ["connector_id"])
    op.create_index("ix_erp_field_mappings_org", "erp_field_mappings", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_products_external_ref", table_name="products")
    op.drop_column("products", "external_ref")
    op.drop_index("ix_materials_external_ref", table_name="materials")
    op.drop_column("materials", "external_ref")

    op.drop_index("ix_erp_field_mappings_org", table_name="erp_field_mappings")
    op.drop_index("ix_erp_field_mappings_connector", table_name="erp_field_mappings")
    op.drop_table("erp_field_mappings")

    op.drop_index("ix_erp_sync_jobs_org", table_name="erp_sync_jobs")
    op.drop_index("ix_erp_sync_jobs_started", table_name="erp_sync_jobs")
    op.drop_index("ix_erp_sync_jobs_status", table_name="erp_sync_jobs")
    op.drop_index("ix_erp_sync_jobs_connector", table_name="erp_sync_jobs")
    op.drop_table("erp_sync_jobs")

    op.drop_index("ix_erp_connectors_status", table_name="erp_connectors")
    op.drop_index("ix_erp_connectors_org", table_name="erp_connectors")
    op.drop_table("erp_connectors")
