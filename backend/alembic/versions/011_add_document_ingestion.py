"""
EIOS Migration 011 — Document Ingestion (M15)

Adds document file metadata and ingestion tracking to the evidences table,
and source-location traceability fields to evidence_chunks.

Changes:
  evidences:
    - ingestion_status  VARCHAR(20)  NOT NULL DEFAULT 'none'
    - chunk_count       INTEGER      NOT NULL DEFAULT 0
    - file_name         VARCHAR(500) NULLABLE
    - file_size_bytes   INTEGER      NULLABLE
    - file_mime_type    VARCHAR(200) NULLABLE

  evidence_chunks:
    - page_number       INTEGER      NULLABLE  (1-indexed page in source PDF/sheet)
    - source_section    VARCHAR(500) NULLABLE  (worksheet name / DOCX heading)
"""

import sqlalchemy as sa

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # evidences — document ingestion tracking
    op.add_column(
        "evidences",
        sa.Column("ingestion_status", sa.String(20), nullable=False, server_default="none"),
    )
    op.add_column(
        "evidences", sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("evidences", sa.Column("file_name", sa.String(500), nullable=True))
    op.add_column("evidences", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    op.add_column("evidences", sa.Column("file_mime_type", sa.String(200), nullable=True))

    # evidence_chunks — traceability
    op.add_column("evidence_chunks", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("evidence_chunks", sa.Column("source_section", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence_chunks", "source_section")
    op.drop_column("evidence_chunks", "page_number")

    op.drop_column("evidences", "file_mime_type")
    op.drop_column("evidences", "file_size_bytes")
    op.drop_column("evidences", "file_name")
    op.drop_column("evidences", "chunk_count")
    op.drop_column("evidences", "ingestion_status")
