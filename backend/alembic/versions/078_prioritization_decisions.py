"""078 — Prioritisation Decisions (GAP-18 / CSDDD Art. 10).

Creates the prioritization_decisions table required by CSDDD Art. 10
(documented and reasoned decisions on prioritisation of adverse impacts)
and LkSG §5 (risk analysis and prioritisation).

Revision ID: 078
Revises: 077
Create Date: 2026-07-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prioritization_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("severity_weight", sa.Float, nullable=False, server_default="0"),
        sa.Column("probability_weight", sa.Float, nullable=False, server_default="0"),
        sa.Column("people_affected_weight", sa.Float, nullable=False, server_default="0"),
        sa.Column("priority_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("priority_rank", sa.Integer, nullable=False, server_default="0"),
        sa.Column("resource_capacity_per_quarter", sa.Integer, nullable=False, server_default="4"),
        sa.Column("reasoning", sa.Text, nullable=False, server_default=""),
        sa.Column("overridden_manually", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("override_comment", sa.Text, nullable=True),
        sa.Column("decided_by_user_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "regulation_refs",
            sa.String(100),
            nullable=False,
            server_default="CSDDD Art. 10; LkSG §5",
        ),
    )
    op.create_index("ix_prio_org", "prioritization_decisions", ["organization_id"])
    op.create_index(
        "ix_prio_org_supplier", "prioritization_decisions", ["organization_id", "supplier_id"]
    )
    op.create_index(
        "ix_prio_org_rank", "prioritization_decisions", ["organization_id", "priority_rank"]
    )


def downgrade() -> None:
    op.drop_index("ix_prio_org_rank", table_name="prioritization_decisions")
    op.drop_index("ix_prio_org_supplier", table_name="prioritization_decisions")
    op.drop_index("ix_prio_org", table_name="prioritization_decisions")
    op.drop_table("prioritization_decisions")
