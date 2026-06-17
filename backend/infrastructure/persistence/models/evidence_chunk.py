from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.config import settings

from .base import BaseModel


class EvidenceChunkModel(BaseModel):
    __tablename__ = "evidence_chunks"

    evidence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Vector column: dimension set from config to support model swaps via migration
    embedding = mapped_column(Vector(settings.embedding_dim), nullable=True)
    # Traceability (M15)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_section: Mapped[str | None] = mapped_column(String(500), nullable=True)

    evidence: Mapped[EvidenceModel] = relationship(back_populates="chunks")
