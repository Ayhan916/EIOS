from __future__ import annotations

from sqlalchemy import JSON, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class ReportModel(BaseModel):
    __tablename__ = "reports"

    assessment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_by: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="pdf")
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommendation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pdf_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
