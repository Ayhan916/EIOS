"""Entity Linker — maps company name variants to Supplier records (ADR-013 / E2-F3).

No LLM is used (ADR-001). Matching is purely deterministic:

  Tier 1 — Exact  (confidence 1.0):
    Normalised query == normalised canonical_name or legal_name.

  Tier 2 — Alias  (confidence 0.9):
    Normalised query matches any alias in EntityCandidate.aliases.

  Tier 3 — Fuzzy  (confidence 0.7–0.89):
    difflib.SequenceMatcher ratio >= FUZZY_THRESHOLD (0.75) on normalised names.
    Confidence = round(ratio * 0.9, 2) — scales 0.675–0.81 within the fuzzy tier.

  No match (confidence 0.0):
    No tier matched.

Callers are responsible for loading the candidate list from the database
(Supplier name + legal_name + entity_aliases rows). The engine is stateless
and operates purely on the supplied list — makes it trivially testable.

Usage:
    linker = EntityLinker()
    candidates = [
        EntityCandidate("sup-1", "BMW AG", legal_name="Bayerische Motoren Werke AG",
                        aliases=("BMW Group", "BMW")),
    ]
    match = linker.link("BMW Group", candidates)
    # EntityMatch(supplier_id="sup-1", matched_name="BMW Group",
    #             confidence=0.9, match_method="alias")
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from domain.entity_match import EntityCandidate, EntityMatch

# Minimum SequenceMatcher ratio to qualify as a fuzzy match
FUZZY_THRESHOLD: float = 0.75

_STRIP_RE = re.compile(r"[.,()&\-/]")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace, remove accents."""
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = _STRIP_RE.sub(" ", name)
    name = _WHITESPACE_RE.sub(" ", name).strip()
    return name


class EntityLinker:
    """Deterministic, stateless entity linker (ADR-013).

    Instantiate once and reuse — no mutable state.
    """

    def link(
        self,
        query_name: str,
        candidates: list[EntityCandidate],
    ) -> EntityMatch:
        """Map a company name to the best matching supplier candidate.

        Args:
            query_name:  Company name as it appears in a news signal or document.
            candidates:  All supplier candidates to search against. Load from DB
                         before calling (Supplier.name + legal_name + aliases).

        Returns:
            EntityMatch with the best match found, or match_method="no_match"
            if nothing meets the fuzzy threshold.
        """
        norm_query = _normalize(query_name)

        # ── Tier 1: exact match ───────────────────────────────────────────────
        for candidate in candidates:
            if norm_query == _normalize(candidate.canonical_name):
                return EntityMatch(
                    supplier_id=candidate.supplier_id,
                    matched_name=candidate.canonical_name,
                    confidence=1.0,
                    match_method="exact",
                )
            if candidate.legal_name and norm_query == _normalize(candidate.legal_name):
                return EntityMatch(
                    supplier_id=candidate.supplier_id,
                    matched_name=candidate.legal_name,
                    confidence=1.0,
                    match_method="exact",
                )

        # ── Tier 2: alias match ───────────────────────────────────────────────
        for candidate in candidates:
            for alias in candidate.aliases:
                if norm_query == _normalize(alias):
                    return EntityMatch(
                        supplier_id=candidate.supplier_id,
                        matched_name=alias,
                        confidence=0.9,
                        match_method="alias",
                    )

        # ── Tier 3: fuzzy match ───────────────────────────────────────────────
        best_ratio: float = 0.0
        best_match: EntityMatch | None = None

        for candidate in candidates:
            names_to_check = [candidate.canonical_name]
            if candidate.legal_name:
                names_to_check.append(candidate.legal_name)
            names_to_check.extend(candidate.aliases)

            for name in names_to_check:
                ratio = SequenceMatcher(None, norm_query, _normalize(name)).ratio()
                if ratio >= FUZZY_THRESHOLD and ratio > best_ratio:
                    best_ratio = ratio
                    best_match = EntityMatch(
                        supplier_id=candidate.supplier_id,
                        matched_name=name,
                        confidence=round(ratio * 0.9, 2),
                        match_method="fuzzy",
                    )

        if best_match is not None:
            return best_match

        # ── No match ─────────────────────────────────────────────────────────
        return EntityMatch(
            supplier_id=None,
            matched_name=query_name,
            confidence=0.0,
            match_method="no_match",
        )

    def link_many(
        self,
        query_names: list[str],
        candidates: list[EntityCandidate],
    ) -> list[EntityMatch]:
        """Convenience: link multiple names against the same candidate list."""
        return [self.link(name, candidates) for name in query_names]
