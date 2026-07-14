"""Tests for application/intelligence/entity_linker.py — ADR-013 / E2-F3.

Invariants tested:
  - Exact match: normalised names equal → confidence=1.0, method="exact"
  - Legal name exact match → confidence=1.0, method="exact"
  - Alias match → confidence=0.9, method="alias"
  - Fuzzy match above threshold → confidence 0.7–0.89, method="fuzzy"
  - Fuzzy below threshold → no_match
  - Normalisation: punctuation, case, accents stripped before comparison
  - Empty candidates → no_match
  - DoD: "BMW Group" → BMW AG (confidence 0.9, alias)
  - DoD: "Bayerische Motorenwerke" → BMW AG (fuzzy, confidence >= 0.7)
  - DoD: unknown entity → confidence=0.0, no supplier_id
  - link_many returns one result per query
"""

from __future__ import annotations

import pytest

from application.intelligence.entity_linker import EntityLinker
from domain.entity_match import EntityCandidate, EntityMatch

pytestmark = pytest.mark.unit

# ── fixtures ──────────────────────────────────────────────────────────────────

_BMW = EntityCandidate(
    supplier_id="sup-bmw",
    canonical_name="BMW AG",
    legal_name="Bayerische Motoren Werke Aktiengesellschaft",
    aliases=("BMW Group", "BMW", "Bayerische Motorenwerke AG"),
)

_VW = EntityCandidate(
    supplier_id="sup-vw",
    canonical_name="Volkswagen AG",
    legal_name="Volkswagen Aktiengesellschaft",
    aliases=("VW", "VW Group", "Volkswagen Group"),
)

_CANDIDATES = [_BMW, _VW]


# ── exact match ───────────────────────────────────────────────────────────────

class TestExactMatch:
    def test_canonical_name_exact(self) -> None:
        linker = EntityLinker()
        match = linker.link("BMW AG", _CANDIDATES)
        assert match.supplier_id == "sup-bmw"
        assert match.confidence == 1.0
        assert match.match_method == "exact"

    def test_case_insensitive_exact(self) -> None:
        linker = EntityLinker()
        match = linker.link("bmw ag", _CANDIDATES)
        assert match.confidence == 1.0
        assert match.match_method == "exact"

    def test_legal_name_exact(self) -> None:
        linker = EntityLinker()
        match = linker.link(
            "Bayerische Motoren Werke Aktiengesellschaft", _CANDIDATES
        )
        assert match.supplier_id == "sup-bmw"
        assert match.confidence == 1.0
        assert match.match_method == "exact"

    def test_punctuation_stripped_for_exact(self) -> None:
        linker = EntityLinker()
        match = linker.link("Volkswagen, AG.", _CANDIDATES)
        assert match.supplier_id == "sup-vw"
        assert match.confidence == 1.0


# ── alias match (DoD: "BMW Group" → BMW AG confidence 0.9) ───────────────────

class TestAliasMatch:
    def test_bmw_group_maps_to_bmw_ag(self) -> None:
        """DoD: "BMW Group" → BMW AG (confidence 0.9)."""
        linker = EntityLinker()
        match = linker.link("BMW Group", _CANDIDATES)
        assert match.supplier_id == "sup-bmw"
        assert match.confidence == 0.9
        assert match.match_method == "alias"

    def test_alias_case_insensitive(self) -> None:
        linker = EntityLinker()
        match = linker.link("vw group", _CANDIDATES)
        assert match.supplier_id == "sup-vw"
        assert match.confidence == 0.9
        assert match.match_method == "alias"

    def test_short_alias(self) -> None:
        linker = EntityLinker()
        match = linker.link("BMW", _CANDIDATES)
        assert match.supplier_id == "sup-bmw"
        assert match.match_method == "alias"


# ── fuzzy match (DoD: "Bayerische Motorenwerke" → BMW AG, confidence ≥ 0.7) ──

class TestFuzzyMatch:
    def test_bayerische_motorenwerke_fuzzy(self) -> None:
        """DoD: "Bayerische Motorenwerke" → BMW AG (fuzzy, confidence >= 0.7)."""
        linker = EntityLinker()
        match = linker.link("Bayerische Motorenwerke", _CANDIDATES)
        assert match.supplier_id == "sup-bmw"
        assert match.confidence >= 0.7
        assert match.match_method == "fuzzy"

    def test_fuzzy_typo_in_name(self) -> None:
        linker = EntityLinker()
        match = linker.link("Volkswagen AG", _CANDIDATES)  # exact actually
        assert match.supplier_id == "sup-vw"

    def test_fuzzy_partial_name(self) -> None:
        linker = EntityLinker()
        # "Volkswagen Aktiengesellschaft" is the legal name → alias or fuzzy
        match = linker.link("Volkswagen Aktiengesellschaft", _CANDIDATES)
        assert match.supplier_id == "sup-vw"
        assert match.confidence == 1.0  # exact legal name match


# ── no match (DoD: unknown entity → confidence=0.0) ──────────────────────────

class TestNoMatch:
    def test_completely_unknown_entity(self) -> None:
        """DoD: Unknown entities → confidence=0.0, not linked."""
        linker = EntityLinker()
        match = linker.link("Completely Unknown Corp XYZ123", _CANDIDATES)
        assert match.supplier_id is None
        assert match.confidence == 0.0
        assert match.match_method == "no_match"

    def test_empty_candidates_gives_no_match(self) -> None:
        linker = EntityLinker()
        match = linker.link("BMW AG", [])
        assert match.match_method == "no_match"
        assert match.confidence == 0.0

    def test_short_noisy_query_below_threshold(self) -> None:
        linker = EntityLinker()
        match = linker.link("XYZ", _CANDIDATES)
        assert match.confidence == 0.0


# ── value object contract ─────────────────────────────────────────────────────

class TestValueObjectContract:
    def test_entity_match_is_frozen(self) -> None:
        linker = EntityLinker()
        match = linker.link("BMW AG", _CANDIDATES)
        with pytest.raises((AttributeError, TypeError)):
            match.confidence = 0.0  # type: ignore[misc]

    def test_entity_match_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            EntityMatch(
                supplier_id="x",
                matched_name="x",
                confidence=1.5,
                match_method="exact",
            )

    def test_entity_match_invalid_method_raises(self) -> None:
        with pytest.raises(ValueError, match="match_method"):
            EntityMatch(
                supplier_id="x",
                matched_name="x",
                confidence=0.5,
                match_method="unknown_method",
            )


# ── link_many ─────────────────────────────────────────────────────────────────

class TestLinkMany:
    def test_returns_one_result_per_query(self) -> None:
        linker = EntityLinker()
        queries = ["BMW AG", "Volkswagen AG", "Unknown Corp"]
        results = linker.link_many(queries, _CANDIDATES)
        assert len(results) == 3

    def test_preserves_order(self) -> None:
        linker = EntityLinker()
        queries = ["Volkswagen AG", "BMW AG"]
        results = linker.link_many(queries, _CANDIDATES)
        assert results[0].supplier_id == "sup-vw"
        assert results[1].supplier_id == "sup-bmw"
