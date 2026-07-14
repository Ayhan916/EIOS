"""review enhancements: excluded_from_index, classification_confidence, copilot_hidden

Revision ID: 118
Revises: 117
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "118"
down_revision = "117"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # rag_documents: per-chunk exclusion from retrieval
    op.add_column("rag_documents", sa.Column("excluded_from_index", sa.Boolean(), nullable=False, server_default="false"))

    # document_files: classification confidence + alternatives
    op.add_column("document_files", sa.Column("classification_confidence", sa.Float(), nullable=True))
    op.add_column("document_files", sa.Column("classification_alternatives", sa.JSON(), nullable=True))

    # document_files: hide whole document from copilot without deleting
    op.add_column("document_files", sa.Column("copilot_hidden", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("rag_documents", "excluded_from_index")
    op.drop_column("document_files", "classification_confidence")
    op.drop_column("document_files", "classification_alternatives")
    op.drop_column("document_files", "copilot_hidden")
