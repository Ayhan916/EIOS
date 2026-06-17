"""
EIOS Domain Model — Evidence

Canonical Enterprise Object per architecture/026.
Represents verifiable information that supports or refutes enterprise knowledge.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity
from .enums import ConfidenceLevel, EvidenceType


@dataclass(slots=True, kw_only=True)
class Evidence(BaseEntity):
    title: str
    source: str
    description: str
    evidence_type: EvidenceType = field(default=EvidenceType.DOCUMENT)
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.HIGH)
    url: str | None = None
    language: str = "en"
    published_at: datetime | None = None
    retrieved_at: datetime | None = None
    organization_id: str | None = None
    reliability_score: float | None = None
    assessment_ids: list[str] = field(default_factory=list)
    # Document ingestion tracking (M15)
    ingestion_status: str = "none"  # none | ingested | failed | ocr_required
    chunk_count: int = 0
    file_name: str | None = None
    file_size_bytes: int | None = None
    file_mime_type: str | None = None
