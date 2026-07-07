"""External ESG Ratings — M25 / KAN-90

Adds supplier_external_esg_ratings table to store third-party ESG scores
from providers like EcoVadis, MSCI, Sustainalytics, CDP, ISS-ESG, etc.

Revision ID: 066
Revises: 065
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_external_esg_ratings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("rating_date", sa.Date, nullable=False),
        # Numeric scores
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("max_score", sa.Float, nullable=True),
        sa.Column("score_pct", sa.Float, nullable=True),
        # Grade / tier
        sa.Column("grade", sa.String(30), nullable=True),
        # Peer benchmarking
        sa.Column("percentile", sa.Float, nullable=True),
        sa.Column("peer_group", sa.String(300), nullable=True),
        # Sub-scores
        sa.Column("environmental_score", sa.Float, nullable=True),
        sa.Column("social_score", sa.Float, nullable=True),
        sa.Column("governance_score", sa.Float, nullable=True),
        sa.Column("ethics_score", sa.Float, nullable=True),
        sa.Column("sustainable_procurement_score", sa.Float, nullable=True),
        # Validity
        sa.Column("valid_until", sa.Date, nullable=True),
        # Source metadata
        sa.Column("report_url", sa.String(1000), nullable=True),
        sa.Column("methodology_version", sa.String(100), nullable=True),
        sa.Column("evidence_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        # Audit columns
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
        sa.Column("created_by", sa.String(36), nullable=True),
    )

    op.create_unique_constraint(
        "uq_esg_rating_supplier_provider_date",
        "supplier_external_esg_ratings",
        ["supplier_id", "organization_id", "provider", "rating_date"],
    )
    op.create_index("ix_sext_esg_supplier", "supplier_external_esg_ratings", ["supplier_id"])
    op.create_index("ix_sext_esg_org", "supplier_external_esg_ratings", ["organization_id"])
    op.create_index("ix_sext_esg_provider", "supplier_external_esg_ratings", ["provider"])
    op.create_index("ix_sext_esg_date", "supplier_external_esg_ratings", ["rating_date"])
    op.create_index("ix_sext_esg_valid_until", "supplier_external_esg_ratings", ["valid_until"])


def downgrade() -> None:
    op.drop_index("ix_sext_esg_valid_until", table_name="supplier_external_esg_ratings")
    op.drop_index("ix_sext_esg_date", table_name="supplier_external_esg_ratings")
    op.drop_index("ix_sext_esg_provider", table_name="supplier_external_esg_ratings")
    op.drop_index("ix_sext_esg_org", table_name="supplier_external_esg_ratings")
    op.drop_index("ix_sext_esg_supplier", table_name="supplier_external_esg_ratings")
    op.drop_table("supplier_external_esg_ratings")
