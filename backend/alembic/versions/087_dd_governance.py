"""087 — CSDDD-002 DD-Governance tables (Art. 7).

Revision ID: 087
Revises: 086
Create Date: 2026-07-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "087"
down_revision = "086"
branch_labels = None
depends_on = None

BASE_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, default="Draft"),
    sa.Column("version", sa.Integer, nullable=False, default=1),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
]


def upgrade() -> None:
    op.create_table(
        "dd_policies",
        *BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("policy_status", sa.String(20), nullable=False, default="draft"),
        sa.Column("content_text", sa.Text, nullable=False, default=""),
        sa.Column("file_url", sa.Text, nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=False, default=""),
        sa.Column("approved_role", sa.String(255), nullable=False, default=""),
        sa.Column("valid_from", sa.Date, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_due", sa.Date, nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, default=False),
        sa.Column("public_token", sa.String(64), nullable=True, unique=True),
        sa.Column("policy_version", sa.Integer, nullable=False, default=1),
        sa.Column("parent_policy_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_dd_policies_org", "dd_policies", ["organization_id"])
    op.create_index("ix_dd_policies_org_status", "dd_policies", ["organization_id", "policy_status"])

    op.create_table(
        "codes_of_conduct",
        *BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content_text", sa.Text, nullable=False, default=""),
        sa.Column("file_url", sa.Text, nullable=True),
        sa.Column("coc_version", sa.Integer, nullable=False, default=1),
        sa.Column("valid_from", sa.Date, nullable=True),
        sa.Column("acceptance_validity_months", sa.SmallInteger, nullable=False, default=24),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("linked_policy_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_coc_org", "codes_of_conduct", ["organization_id"])

    op.create_table(
        "coc_acceptances",
        *BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("coc_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("coc_version", sa.Integer, nullable=False, default=1),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by_name", sa.String(500), nullable=False, default=""),
        sa.Column("ip_hash", sa.String(16), nullable=True),
        sa.Column("expires_at", sa.Date, nullable=True),
    )
    op.create_index("ix_coc_acceptances_org", "coc_acceptances", ["organization_id"])
    op.create_index("ix_coc_acceptances_coc", "coc_acceptances", ["coc_id"])
    op.create_index("ix_coc_acceptances_supplier", "coc_acceptances", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_coc_acceptances_supplier", "coc_acceptances")
    op.drop_index("ix_coc_acceptances_coc", "coc_acceptances")
    op.drop_index("ix_coc_acceptances_org", "coc_acceptances")
    op.drop_table("coc_acceptances")
    op.drop_index("ix_coc_org", "codes_of_conduct")
    op.drop_table("codes_of_conduct")
    op.drop_index("ix_dd_policies_org_status", "dd_policies")
    op.drop_index("ix_dd_policies_org", "dd_policies")
    op.drop_table("dd_policies")
