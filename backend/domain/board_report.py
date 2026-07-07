from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from domain.base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class BoardReport(BaseEntity):
    """Immutable board report snapshot.  Never updated after generation."""

    organization_id: str
    title: str
    report_version: str = "1.0"
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    executive_summary: str = ""
    report_data: dict[str, Any] = field(default_factory=dict)
    supplier_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class ReportSchedule(BaseEntity):
    """Scheduling metadata for automated report generation (M30 delivery)."""

    organization_id: str
    frequency: str = "monthly"
    next_run_at: datetime = field(default_factory=lambda: __import__("datetime").datetime.min)
    last_run_at: datetime | None = None
    report_config: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
