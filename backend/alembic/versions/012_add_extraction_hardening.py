"""
EIOS Migration 012 — Extraction Hardening (M16)

Adds extraction audit trail to the assessments table.

Changes:
  assessments:
    - extraction_metadata  JSON  NULLABLE  (ExtractionReport stored as JSON dict)
"""

from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("extraction_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "extraction_metadata")
