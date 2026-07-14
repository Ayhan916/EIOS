"""ADR-010: CSDDD Obligation Rule Engine — csddd_obligations + finding_legal_mappings tables.

Revision ID: 108
Revises: 107
Create Date: 2026-07-09

NOTE: This migration is NOT executed automatically.
Run manually: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "108"
down_revision = "107"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Static CSDDD obligation registry
    op.create_table(
        "csddd_obligations",
        sa.Column("article_id", sa.String(64), primary_key=True),
        sa.Column("article_number", sa.String(32), nullable=False),
        sa.Column("obligation_text", sa.Text, nullable=False),
        sa.Column("trigger_conditions", JSONB, nullable=False, server_default="[]"),
        sa.Column("evidence_requirements", JSONB, nullable=False, server_default="[]"),
        sa.Column("severity_threshold", sa.String(16), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Persisted rule engine output: one row per finding × obligation match
    op.create_table(
        "finding_legal_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "finding_id",
            sa.String(36),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "article_id",
            sa.String(64),
            sa.ForeignKey("csddd_obligations.article_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("match_type", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("matched_conditions", JSONB, nullable=False, server_default="[]"),
        sa.UniqueConstraint("finding_id", "article_id", name="uq_finding_legal_mapping"),
    )
    op.create_index("ix_finding_legal_article", "finding_legal_mappings", ["article_id"])


def downgrade() -> None:
    op.drop_index("ix_finding_legal_article", table_name="finding_legal_mappings")
    op.drop_table("finding_legal_mappings")
    op.drop_table("csddd_obligations")
