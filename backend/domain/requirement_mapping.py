from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class RequirementMapping(BaseEntity):
    """Links a Finding, Risk, or Recommendation to a RegulationRequirement.

    Explainability chain: entity → requirement → rationale → confidence.
    Every mapping records how and why it was created so it remains auditable.
    """

    organization_id: str
    regulation_requirement_id: str
    entity_type: str  # "finding" / "risk" / "recommendation"
    entity_id: str
    confidence: float = 0.8  # 0.0–1.0
    rationale: str = ""
    mapping_method: str = "manual"  # manual / rule_based / ai
    mapping_version: str = "1.0"
    # Framework version captured at mapping time for historical traceability
    regulation_version_at_mapping: str = "1.0"
    mapped_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    supplier_id: str | None = None
    assessment_id: str | None = None
