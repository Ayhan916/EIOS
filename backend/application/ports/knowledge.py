from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RetrievedChunkMeta:
    """Rich metadata for a single knowledge chunk returned by semantic search."""

    chunk_id: str
    evidence_id: str
    page_number: int | None
    source_section: str | None
    text: str
    similarity_score: float
    evidence_title: str
    evidence_source: str

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "evidence_id": self.evidence_id,
            "page_number": self.page_number,
            "source_section": self.source_section,
            "text": self.text,
            "similarity_score": self.similarity_score,
            "evidence_title": self.evidence_title,
            "evidence_source": self.evidence_source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RetrievedChunkMeta:
        return cls(
            chunk_id=d["chunk_id"],
            evidence_id=d["evidence_id"],
            page_number=d.get("page_number"),
            source_section=d.get("source_section"),
            text=d.get("text", ""),
            similarity_score=float(d.get("similarity_score", 0.0)),
            evidence_title=d.get("evidence_title", ""),
            evidence_source=d.get("evidence_source", ""),
        )


@runtime_checkable
class KnowledgeSearchPort(Protocol):
    """Abstract port for semantic knowledge retrieval.

    Returns rich chunk metadata (not just text) so callers can build
    traceable evidence links from workflow runs.
    """

    async def search(self, query: str, limit: int = 10) -> list[RetrievedChunkMeta]: ...
