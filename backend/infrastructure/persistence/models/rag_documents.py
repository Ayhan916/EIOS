"""RAG Knowledge Base — persistent document store with vector embeddings."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import Base

_EMBEDDING_DIM = 1024  # intfloat/multilingual-e5-large


class RagDocumentModel(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    supplier_id: Mapped[str | None] = mapped_column(sa.String, nullable=True, index=True)

    # Origin of the document
    doc_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    # "news_article" | "intelligence_event" | "risk_signal" | "regulatory_doc"
    source_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    # ID in the originating table (news_articles.id, intelligence_timeline_events.id, etc.)

    # Content
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # Chunked, normalised text fed into the embedding model

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(_EMBEDDING_DIM), nullable=True
    )

    language: Mapped[str] = mapped_column(sa.String(8), default="de")
    signal_type: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    severity: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    source_name: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("organization_id", "source_id", "doc_type", name="uq_rag_source"),
        sa.Index("ix_rag_org_supplier", "organization_id", "supplier_id"),
        sa.Index("ix_rag_org_doctype", "organization_id", "doc_type"),
    )
