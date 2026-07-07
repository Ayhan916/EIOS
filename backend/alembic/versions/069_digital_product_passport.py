"""Digital Product Passport — M28 / KAN-92

Single table: digital_product_passports
Links to products (product_id).
Includes battery-regulation-specific fields, sustainability KPIs,
and aggregated computed counters refreshed by the service layer.

Revision ID: 069
Revises: 068
Create Date: 2026-06-29
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None

_AUDIT_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
]


def upgrade() -> None:
    op.create_table(
        "digital_product_passports",
        *_AUDIT_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("format", sa.String(30), nullable=False),
        sa.Column("dpp_status", sa.String(20), nullable=False, server_default="DRAFT"),
        # Digital identity
        sa.Column("passport_uid", sa.String(36), nullable=False),
        sa.Column("qr_payload", sa.Text, nullable=True),
        # Product context
        sa.Column("product_category", sa.String(200), nullable=True),
        # Battery-Regulation fields
        sa.Column("battery_chemistry", sa.String(20), nullable=True),
        sa.Column("capacity_wh", sa.Float, nullable=True),
        sa.Column("nominal_voltage_v", sa.Float, nullable=True),
        sa.Column("declared_capacity_cycles", sa.Integer, nullable=True),
        # Sustainability
        sa.Column("carbon_footprint_kg_co2e", sa.Float, nullable=True),
        sa.Column("carbon_footprint_source", sa.String(30), nullable=True),
        sa.Column("recycled_content_pct", sa.Float, nullable=True),
        sa.Column("renewable_content_pct", sa.Float, nullable=True),
        # Computed aggregates
        sa.Column("substances_of_concern_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "non_compliant_regulations_count", sa.Integer, nullable=False, server_default="0"
        ),
        # Manufacturer
        sa.Column("manufacturer_name", sa.String(300), nullable=True),
        sa.Column("manufacturer_country", sa.String(100), nullable=True),
        sa.Column("manufacturing_date", sa.Date, nullable=True),
        # Lifecycle
        sa.Column("valid_from", sa.Date, nullable=True),
        sa.Column("valid_until", sa.Date, nullable=True),
        sa.Column("disclosed_at", sa.DateTime(timezone=True), nullable=True),
        # Evidence
        sa.Column("evidence_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_dpp_org", "digital_product_passports", ["organization_id"])
    op.create_index("ix_dpp_product", "digital_product_passports", ["product_id"])
    op.create_index("ix_dpp_status", "digital_product_passports", ["dpp_status"])
    op.create_index("ix_dpp_format", "digital_product_passports", ["format"])
    op.create_index("ix_dpp_uid", "digital_product_passports", ["passport_uid"], unique=True)
    op.create_index("ix_dpp_disclosed", "digital_product_passports", ["disclosed_at"])


def downgrade() -> None:
    op.drop_table("digital_product_passports")
