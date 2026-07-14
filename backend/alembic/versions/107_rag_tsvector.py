"""ADR-008: Add ts_content tsvector column to rag_documents for BM25 hybrid search.

Revision ID: 107
Revises: 106
Create Date: 2026-07-09

NOTE: This migration is NOT executed automatically.
Run manually: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = "107"
down_revision = "106"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rag_documents",
        sa.Column("ts_content", TSVECTOR, nullable=True),
    )
    # GIN index for fast full-text search (required for BM25 performance)
    op.create_index(
        "ix_rag_ts_content",
        "rag_documents",
        ["ts_content"],
        postgresql_using="gin",
    )
    # Backfill: compute tsvector for all existing rows.
    # Uses 'german' config — covers the majority of EIOS documents.
    # Rows with language='en' remain searchable via on-the-fly computation
    # until a language-aware backfill is run separately.
    op.execute(
        """
        UPDATE rag_documents
        SET ts_content = to_tsvector('german', content)
        WHERE ts_content IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_rag_ts_content", table_name="rag_documents")
    op.drop_column("rag_documents", "ts_content")
