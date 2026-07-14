"""Tests for application/scoring/risk_score_calculator.py — ADR-002.

Invariants tested:
  - Determinism: same inputs → identical RiskScore every call
  - formula_version is always FORMULA_VERSION constant
  - composite_score in [0, 100]
  - Band thresholds match spec (≤25 LOW, ≤50 MODERATE, ≤75 HIGH, >75 CRITICAL)
  - factor_breakdown contains all 9 factors with correct weights
  - factor contributions are correctly normalised (count × weight / 5)
  - ConfidenceCard level reflects data completeness
  - RiskScore is a frozen Value Object (immutable)
  - Zero-input baseline: score=0.0, band=LOW, confidence=LOW
"""

import pytest

from application.scoring.risk_score_calculator import FORMULA_VERSION, calculate
from application.scoring.supplier_scorer import ScoreInputs
from domain.enums import ConfidenceLevel, RiskBand
from domain.value_objects import RiskScore

pytestmark = pytest.mark.unit

# ── helpers ───────────────────────────────────────────────────────────────────


def _inputs(**kwargs: int) -> ScoreInputs:
    return ScoreInputs(**kwargs)


# ── determinism ───────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_inputs_same_output(self) -> None:
        inputs = _inputs(critical_findings=1, high_risks=2, open_actions=3)
        assert calculate(inputs) == calculate(inputs)

    def test_different_inputs_different_output(self) -> None:
        a = calculate(_inputs(critical_findings=1))
        b = calculate(_inputs(critical_findings=2))
        assert a.composite_score != b.composite_score

    def test_formula_version_is_constant(self) -> None:
        result = calculate(_inputs())
        assert result.formula_version == FORMULA_VERSION == "RiskScore-v1.0"


# ── composite score & band ────────────────────────────────────────────────────


class TestCompositeScore:
    def test_zero_inputs_gives_zero_score(self) -> None:
        result = calculate(_inputs())
        assert result.composite_score == 0.0
        assert result.band == RiskBand.LOW

    def test_score_capped_at_100(self) -> None:
        result = calculate(
            _inputs(
                critical_findings=99,
                high_findings=99,
                critical_risks=99,
                overdue_actions=99,
            )
        )
        assert result.composite_score == 100.0

    def test_score_in_valid_range(self) -> None:
        result = calculate(_inputs(critical_findings=2, high_risks=3))
        assert 0.0 <= result.composite_score <= 100.0

    def test_band_low_boundary(self) -> None:
        # raw=125 → score=25.0 → LOW
        result = calculate(_inputs(critical_findings=6, high_findings=1))
        # raw = 6×20 + 1×10 = 130 → score = 26.0 → MODERATE
        # Let's pick raw=125: 6×20=120, low_findings=5 → raw=125 → 25.0
        result = calculate(_inputs(critical_findings=6, low_findings=5))
        assert result.composite_score == 25.0
        assert result.band == RiskBand.LOW

    def test_band_moderate(self) -> None:
        # raw = 3×20 = 60 → score = 12.0 LOW; need score in (25, 50]
        # raw = 200 → score = 40.0 → 2 critical_findings × 20 + 8 high_findings × 10 = 40+80=120 → /5=24 LOW
        # critical_findings=5 → raw=100 → score=20.0 → LOW
        # critical_findings=8 → raw=160 → score=32.0 → MODERATE ✓
        result = calculate(_inputs(critical_findings=8))
        assert result.composite_score == 32.0
        assert result.band == RiskBand.MODERATE

    def test_band_high(self) -> None:
        # score in (50, 75]: raw in (250, 375]
        # critical_findings=15 → raw=300 → score=60.0 → HIGH
        result = calculate(_inputs(critical_findings=15))
        assert result.composite_score == 60.0
        assert result.band == RiskBand.HIGH

    def test_band_critical(self) -> None:
        # score > 75: raw > 375
        # critical_findings=20 → raw=400 → score=80.0 → CRITICAL
        result = calculate(_inputs(critical_findings=20))
        assert result.composite_score == 80.0
        assert result.band == RiskBand.CRITICAL


# ── factor breakdown ──────────────────────────────────────────────────────────


class TestFactorBreakdown:
    _EXPECTED_FACTORS = {
        "critical_findings",
        "high_findings",
        "medium_findings",
        "low_findings",
        "critical_risks",
        "high_risks",
        "medium_risks",
        "overdue_actions",
        "open_actions",
    }

    def test_all_nine_factors_present(self) -> None:
        result = calculate(_inputs(critical_findings=1, open_actions=2))
        names = {f.factor for f in result.factor_breakdown}
        assert names == self._EXPECTED_FACTORS

    def test_factor_count_matches_input(self) -> None:
        inputs = _inputs(critical_findings=3, high_risks=2, overdue_actions=1)
        result = calculate(inputs)
        by_factor = {f.factor: f for f in result.factor_breakdown}
        assert by_factor["critical_findings"].count == 3
        assert by_factor["high_risks"].count == 2
        assert by_factor["overdue_actions"].count == 1

    def test_factor_contribution_formula(self) -> None:
        # critical_findings weight=20 → contribution = 2 × 20 / 5 = 8.0
        inputs = _inputs(critical_findings=2)
        result = calculate(inputs)
        by_factor = {f.factor: f for f in result.factor_breakdown}
        assert by_factor["critical_findings"].contribution == 8.0

    def test_zero_count_factors_still_present(self) -> None:
        result = calculate(_inputs())
        by_factor = {f.factor: f for f in result.factor_breakdown}
        assert by_factor["critical_findings"].count == 0
        assert by_factor["critical_findings"].contribution == 0.0

    def test_breakdown_is_immutable_tuple(self) -> None:
        result = calculate(_inputs(critical_findings=1))
        assert isinstance(result.factor_breakdown, tuple)
        with pytest.raises((AttributeError, TypeError)):
            result.factor_breakdown[0] = result.factor_breakdown[0]  # type: ignore[index]


# ── confidence card ───────────────────────────────────────────────────────────


class TestConfidenceCard:
    def test_no_data_gives_low_confidence(self) -> None:
        result = calculate(_inputs())
        assert result.confidence.level == ConfidenceLevel.LOW
        assert result.confidence.score < 0.5

    def test_one_assessment_one_finding_gives_medium_confidence(self) -> None:
        result = calculate(_inputs(total_assessments=1, critical_findings=1))
        assert result.confidence.level == ConfidenceLevel.MEDIUM
        assert 0.5 <= result.confidence.score < 0.85

    def test_one_assessment_three_findings_gives_high_confidence(self) -> None:
        result = calculate(
            _inputs(
                total_assessments=1,
                critical_findings=1,
                high_findings=1,
                medium_findings=1,
            )
        )
        assert result.confidence.level == ConfidenceLevel.HIGH
        assert result.confidence.score >= 0.85

    def test_findings_without_assessment_gives_low_confidence(self) -> None:
        # findings present but no assessment → still LOW
        result = calculate(_inputs(total_assessments=0, critical_findings=5))
        assert result.confidence.level == ConfidenceLevel.LOW

    def test_confidence_has_basis(self) -> None:
        result = calculate(_inputs())
        assert result.confidence.basis


# ── value object contract ─────────────────────────────────────────────────────


class TestValueObjectContract:
    def test_risk_score_is_frozen(self) -> None:
        result = calculate(_inputs(critical_findings=1))
        with pytest.raises((AttributeError, TypeError)):
            result.composite_score = 0.0  # type: ignore[misc]

    def test_risk_score_equality_by_value(self) -> None:
        inputs = _inputs(critical_findings=2, high_findings=1)
        assert calculate(inputs) == calculate(inputs)

    def test_risk_score_is_instance_of_value_object(self) -> None:
        result = calculate(_inputs())
        assert isinstance(result, RiskScore)
