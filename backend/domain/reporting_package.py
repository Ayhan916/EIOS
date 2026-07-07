from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class ReportingPackage(BaseEntity):
    """Immutable snapshot of a published sustainability reporting package."""

    organization_id: str
    framework_id: str
    framework_code: str = ""
    framework_version: str = ""
    package_type: str = ""
    publication_date: datetime = field(default_factory=lambda: datetime.now(UTC))
    published_by: str = ""
    report_data: dict[str, Any] = field(default_factory=dict)
    report_hash: str = ""
