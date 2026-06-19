from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class DueDiligenceReportModel(BaseModel):
    """Immutable snapshot of a generated due diligence report.

    report_data, report_hash, and framework_version are protected by
    a PL/pgSQL immutability trigger (migration 029).
    """

    __tablename__ = "due_diligence_reports"
    __table_args__ = (
        Index("ix_dd_reports_org_type", "organization_id", "report_type"),
        Index("ix_dd_reports_org_framework", "organization_id", "framework"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    framework: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    framework_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    report_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
