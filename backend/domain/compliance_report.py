from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class ComplianceReport(BaseEntity):
    """Immutable snapshot of a compliance report.

    The report_data field captures the full framework + gap state at generation
    time. PDFs are always rendered from this snapshot, never from live DB state,
    guaranteeing reproducibility regardless of subsequent data changes.
    """

    organization_id: str
    report_type: str  # csrd_gap | esrs_readiness | csddd_due_diligence
    framework_code: str = ""
    framework_version: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    generated_by: str = ""
    report_data: dict[str, Any] = field(default_factory=dict)
    report_hash: str = ""
