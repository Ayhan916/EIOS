"""099 — RAG Knowledge Base: rag_documents table with pgvector embeddings.

Tables created:
  - rag_documents    (vector knowledge base for semantic search)

Revision ID: 099
Revises: 098
Create Date: 2026-07-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "099"
down_revision = "098"
branch_labels = None
depends_on = None

_EMBEDDING_DIM = 1024  # intfloat/multilingual-e5-large


def upgrade() -> None:
    # pgvector extension must already be enabled (installed via 000 or superuser)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "rag_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            sa.Text(),  # stored as text, cast to vector at query time via pgvector
            nullable=True,
        ),
        sa.Column("language", sa.String(8), nullable=True, server_default="de"),
        sa.Column("signal_type", sa.String(64), nullable=True),
        sa.Column("severity", sa.String(16), nullable=True),
        sa.Column("source_name", sa.String(128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "source_id", "doc_type", name="uq_rag_source"
        ),
    )

    op.create_index("ix_rag_org_id", "rag_documents", ["organization_id"])
    op.create_index("ix_rag_supplier_id", "rag_documents", ["supplier_id"])
    op.create_index("ix_rag_org_supplier", "rag_documents", ["organization_id", "supplier_id"])
    op.create_index("ix_rag_org_doctype", "rag_documents", ["organization_id", "doc_type"])

    # Convert the text column to vector type after table creation
    op.execute(
        f"ALTER TABLE rag_documents "
        f"ALTER COLUMN embedding TYPE vector({_EMBEDDING_DIM}) "
        f"USING embedding::vector({_EMBEDDING_DIM})"
    )

    # HNSW index for fast approximate nearest-neighbour search (cosine distance)
    op.execute(
        "CREATE INDEX ix_rag_embedding_hnsw ON rag_documents "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_table("rag_documents")
