"""add page_number to rag_documents

Revision ID: 117
Revises: 116
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "117"
down_revision = "116"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rag_documents",
        sa.Column("page_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rag_documents", "page_number")
