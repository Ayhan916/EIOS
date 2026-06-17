"""
EIOS Migration 008 — Add assessment_id to recommendations

Links recommendations directly to their parent assessment, completing the
traceability chain: Assessment → Finding / Risk / Recommendation.

Revision: 008
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column(
            "assessment_id",
            sa.String(36),
            sa.ForeignKey("assessments.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_recommendations_assessment_id",
        "recommendations",
        ["assessment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_assessment_id", table_name="recommendations")
    op.drop_column("recommendations", "assessment_id")
