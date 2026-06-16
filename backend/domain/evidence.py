"""
EIOS Domain Model — Evidence

Canonical Enterprise Object per architecture/026.
Represents verifiable information that supports or refutes enterprise knowledge.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base_entity import BaseEntity
from .enums import ConfidenceLevel, EvidenceType


@dataclass(slots=True, kw_only=True)
class Evidence(BaseEntity):
    title: str
    source: str
    description: str
    evidence_type: EvidenceType = field(default=EvidenceType.DOCUMENT)
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.HIGH)
    url: Optional[str] = None
    language: str = "en"
    published_at: Optional[datetime] = None
    retrieved_at: Optional[datetime] = None
    organization_id: Optional[str] = None
    reliability_score: Optional[float] = None
    assessment_ids: list[str] = field(default_factory=list)
    # Document ingestion tracking (M15)
    ingestion_status: str = "none"  # none | ingested | failed | ocr_required
    chunk_count: int = 0
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_mime_type: Optional[str] = None
