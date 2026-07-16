"""Add classification_evidence column to document_files

Revision ID: 128
Revises: 127
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = "128"
down_revision = "127"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_files",
        sa.Column("classification_evidence", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_files", "classification_evidence")
