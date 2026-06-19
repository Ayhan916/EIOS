from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class DueDiligenceReport(BaseEntity):
    """Immutable snapshot of a generated due diligence report.

    report_data stores the full state captured at generation time.
    PDFs are rendered from this snapshot — never from live DB state.
    report_hash (SHA-256) guarantees integrity and reproducibility.
    """

    organization_id: str
    report_type: str  # DueDiligenceReportType value
    framework: str = ""  # e.g. "LkSG", "CSDDD"
    framework_version: str = ""  # e.g. "2023"
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    generated_by: str = ""
    report_data: dict = field(default_factory=dict)
    report_hash: str = ""
