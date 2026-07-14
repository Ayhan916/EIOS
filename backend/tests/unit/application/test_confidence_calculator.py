"""Tests for application/confidence_calculator.py — ADR-015 / E4-F1.

Invariants tested:
  - Determinism: same inputs → same ConfidenceCard
  - Level thresholds: >= 0.75 HIGH, >= 0.45 MEDIUM, < 0.45 LOW
  - data_completeness drives 50% of the score
  - source_count: 0 = 0, 1 = 0.33, 3+ = 1.0 (saturates)
  - recency: ≤30 days = full score, ≥365 days = 0
  - contradiction_penalty reduces final score
  - missing_information appears in ConfidenceCard.limitations
  - ConfidenceInputs validates ranges on construction
  - Returns ConfidenceCard (frozen value object)
  - basis string is non-empty
"""

from __future__ import annotations

import pytest

from application.confidence_calculator import ConfidenceCalculator, ConfidenceInputs
from domain.enums import ConfidenceLevel
from domain.value_objects import ConfidenceCard

pytestmark = pytest.mark.unit


def _calc() -> ConfidenceCalculator:
    return ConfidenceCalculator()


def _inputs(**kwargs) -> ConfidenceInputs:
    return ConfidenceInputs(**kwargs)


# ── determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_inputs_same_output(self) -> None:
        calc = _calc()
        inp = _inputs(source_count=2, data_completeness=0.8, source_recency_days=10)
        assert calc.calculate(inp) == calc.calculate(inp)

    def test_returns_confidence_card(self) -> None:
        result = _calc().calculate(_inputs())
        assert isinstance(result, ConfidenceCard)

    def test_result_is_frozen(self) -> None:
        result = _calc().calculate(_inputs())
        with pytest.raises((AttributeError, TypeError)):
            result.score = 0.99  # type: ignore[misc]


# ── level thresholds ──────────────────────────────────────────────────────────

class TestLevelThresholds:
    def test_high_confidence_with_complete_fresh_data(self) -> None:
        result = _calc().calculate(_inputs(
            source_count=3, data_completeness=1.0, source_recency_days=0
        ))
        assert result.level == ConfidenceLevel.HIGH
        assert result.score >= 0.75

    def test_low_confidence_with_no_data(self) -> None:
        result = _calc().calculate(_inputs())
        assert result.level == ConfidenceLevel.LOW
        assert result.score < 0.45

    def test_medium_confidence_partial_data(self) -> None:
        result = _calc().calculate(_inputs(
            source_count=1, data_completeness=0.6, source_recency_days=60
        ))
        assert result.level in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)


# ── data_completeness (50% weight) ───────────────────────────────────────────

class TestDataCompleteness:
    def test_full_completeness_contributes_0_5(self) -> None:
        result_full = _calc().calculate(_inputs(data_completeness=1.0))
        result_half = _calc().calculate(_inputs(data_completeness=0.5))
        assert result_full.score > result_half.score

    def test_zero_completeness_lowers_score(self) -> None:
        result = _calc().calculate(_inputs(data_completeness=0.0))
        # only recency contributes (20% with 0 days)
        assert result.score <= 0.2


# ── source_count (30% weight via source_score) ───────────────────────────────

class TestSourceCount:
    def test_zero_sources_gives_zero_source_contribution(self) -> None:
        r_zero = _calc().calculate(_inputs(source_count=0, data_completeness=0.8))
        r_one = _calc().calculate(_inputs(source_count=1, data_completeness=0.8))
        assert r_one.score > r_zero.score

    def test_three_sources_saturates(self) -> None:
        r3 = _calc().calculate(_inputs(source_count=3, data_completeness=0.8))
        r9 = _calc().calculate(_inputs(source_count=9, data_completeness=0.8))
        assert r3.score == r9.score


# ── recency (20% weight) ─────────────────────────────────────────────────────

class TestRecency:
    def test_fresh_data_full_recency_score(self) -> None:
        r_fresh = _calc().calculate(_inputs(source_count=1, data_completeness=0.8, source_recency_days=0))
        r_old = _calc().calculate(_inputs(source_count=1, data_completeness=0.8, source_recency_days=200))
        assert r_fresh.score > r_old.score

    def test_very_old_data_zero_recency(self) -> None:
        r_old = _calc().calculate(_inputs(data_completeness=0.8, source_recency_days=365))
        r_fresh = _calc().calculate(_inputs(data_completeness=0.8, source_recency_days=0))
        # 0.2 difference (recency weight)
        assert abs((r_fresh.score - r_old.score) - 0.2) < 0.01


# ── contradiction penalty ─────────────────────────────────────────────────────

class TestContradictionPenalty:
    def test_penalty_reduces_score(self) -> None:
        r_clean = _calc().calculate(_inputs(source_count=2, data_completeness=0.8))
        r_penalty = _calc().calculate(_inputs(source_count=2, data_completeness=0.8,
                                              contradiction_penalty=0.2))
        assert r_penalty.score < r_clean.score
        assert abs(r_clean.score - r_penalty.score - 0.2) < 0.001

    def test_score_never_below_zero(self) -> None:
        result = _calc().calculate(_inputs(contradiction_penalty=0.3))
        assert result.score >= 0.0


# ── missing information ───────────────────────────────────────────────────────

class TestMissingInformation:
    def test_missing_info_appears_in_limitations(self) -> None:
        gaps = ("No recent audit", "Supplier self-report only")
        result = _calc().calculate(_inputs(
            missing_information=gaps
        ))
        assert result.limitations == gaps

    def test_no_missing_info_empty_limitations(self) -> None:
        result = _calc().calculate(_inputs())
        assert result.limitations == ()


# ── input validation ──────────────────────────────────────────────────────────

class TestInputValidation:
    def test_completeness_above_1_raises(self) -> None:
        with pytest.raises(ValueError, match="data_completeness"):
            ConfidenceInputs(data_completeness=1.5)

    def test_completeness_below_0_raises(self) -> None:
        with pytest.raises(ValueError, match="data_completeness"):
            ConfidenceInputs(data_completeness=-0.1)

    def test_cross_validation_above_1_raises(self) -> None:
        with pytest.raises(ValueError, match="cross_validation"):
            ConfidenceInputs(cross_validation_score=1.1)

    def test_contradiction_above_0_3_raises(self) -> None:
        with pytest.raises(ValueError, match="contradiction"):
            ConfidenceInputs(contradiction_penalty=0.31)

    def test_negative_recency_raises(self) -> None:
        with pytest.raises(ValueError, match="source_recency"):
            ConfidenceInputs(source_recency_days=-1)

    def test_basis_is_non_empty(self) -> None:
        result = _calc().calculate(_inputs(source_count=2, data_completeness=0.7))
        assert result.basis
