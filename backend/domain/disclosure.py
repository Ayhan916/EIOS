from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class DisclosureFramework(BaseEntity):
    """A reporting standard against which sustainability disclosures are made."""

    code: str
    name: str
    fw_version: str = "1.0"
    jurisdiction: str = "Global"
    effective_date: date | None = None
    description: str = ""


@dataclass(slots=True, kw_only=True)
class DisclosureRequirement(BaseEntity):
    """A specific item that must be disclosed under a DisclosureFramework."""

    framework_id: str
    reference: str
    title: str
    description: str = ""
    category: str = ""


@dataclass(slots=True, kw_only=True)
class DisclosureResponse(BaseEntity):
    """An organisation's draft/approved/published response to a DisclosureRequirement."""

    organization_id: str
    requirement_id: str
    disclosure_status: str = "Not Started"
    narrative_text: str = ""
    evidence_coverage: float = 0.0
    coverage_category: str = "Weak"
    coverage_rationale: list[dict[str, Any]] = field(default_factory=list)
    readiness_status: str = "Not Started"
    readiness_rationale: str = ""
    reviewed_by: str | None = None
    approved_by: str | None = None
    published_at: datetime | None = None
