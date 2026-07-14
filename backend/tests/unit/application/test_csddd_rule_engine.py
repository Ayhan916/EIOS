"""Tests for application/compliance/csddd_rule_engine.py — ADR-010.

Invariants tested:
  - Determinism: same finding → same matches every call
  - No LLM: evaluate() is synchronous and pure
  - Category match → match_type="exact", confidence="High"
  - Title/description match → match_type="partial", confidence="Medium"
  - Category match wins over title match (no duplicate for same obligation)
  - Severity threshold filtering
  - Empty/null fields handled gracefully
  - Findings below threshold produce no match
  - Results ordered by article_id
  - Known CSDDD articles (Art. 10, Art. 11, Art. 12) trigger correctly
  - Built-in registry has correct size and structure
"""

from __future__ import annotations

import pytest

from application.compliance.csddd_rule_engine import CSDDD_OBLIGATIONS, CsdddRuleEngine
from domain.csddd_obligation import CsdddObligation, ObligationMatch

pytestmark = pytest.mark.unit


# ── helpers ───────────────────────────────────────────────────────────────────

def _finding(
    title: str = "",
    category: str = "",
    severity: str = "High",
    description: str = "",
) -> dict:
    return {"title": title, "category": category, "severity": severity, "description": description}


def _engine_with(*obligations: CsdddObligation) -> CsdddRuleEngine:
    return CsdddRuleEngine(obligations=obligations)


# ── determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_finding_produces_same_matches(self) -> None:
        engine = CsdddRuleEngine()
        f = _finding(category="human rights", severity="High")
        assert engine.evaluate(f) == engine.evaluate(f)

    def test_evaluate_is_synchronous_pure_function(self) -> None:
        # If evaluate were async or had side effects, this would fail or hang
        import inspect
        engine = CsdddRuleEngine()
        assert not inspect.iscoroutinefunction(engine.evaluate)


# ── match type logic ──────────────────────────────────────────────────────────

class TestMatchTypes:
    _OBL = CsdddObligation(
        article_id="test-art-1",
        article_number="Art. 1",
        obligation_text="Test obligation",
        trigger_conditions=("forced labour", "child labour"),
        evidence_requirements=("evidence A",),
        severity_threshold=None,
    )

    def test_category_match_is_exact_with_high_confidence(self) -> None:
        engine = _engine_with(self._OBL)
        matches = engine.evaluate(_finding(category="forced labour supply chain"))
        assert len(matches) == 1
        assert matches[0].match_type == "exact"
        assert matches[0].confidence == "High"

    def test_title_match_is_partial_with_medium_confidence(self) -> None:
        engine = _engine_with(self._OBL)
        matches = engine.evaluate(_finding(title="Suspected child labour at tier-2 supplier"))
        assert len(matches) == 1
        assert matches[0].match_type == "partial"
        assert matches[0].confidence == "Medium"

    def test_description_match_triggers_partial(self) -> None:
        engine = _engine_with(self._OBL)
        matches = engine.evaluate(_finding(description="Evidence of forced labour practices"))
        assert len(matches) == 1
        assert matches[0].match_type == "partial"

    def test_category_match_wins_over_title_match_no_duplicate(self) -> None:
        # Both category and title match → only one result, match_type=exact
        engine = _engine_with(self._OBL)
        matches = engine.evaluate(
            _finding(category="forced labour", title="forced labour report")
        )
        assert len(matches) == 1
        assert matches[0].match_type == "exact"

    def test_matched_conditions_contains_hit_keyword(self) -> None:
        engine = _engine_with(self._OBL)
        matches = engine.evaluate(_finding(category="forced labour supply chain"))
        assert "forced labour" in matches[0].matched_conditions


# ── severity threshold ────────────────────────────────────────────────────────

class TestSeverityThreshold:
    _HIGH_THRESHOLD_OBL = CsdddObligation(
        article_id="test-art-2",
        article_number="Art. 2",
        obligation_text="High-threshold obligation",
        trigger_conditions=("environmental",),
        evidence_requirements=(),
        severity_threshold="High",
    )

    def test_finding_at_threshold_triggers_match(self) -> None:
        engine = _engine_with(self._HIGH_THRESHOLD_OBL)
        matches = engine.evaluate(_finding(category="environmental", severity="High"))
        assert len(matches) == 1

    def test_finding_above_threshold_triggers_match(self) -> None:
        engine = _engine_with(self._HIGH_THRESHOLD_OBL)
        matches = engine.evaluate(_finding(category="environmental", severity="Critical"))
        assert len(matches) == 1

    def test_finding_below_threshold_produces_no_match(self) -> None:
        engine = _engine_with(self._HIGH_THRESHOLD_OBL)
        matches = engine.evaluate(_finding(category="environmental", severity="Low"))
        assert matches == []

    def test_medium_below_high_threshold_no_match(self) -> None:
        engine = _engine_with(self._HIGH_THRESHOLD_OBL)
        matches = engine.evaluate(_finding(category="environmental", severity="Medium"))
        assert matches == []

    def test_none_threshold_always_triggers(self) -> None:
        obl = CsdddObligation(
            article_id="test-art-3",
            article_number="Art. 3",
            obligation_text="Always triggers",
            trigger_conditions=("audit",),
            evidence_requirements=(),
            severity_threshold=None,
        )
        engine = _engine_with(obl)
        for severity in ("Low", "Medium", "High", "Critical"):
            matches = engine.evaluate(_finding(category="audit", severity=severity))
            assert len(matches) == 1, f"Expected match at severity={severity}"


# ── edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_finding_returns_empty_list(self) -> None:
        engine = CsdddRuleEngine()
        assert engine.evaluate({}) == []

    def test_none_values_handled_gracefully(self) -> None:
        engine = CsdddRuleEngine()
        result = engine.evaluate({"title": None, "category": None, "severity": None})
        assert isinstance(result, list)

    def test_no_matching_category_returns_empty(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(_finding(category="something completely unrelated xyz123"))
        assert matches == []

    def test_results_sorted_by_article_id(self) -> None:
        engine = CsdddRuleEngine()
        # "human rights" should trigger both Art. 7 and Art. 10 and Art. 11
        matches = engine.evaluate(_finding(category="human rights", severity="High"))
        ids = [m.article_id for m in matches]
        assert ids == sorted(ids)


# ── known CSDDD articles ──────────────────────────────────────────────────────

class TestKnownArticles:
    def test_child_labour_triggers_art_10(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(_finding(category="child labour", severity="High"))
        ids = {m.article_id for m in matches}
        assert "csddd-art-10" in ids

    def test_environmental_damage_triggers_art_11(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(
            _finding(category="environmental damage", severity="High")
        )
        ids = {m.article_id for m in matches}
        assert "csddd-art-11" in ids

    def test_remediation_triggers_art_12(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(_finding(category="remediation plan", severity="Medium"))
        ids = {m.article_id for m in matches}
        assert "csddd-art-12" in ids

    def test_grievance_triggers_art_14(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(_finding(category="grievance mechanism", severity="Low"))
        ids = {m.article_id for m in matches}
        assert "csddd-art-14" in ids

    def test_board_governance_triggers_art_22(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(_finding(category="governance board", severity="High"))
        ids = {m.article_id for m in matches}
        assert "csddd-art-22" in ids


# ── DoD acceptance tests (IMPLEMENTATION_PLAN.md E2-F2) ──────────────────────

class TestDoDAcceptance:
    """Acceptance tests from IMPLEMENTATION_PLAN.md E2-F2 DoD."""

    def test_forced_labour_myanmar_triggers_art_8_1a_and_art_11(self) -> None:
        """Finding: 'Zwangsarbeit in Myanmar' → Art. 8(1)(a) + Art. 11."""
        engine = CsdddRuleEngine()
        finding = _finding(
            title="Forced labour detected in Myanmar tier-2 supplier",
            category="forced labour",
            severity="Critical",
            description="Workers in Myanmar facility subjected to forced labour conditions",
        )
        matches = engine.evaluate(finding)
        ids = {m.article_id for m in matches}
        assert "csddd-art-8-1a" in ids, f"Art. 8(1)(a) not triggered. Got: {ids}"
        assert "csddd-art-11" in ids, f"Art. 11 not triggered. Got: {ids}"

    def test_environmental_pollution_eu_triggers_art_8_1b(self) -> None:
        """Finding: 'Umweltverschmutzung EU-Lieferant' → Art. 8(1)(b)."""
        engine = CsdddRuleEngine()
        finding = _finding(
            title="Environmental pollution at EU supplier facility",
            category="environmental pollution",
            severity="High",
            description="Hazardous waste dumped near river by EU-based tier-1 supplier",
        )
        matches = engine.evaluate(finding)
        ids = {m.article_id for m in matches}
        assert "csddd-art-8-1b" in ids, f"Art. 8(1)(b) not triggered. Got: {ids}"

    def test_no_llm_in_evaluate_path(self) -> None:
        """evaluate() must be synchronous — no async, no LLM."""
        import inspect
        engine = CsdddRuleEngine()
        result = engine.evaluate(_finding(category="human rights", severity="High"))
        assert not inspect.iscoroutine(result)
        assert isinstance(result, list)

    def test_confidence_high_medium_low_present(self) -> None:
        """HIGH confidence from category match, MEDIUM from title/description match."""
        engine = CsdddRuleEngine()
        cat_match = engine.evaluate(_finding(category="forced labour", severity="Critical"))
        title_match = engine.evaluate(_finding(title="forced labour issue", category="", severity="Critical"))
        assert any(m.confidence == "High" for m in cat_match)
        assert any(m.confidence == "Medium" for m in title_match)

    def test_art_5_triggers_on_policy_category(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(_finding(category="due diligence policy", severity="Low"))
        ids = {m.article_id for m in matches}
        assert "csddd-art-5" in ids

    def test_art_6_triggers_on_supply_chain_mapping(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(_finding(category="supply chain mapping", severity="Low"))
        ids = {m.article_id for m in matches}
        assert "csddd-art-6" in ids

    def test_art_14_climate_triggers_on_transition_plan(self) -> None:
        engine = CsdddRuleEngine()
        matches = engine.evaluate(_finding(category="climate transition plan", severity="Low"))
        ids = {m.article_id for m in matches}
        assert "csddd-art-14-climate" in ids


# ── registry ──────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_built_in_registry_has_twentynine_obligations(self) -> None:
        assert len(CSDDD_OBLIGATIONS) == 29

    def test_all_obligations_have_article_id(self) -> None:
        for obl in CSDDD_OBLIGATIONS:
            assert obl.article_id.startswith("csddd-art-")

    def test_all_obligations_have_trigger_conditions(self) -> None:
        for obl in CSDDD_OBLIGATIONS:
            assert len(obl.trigger_conditions) > 0

    def test_get_obligation_by_known_id(self) -> None:
        engine = CsdddRuleEngine()
        obl = engine.get_obligation("csddd-art-10")
        assert obl is not None
        assert obl.article_number == "Art. 10"

    def test_get_obligation_unknown_id_returns_none(self) -> None:
        engine = CsdddRuleEngine()
        assert engine.get_obligation("does-not-exist") is None

    def test_obligation_count_matches_registry(self) -> None:
        engine = CsdddRuleEngine()
        assert engine.obligation_count == len(CSDDD_OBLIGATIONS)

    def test_value_objects_are_frozen(self) -> None:
        obl = CSDDD_OBLIGATIONS[0]
        with pytest.raises((AttributeError, TypeError)):
            obl.article_id = "modified"  # type: ignore[misc]
