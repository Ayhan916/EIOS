"""RAG Knowledge Base — persistent document store with vector embeddings."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import Base

_EMBEDDING_DIM = 1024  # intfloat/multilingual-e5-large


class RagDocumentModel(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    supplier_id: Mapped[str | None] = mapped_column(sa.String, nullable=True, index=True)

    # Document origin
    doc_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    doc_class: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    # "financial" | "esg" | "regulatory" | "statement" | "signal"

    source_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    document_file_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    # Company + time context
    company_name: Mapped[str | None] = mapped_column(sa.String(256), nullable=True)
    report_year: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    # Content
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(_EMBEDDING_DIM), nullable=True)
    # ADR-008: pre-computed tsvector for BM25 hybrid search — populated by migration 107
    ts_content = mapped_column(TSVECTOR, nullable=True)

    # PDF source page (1-based) — populated by Docling page-aware chunking
    page_number: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    # ADR-009: Parent-Child hierarchy — "flat" | "parent" | "child"
    chunk_level: Mapped[str] = mapped_column(sa.String(8), nullable=False, server_default="flat")
    # FK to the parent RagDocumentModel.id — NULL for flat/parent chunks
    parent_chunk_id: Mapped[str | None] = mapped_column(
        sa.String,
        sa.ForeignKey("rag_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    language: Mapped[str] = mapped_column(sa.String(8), default="de")

    # Signal metadata
    signal_type: Mapped[str | None] = mapped_column(sa.String(256), nullable=True)
    signal_dimension: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    # "financial" | "esg" | "governance" | "supply_chain" | "regulatory" | "reputation"
    signal_direction: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    # "positive" | "negative" | "neutral"
    severity: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)

    source_name: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("organization_id", "source_id", "doc_type", name="uq_rag_source"),
        sa.Index("ix_rag_org_supplier", "organization_id", "supplier_id"),
        sa.Index("ix_rag_org_doctype", "organization_id", "doc_type"),
        sa.Index("ix_rag_company_year", "company_name", "report_year"),
        sa.Index("ix_rag_doc_class", "organization_id", "doc_class"),
        sa.Index("ix_rag_doc_file", "document_file_id"),
        # ADR-008: GIN index for BM25 full-text search
        sa.Index("ix_rag_ts_content", "ts_content", postgresql_using="gin"),
    )
