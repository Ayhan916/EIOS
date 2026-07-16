"""ORM models for Document Intelligence Pipeline."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.models.base import Base


class DocumentSourceModel(Base):
    __tablename__ = "document_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    supplier_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    schedule: Mapped[str] = mapped_column(String(16), nullable=False, default="monthly")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    files: Mapped[list[DocumentFileModel]] = relationship("DocumentFileModel", back_populates="source", cascade="all, delete-orphan")


class DocumentFileModel(Base):
    __tablename__ = "document_files"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("document_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    report_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True, default="de")
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunks_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    extracted_risks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extracted_targets: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extracted_commitments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extracted_kpis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    esg_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_alternatives: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    classification_evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    copilot_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parse_layout: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    source: Mapped[DocumentSourceModel] = relationship("DocumentSourceModel", back_populates="files")
