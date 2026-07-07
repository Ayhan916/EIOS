"""add finding_evidence_links table and evidence strength columns

Revision ID: 016
Revises: 015
Create Date: 2026-06-18
"""

import sqlalchemy as sa

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rich evidence link table — replaces the bare finding_evidence junction
    op.create_table(
        "finding_evidence_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finding_id",
            sa.String(36),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            sa.String(36),
            sa.ForeignKey("evidences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_chunk_id",
            sa.String(36),
            sa.ForeignKey("evidence_chunks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("supporting_excerpt", sa.Text, nullable=True),
        sa.Column("link_method", sa.String(20), nullable=False, server_default="auto"),
    )
    op.create_index("ix_fel_finding_id", "finding_evidence_links", ["finding_id"])
    op.create_index("ix_fel_evidence_id", "finding_evidence_links", ["evidence_id"])
    op.create_index(
        "ix_fel_finding_confidence",
        "finding_evidence_links",
        ["finding_id", "confidence_score"],
    )

    # Evidence intelligence columns on findings
    op.add_column(
        "findings",
        sa.Column("evidence_strength", sa.String(20), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("evidence_source_count", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("findings", "evidence_source_count")
    op.drop_column("findings", "evidence_strength")
    op.drop_index("ix_fel_finding_confidence", table_name="finding_evidence_links")
    op.drop_index("ix_fel_evidence_id", table_name="finding_evidence_links")
    op.drop_index("ix_fel_finding_id", table_name="finding_evidence_links")
    op.drop_table("finding_evidence_links")
