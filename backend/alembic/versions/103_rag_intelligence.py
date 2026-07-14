"""103 — RAG Intelligence: company_name, report_year, document_file_id, doc_class, signal_dimension, signal_direction

Revision ID: 103
Revises: 102
Create Date: 2026-07-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "103"
down_revision = "102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rag_documents", sa.Column("company_name", sa.String(256), nullable=True))
    op.add_column("rag_documents", sa.Column("report_year", sa.Integer(), nullable=True))
    op.add_column("rag_documents", sa.Column("document_file_id", sa.String(), nullable=True))
    op.add_column("rag_documents", sa.Column("doc_class", sa.String(32), nullable=True))
    op.add_column("rag_documents", sa.Column("signal_dimension", sa.String(32), nullable=True))
    op.add_column("rag_documents", sa.Column("signal_direction", sa.String(16), nullable=True))

    op.create_index("ix_rag_company_year", "rag_documents", ["company_name", "report_year"])
    op.create_index("ix_rag_doc_class", "rag_documents", ["organization_id", "doc_class"])
    op.create_index("ix_rag_doc_file", "rag_documents", ["document_file_id"])


def downgrade() -> None:
    op.drop_index("ix_rag_doc_file", "rag_documents")
    op.drop_index("ix_rag_doc_class", "rag_documents")
    op.drop_index("ix_rag_company_year", "rag_documents")
    op.drop_column("rag_documents", "signal_direction")
    op.drop_column("rag_documents", "signal_dimension")
    op.drop_column("rag_documents", "doc_class")
    op.drop_column("rag_documents", "document_file_id")
    op.drop_column("rag_documents", "report_year")
    op.drop_column("rag_documents", "company_name")
