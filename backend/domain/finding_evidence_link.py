"""
EIOS Domain Model — FindingEvidenceLink

Rich traceability link connecting a Finding to the specific EvidenceChunk
that supports it. Enables page-level citations for audit trails.

Fields:
  finding_id       — the finding being supported
  evidence_id      — the source evidence document
  evidence_chunk_id— specific chunk within the document (nullable when linking
                     at document level only)
  page_number      — page in the source document where evidence appears
  confidence_score — 0.0-1.0 how strongly this chunk supports the finding
  supporting_excerpt— verbatim text extracted from the chunk
  link_method      — "auto" (engine extraction) or "manual" (human-added)
"""

from __future__ import annotations

from dataclasses import dataclass

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class FindingEvidenceLink(BaseEntity):
    finding_id: str
    evidence_id: str
    evidence_chunk_id: str | None = None
    page_number: int | None = None
    confidence_score: float | None = None
    supporting_excerpt: str | None = None
    link_method: str = "auto"
