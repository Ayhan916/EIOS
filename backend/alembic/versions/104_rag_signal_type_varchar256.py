"""rag_documents.signal_type VARCHAR(64) -> VARCHAR(256)

Revision ID: 104
Revises: 103
Create Date: 2026-07-08
"""

import sqlalchemy as sa
from alembic import op

revision = "104"
down_revision = "103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("rag_documents", "signal_type", type_=sa.String(256), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("rag_documents", "signal_type", type_=sa.String(64), existing_nullable=True)
