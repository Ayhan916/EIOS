"""Product Twin — M27 / KAN-98

Two tables for the Product aggregate:
  products           — core product / SKU identity
  product_bom_items  — bill-of-materials links (product → material)

Revision ID: 068
Revises: 067
Create Date: 2026-06-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None

_AUDIT_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
]


def upgrade() -> None:
    # ── products ──────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        *_AUDIT_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("product_type", sa.String(20), nullable=False),
        sa.Column("product_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("sku", sa.String(200), nullable=True),
        sa.Column("internal_code", sa.String(100), nullable=True),
        sa.Column("gtin", sa.String(20), nullable=True),
        sa.Column("category", sa.String(200), nullable=True),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("unit_of_measure", sa.String(20), nullable=False, server_default="pcs"),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("country_of_manufacture", sa.String(100), nullable=True),
        sa.Column("is_regulated_product", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("target_market", sa.String(20), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_prod_org", "products", ["organization_id"])
    op.create_index("ix_prod_type", "products", ["product_type"])
    op.create_index("ix_prod_status", "products", ["product_status"])
    op.create_index("ix_prod_sku", "products", ["sku"])
    op.create_index("ix_prod_gtin", "products", ["gtin"])
    op.create_index("ix_prod_category", "products", ["category"])

    # ── product_bom_items ─────────────────────────────────────────────────────
    op.create_table(
        "product_bom_items",
        *_AUDIT_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("material_id", sa.String(36), nullable=False),
        sa.Column("weight_pct", sa.Float, nullable=True),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("is_substance_of_concern", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_unique_constraint(
        "uq_prod_bom_product_material", "product_bom_items",
        ["organization_id", "product_id", "material_id"],
    )
    op.create_index("ix_pbom_product", "product_bom_items", ["product_id"])
    op.create_index("ix_pbom_material", "product_bom_items", ["material_id"])
    op.create_index("ix_pbom_org", "product_bom_items", ["organization_id"])
    op.create_index("ix_pbom_concern", "product_bom_items", ["is_substance_of_concern"])


def downgrade() -> None:
    op.drop_table("product_bom_items")
    op.drop_table("products")
