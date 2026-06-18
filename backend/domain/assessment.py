"""
EIOS Domain Model — Assessment

Canonical Enterprise Object per architecture/026.
Represents an ESG due diligence evaluation that produces Findings, Risks and Recommendations.
Governed object: requires approval before entering ACTIVE state (ASTATE-0001).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base_entity import BaseEntity
from .enums import ConfidenceLevel, ReviewStatus


@dataclass(slots=True, kw_only=True)
class Assessment(BaseEntity):
    title: str
    description: str
    assessment_type: str = ""
    scope: str = ""
    sector_id: str | None = None
    methodology: str | None = None
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.HIGH)
    finding_ids: list[str] = field(default_factory=list)
    risk_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    organization_id: str | None = None
    approved_by: str | None = None
    approval_date: datetime | None = None
    quality_score: float | None = None
    # Extraction audit trail (M16)
    extraction_metadata: dict[str, Any] | None = field(default=None)
    # Review workflow (M26)
    review_status: ReviewStatus = field(default=ReviewStatus.DRAFT)
    assigned_reviewer_id: str | None = None
    review_due_date: datetime | None = None
    # Supplier ownership (M27)
    supplier_id: str | None = None
