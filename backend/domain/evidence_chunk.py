"""
EIOS Domain Model — EvidenceChunk

Represents a chunked segment of an Evidence document with its embedding vector.
EvidenceChunk objects are created by the Knowledge Layer (M5) during ingestion.
They are the unit of retrieval in semantic search.
"""

from dataclasses import dataclass, field
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class EvidenceChunk(BaseEntity):
    evidence_id: str
    chunk_index: int
    text: str
    token_count: int = 0
    embedding: Optional[list[float]] = None
    # Traceability fields (M15): where in the source document this chunk came from
    page_number: Optional[int] = None
    source_section: Optional[str] = None  # worksheet name (XLSX) or heading (DOCX)
