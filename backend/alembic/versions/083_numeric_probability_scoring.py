"""GAP-08: Add numeric 1-10 severity_score and probability_score to findings and risks

Revision ID: 083
Revises: 082
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa

revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("severity_score", sa.SmallInteger(), nullable=True))
    op.add_column("findings", sa.Column("probability_score", sa.SmallInteger(), nullable=True))
    op.add_column("risks", sa.Column("severity_score", sa.SmallInteger(), nullable=True))
    op.add_column("risks", sa.Column("probability_score", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("findings", "probability_score")
    op.drop_column("findings", "severity_score")
    op.drop_column("risks", "probability_score")
    op.drop_column("risks", "severity_score")
