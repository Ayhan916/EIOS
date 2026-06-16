"""
EIOS Domain Model — Assessment

Canonical Enterprise Object per architecture/026.
Represents an ESG due diligence evaluation that produces Findings, Risks and Recommendations.
Governed object: requires approval before entering ACTIVE state (ASTATE-0001).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base_entity import BaseEntity
from .enums import ConfidenceLevel


@dataclass(slots=True, kw_only=True)
class Assessment(BaseEntity):
    title: str
    description: str
    assessment_type: str = ""
    scope: str = ""
    sector_id: Optional[str] = None
    methodology: Optional[str] = None
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.HIGH)
    finding_ids: list[str] = field(default_factory=list)
    risk_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    organization_id: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    quality_score: Optional[float] = None
    # Extraction audit trail (M16)
    extraction_metadata: Optional[dict] = field(default=None)  # type: ignore[assignment]
