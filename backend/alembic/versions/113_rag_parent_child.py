"""E1-F3: parent_chunk_id + chunk_level columns for Parent-Child Chunking (ADR-009).

Revision ID: 113
Revises: 112
Create Date: 2026-07-09

Adds two columns to rag_documents:
  chunk_level      VARCHAR(8)  NOT NULL DEFAULT 'flat'
                   Values: 'flat' (existing), 'parent', 'child'
  parent_chunk_id  VARCHAR     NULLABLE FK → rag_documents(id) ON DELETE CASCADE
                   Set only for chunk_level='child'; NULL for 'flat' and 'parent'.

Existing rows keep chunk_level='flat' and parent_chunk_id=NULL (no backfill needed).

NOTE: This migration is NOT executed automatically.
Run manually: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa

revision = "113"
down_revision = "112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rag_documents",
        sa.Column("chunk_level", sa.String(8), nullable=False, server_default="flat"),
    )
    op.add_column(
        "rag_documents",
        sa.Column(
            "parent_chunk_id",
            sa.String,
            sa.ForeignKey("rag_documents.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_rag_parent_chunk_id", "rag_documents", ["parent_chunk_id"]
    )
    op.create_index(
        "ix_rag_chunk_level", "rag_documents", ["chunk_level"]
    )


def downgrade() -> None:
    op.drop_index("ix_rag_chunk_level", table_name="rag_documents")
    op.drop_index("ix_rag_parent_chunk_id", table_name="rag_documents")
    op.drop_column("rag_documents", "parent_chunk_id")
    op.drop_column("rag_documents", "chunk_level")
