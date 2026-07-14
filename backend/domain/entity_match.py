"""Entity Linker value objects (ADR-013 / E2-F3).

EntityCandidate — one supplier with its canonical name and known aliases,
                  passed to EntityLinker.link() by the caller.
EntityMatch     — the immutable result of a single link() call.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntityCandidate:
    """A supplier known to the system, including alternative name variants.

    Attributes:
        supplier_id:    Stable supplier UUID.
        canonical_name: Primary name (from Supplier.name).
        legal_name:     Optional legal name (from Supplier.legal_name).
        aliases:        Additional known name variants from entity_aliases table.
    """

    supplier_id: str
    canonical_name: str
    legal_name: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntityMatch:
    """Result of EntityLinker.link() for a single query name.

    Attributes:
        supplier_id:   Matched supplier UUID, or None if no match found.
        matched_name:  The name variant that produced the match.
        confidence:    0.0–1.0. Tiers: exact=1.0, alias=0.9, fuzzy≥0.7, no_match=0.0.
        match_method:  "exact" | "alias" | "fuzzy" | "no_match".
    """

    supplier_id: str | None
    matched_name: str
    confidence: float
    match_method: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"EntityMatch.confidence must be 0–1, got {self.confidence}")
        if self.match_method not in ("exact", "alias", "fuzzy", "no_match"):
            raise ValueError(f"Unknown match_method: {self.match_method}")
