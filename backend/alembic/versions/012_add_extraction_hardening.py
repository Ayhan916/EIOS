"""
EIOS Migration 012 — Extraction Hardening (M16)

Adds extraction audit trail to the assessments table.

Changes:
  assessments:
    - extraction_metadata  JSON  NULLABLE  (ExtractionReport stored as JSON dict)
"""

import sqlalchemy as sa

from alembic import op

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
