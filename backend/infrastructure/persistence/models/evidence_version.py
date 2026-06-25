"""M46.2 — Evidence document version history (G-045)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EvidenceVersionModel(Base):
    __tablename__ = "evidence_versions"
    __table_args__ = (
        UniqueConstraint("evidence_id", "version_number", name="uq_evidence_version"),
        Index("ix_evidence_versions_evidence", "evidence_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidences.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_mime_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ingestion_status: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
