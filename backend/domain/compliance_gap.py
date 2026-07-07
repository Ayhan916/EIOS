from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class ComplianceGap(BaseEntity):
    """A persisted compliance gap for an organisation against a specific requirement.

    Gaps are computed by the gap engine and stored so they can be:
    - tracked over time
    - referenced in compliance reports
    - resolved when the underlying issue is addressed
    - reproduced: calculation_version + calculated_at stamp the snapshot
    """

    organization_id: str
    regulation_requirement_id: str
    supplier_id: str | None = None
    # missing_evidence / missing_control / missing_disclosure / unresolved_finding
    gap_type: str = "missing_evidence"
    severity: str = "Medium"  # Low / Medium / High / Critical
    description: str = ""
    evidence_refs: list[Any] = field(default_factory=list)
    source_entity_type: str | None = None  # "finding" / "risk" / None
    source_entity_id: str | None = None
    calculated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    calculation_version: str = "1.0"
    # Framework version captured at calculation time for historical traceability
    regulation_version_at_calculation: str = "1.0"
    is_resolved: bool = False
    resolved_at: datetime | None = None
    resolved_by: str | None = None
