"""
EIOS Migration 007 — Add quality_score to assessments

Adds the quality_score column (Float, nullable) used by the M9
Compliance Intelligence Engine to record the computed assessment quality.

Revision: 007
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("quality_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "quality_score")
