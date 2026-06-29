from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import assessment_evidence, finding_evidence
from .base import BaseModel


class EvidenceModel(BaseModel):
    __tablename__ = "evidences"

    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, default="Document")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="High")
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Document ingestion tracking (M15)
    ingestion_status: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_mime_type: Mapped[str | None] = mapped_column(String(200), nullable=True)

    assessments: Mapped[list[AssessmentModel]] = relationship(
        secondary=assessment_evidence, back_populates="evidence"
    )
    findings: Mapped[list[FindingModel]] = relationship(
        secondary=finding_evidence, back_populates="evidence"
    )
    chunks: Mapped[list[EvidenceChunkModel]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )
