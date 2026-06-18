from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class FindingEvidenceLinkModel(BaseModel):
    __tablename__ = "finding_evidence_links"

    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_chunk_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evidence_chunks.id", ondelete="SET NULL"), nullable=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    supporting_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_method: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")

    finding: Mapped[FindingModel] = relationship(back_populates="evidence_links")
