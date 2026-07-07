"""Add supplier_scores table (M28 Supplier Intelligence)

Revision ID: 020
Revises: 019
Create Date: 2026-06-18

Changes:
  - Creates supplier_scores table with ESG scores, risk score, trend,
    benchmark percentile, and JSON inputs/drivers columns.
  - ON DELETE CASCADE: deleting a supplier removes its score history.
  - Composite index on (supplier_id, created_at) for efficient latest-score
    lookups without a window function.
  - Index on (organization_id, risk_score) for portfolio watchlist queries.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
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
        sa.Column(
            "supplier_id",
            sa.String(36),
            sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("score_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("esg_score", sa.Float, nullable=False, server_default="100.0"),
        sa.Column("environmental_score", sa.Float, nullable=False, server_default="100.0"),
        sa.Column("social_score", sa.Float, nullable=False, server_default="100.0"),
        sa.Column("governance_score", sa.Float, nullable=False, server_default="100.0"),
        sa.Column("risk_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("risk_band", sa.String(20), nullable=False, server_default="Low"),
        sa.Column("trend", sa.String(20), nullable=False, server_default="Stable"),
        sa.Column("trend_delta", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("sector_percentile", sa.Float, nullable=True),
        sa.Column("inputs", sa.JSON, nullable=False),
        sa.Column("drivers", sa.JSON, nullable=False),
    )

    op.create_index(
        "ix_supplier_scores_supplier_created",
        "supplier_scores",
        ["supplier_id", "created_at"],
    )
    op.create_index(
        "ix_supplier_scores_org_risk",
        "supplier_scores",
        ["organization_id", "risk_score"],
    )
    op.create_index(
        "ix_supplier_scores_org_id",
        "supplier_scores",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_scores_org_id", "supplier_scores")
    op.drop_index("ix_supplier_scores_org_risk", "supplier_scores")
    op.drop_index("ix_supplier_scores_supplier_created", "supplier_scores")
    op.drop_table("supplier_scores")
