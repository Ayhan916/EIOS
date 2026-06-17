"""Add pgvector extension and evidence_chunks table

Revision ID: 003
Revises: 002
Create Date: 2026-06-16

Enables the pgvector PostgreSQL extension and creates the evidence_chunks table
for semantic similarity search. Embedding dimension matches the configured
embedding model (default: 384 for BAAI/bge-small-en-v1.5).

Production note: if the embedding model is changed to a different dimension,
a new migration must be written to drop and recreate the embedding column.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 384  # BAAI/bge-small-en-v1.5; change if model changes


def upgrade() -> None:
    # Enable pgvector extension (requires PostgreSQL superuser or the extension pre-installed)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "evidence_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "evidence_id",
            sa.String(36),
            sa.ForeignKey("evidences.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("embedding", sa.Text, nullable=True),  # overridden below
    )

    # Replace the placeholder column with the actual vector column
    op.drop_column("evidence_chunks", "embedding")
    op.execute(f"ALTER TABLE evidence_chunks ADD COLUMN embedding vector({EMBEDDING_DIM})")

    # HNSW index for fast approximate nearest-neighbor search (cosine distance)
    op.execute(
        "CREATE INDEX evidence_chunks_embedding_hnsw "
        "ON evidence_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("evidence_chunks")
    op.execute("DROP EXTENSION IF EXISTS vector")
