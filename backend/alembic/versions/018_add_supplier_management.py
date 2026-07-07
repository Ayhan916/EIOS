"""add supplier management (M27)

Revision ID: 018
Revises: 017
Create Date: 2026-06-18

Adds:
  - suppliers table (primary business entity for ESG due diligence)
  - assessments.supplier_id FK (nullable — soft migration for existing records)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── suppliers ─────────────────────────────────────────────────────────────
    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("legal_name", sa.String(500), nullable=True),
        sa.Column("country", sa.String(100), nullable=False, server_default=""),
        sa.Column("industry", sa.String(200), nullable=False, server_default=""),
        sa.Column("nace_code", sa.String(20), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("supplier_tier", sa.String(20), nullable=False, server_default="Tier 1"),
        sa.Column("supplier_status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_suppliers_org_name", "suppliers", ["organization_id", "name"])

    # ── assessments.supplier_id (nullable FK — existing rows remain NULL) ─────
    op.add_column(
        "assessments",
        sa.Column(
            "supplier_id",
            sa.String(36),
            sa.ForeignKey("suppliers.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("assessments", "supplier_id")
    op.drop_index("ix_suppliers_org_name", table_name="suppliers")
    op.drop_table("suppliers")
