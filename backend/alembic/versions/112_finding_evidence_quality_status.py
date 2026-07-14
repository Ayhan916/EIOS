"""E3-F1: evidence_quality_status column on findings (ADR-003).

Revision ID: 112
Revises: 111
Create Date: 2026-07-09

Adds evidence_quality_status VARCHAR(20) to findings:
  'Hypothetical' — no evidence reference (default for all existing rows)
  'Evidenced'    — has ≥1 FindingEvidenceLink

Backfill: findings that already have evidence links are set to 'Evidenced'.

NOTE: This migration is NOT executed automatically.
Run manually: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa

revision = "112"
down_revision = "111"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column(
            "evidence_quality_status",
            sa.String(20),
            nullable=False,
            server_default="Hypothetical",
        ),
    )

    # Backfill: findings that already have at least one evidence link → Evidenced
    op.execute(
        """
        UPDATE findings
        SET evidence_quality_status = 'Evidenced'
        WHERE id IN (
            SELECT DISTINCT finding_id
            FROM finding_evidence_links
        )
        """
    )


def downgrade() -> None:
    op.drop_column("findings", "evidence_quality_status")
