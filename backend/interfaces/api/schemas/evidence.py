from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel, EvidenceType
from .base import EntityResponse


class EvidenceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence_type: EvidenceType = EvidenceType.DOCUMENT
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    url: Optional[str] = None
    language: str = "en"
    published_at: Optional[datetime] = None
    reliability_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EvidenceResponse(EntityResponse):
    title: str
    source: str
    description: str
    evidence_type: str
    confidence: str
    url: Optional[str] = None
    language: str
    published_at: Optional[datetime] = None
    retrieved_at: Optional[datetime] = None
    reliability_score: Optional[float] = None
    organization_id: Optional[str] = None
    # Document ingestion tracking (M15)
    ingestion_status: str = "none"
    chunk_count: int = 0
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_mime_type: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    evidence_id: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    ingestion_status: str
    chunks_created: int
    warnings: list[str] = []
    parser_used: str = ""
