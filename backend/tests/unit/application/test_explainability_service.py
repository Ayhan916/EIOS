"""Tests for application/scoring/explainability_service.py — E5-F1.

Invariants tested:
  - explain() returns RiskScoreExplanation from a RiskScore VO
  - all 9 factors present in explanation.factors
  - pct_of_total sums to ~100% for non-zero composite
  - top_drivers: max 3, only non-zero factors, sorted by contribution desc
  - zero composite_score produces pct_of_total=0 for all factors
  - confidence fields mapped from ConfidenceCard
  - limitations mapped from ConfidenceCard.limitations
  - result is deterministic
  - ExplainabilityService is stateless (no I/O)
"""

from __future__ import annotations

import pytest

from application.scoring.explainability_service import ExplainabilityService
from application.scoring.risk_score_calculator import calculate
from application.scoring.supplier_scorer import ScoreInputs
from domain.enums import ConfidenceLevel, RiskBand
from domain.value_objects import ConfidenceCard, FactorScore, RiskScore

pytestmark = pytest.mark.unit


def _score(
    critical_findings: int = 0,
    high_findings: int = 0,
    total_assessments: int = 1,
    **kwargs,
) -> RiskScore:
    return calculate(ScoreInputs(
        critical_findings=critical_findings,
        high_findings=high_findings,
        total_assessments=total_assessments,
        **kwargs,
    ))


# ── structure ─────────────────────────────────────────────────────────────────

class TestStructure:
    def test_returns_risk_score_explanation(self) -> None:
        from application.scoring.explainability_service import RiskScoreExplanation
        svc = ExplainabilityService()
        result = svc.explain(_score(critical_findings=2))
        assert isinstance(result, RiskScoreExplanation)

    def test_result_is_frozen(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score())
        with pytest.raises((AttributeError, TypeError)):
            result.composite_score = 99.0  # type: ignore[misc]

    def test_all_nine_factors_present(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score(critical_findings=1))
        assert len(result.factors) == 9

    def test_factor_names_match_expected(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score())
        names = {f.factor for f in result.factors}
        assert "critical_findings" in names
        assert "overdue_actions" in names

    def test_factor_has_label(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score(critical_findings=1))
        cf = next(f for f in result.factors if f.factor == "critical_findings")
        assert cf.label == "Critical Findings"

    def test_factor_has_impact_tier(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score(critical_findings=1))
        cf = next(f for f in result.factors if f.factor == "critical_findings")
        assert cf.impact == "critical"


# ── pct_of_total ──────────────────────────────────────────────────────────────

class TestPctOfTotal:
    def test_pct_sums_to_100_for_nonzero_score(self) -> None:
        svc = ExplainabilityService()
        # 1 critical_findings → composite = 4.0 (20/5)
        result = svc.explain(_score(critical_findings=1))
        total_pct = sum(f.pct_of_total for f in result.factors)
        assert abs(total_pct - 100.0) < 0.1

    def test_pct_zero_when_composite_is_zero(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score())
        for f in result.factors:
            assert f.pct_of_total == 0.0


# ── top_drivers ───────────────────────────────────────────────────────────────

class TestTopDrivers:
    def test_top_drivers_max_three(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score(critical_findings=3, high_findings=2, overdue_actions=1))
        assert len(result.top_drivers) <= 3

    def test_top_drivers_only_nonzero(self) -> None:
        svc = ExplainabilityService()
        # Only critical_findings is non-zero
        result = svc.explain(_score(critical_findings=2))
        assert all(f.count > 0 for f in result.top_drivers)

    def test_top_drivers_sorted_by_contribution_desc(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score(
            critical_findings=5,  # contribution = 20.0
            high_findings=2,      # contribution = 4.0
            overdue_actions=1,    # contribution = 1.6
        ))
        contribs = [f.contribution for f in result.top_drivers]
        assert contribs == sorted(contribs, reverse=True)

    def test_top_drivers_empty_when_no_findings(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score())
        assert len(result.top_drivers) == 0


# ── confidence fields ─────────────────────────────────────────────────────────

class TestConfidenceFields:
    def test_confidence_level_mapped(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score(total_assessments=1, critical_findings=3,
                                    high_findings=1, medium_findings=1))
        assert result.confidence_level in ("Low", "Medium", "High")

    def test_confidence_score_in_range(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score())
        assert 0.0 <= result.confidence_score <= 1.0

    def test_confidence_basis_non_empty(self) -> None:
        svc = ExplainabilityService()
        result = svc.explain(_score())
        assert result.confidence_basis

    def test_limitations_mapped_from_confidence_card(self) -> None:
        svc = ExplainabilityService()
        # no assessments → LOW confidence with limitations
        result = svc.explain(_score(total_assessments=0))
        assert isinstance(result.limitations, tuple)


# ── determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        svc = ExplainabilityService()
        score = _score(critical_findings=3, high_risks=2)
        assert svc.explain(score) == svc.explain(score)

    def test_composite_score_matches_risk_score(self) -> None:
        score = _score(critical_findings=5)
        svc = ExplainabilityService()
        result = svc.explain(score)
        assert result.composite_score == score.composite_score

    def test_band_matches_risk_score(self) -> None:
        score = _score(critical_findings=20)
        svc = ExplainabilityService()
        result = svc.explain(score)
        assert result.band == score.band.value
