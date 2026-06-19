"""Shared data structures for Copilot retrieval adapters."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalResult:
    """Structured output from a retrieval adapter.

    data: list of plain dicts ready for context assembly (no ORM objects)
    source_ids: IDs of retrieved objects for citation resolution
    provenance: human-readable description of what was retrieved
    retriever: adapter name for audit trail
    freshness_metadata: per-object age data for the Data Freshness Layer (M33.2)
    """

    retriever: str
    provenance: str
    data: list[dict] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    citation_type: str = ""
    freshness_metadata: list[dict] = field(default_factory=list)
