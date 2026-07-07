from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class BoardReportModel(BaseModel):
    __tablename__ = "board_reports"
    __table_args__ = (Index("ix_board_reports_org_created", "organization_id", "created_at"),)

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    supplier_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ReportScheduleModel(BaseModel):
    __tablename__ = "report_schedules"
    __table_args__ = (Index("ix_report_schedules_org_active", "organization_id", "is_active"),)

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
