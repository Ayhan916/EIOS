"""Unit tests for M32 Evidence Coverage Engine."""

from __future__ import annotations

import pytest

from application.disclosure.coverage_engine import (
    CoverageResult,
    compute_coverage,
    _categorise,
    _QUANTITY_SATURATION,
    _QUANTITY_WEIGHT,
    _QUALITY_WEIGHT,
    _DIVERSITY_WEIGHT,
    _CONFIDENCE_WEIGHT,
)


def _ev(reliability: float = 0.8, ev_type: str = "Document") -> dict:
    return {"reliability_score": reliability, "evidence_type": ev_type}


class TestCoverageWeights:
    def test_weights_sum_to_one(self):
        total = _QUANTITY_WEIGHT + _QUALITY_WEIGHT + _DIVERSITY_WEIGHT + _CONFIDENCE_WEIGHT
        assert abs(total - 1.0) < 1e-9

    def test_empty_input_gives_zero_score(self):
        result = compute_coverage(evidence_items=[], mapping_confidences=[])
        assert result.score == 0.0
        assert result.category == "Weak"

    def test_returns_coverage_result(self):
        result = compute_coverage(evidence_items=[_ev()], mapping_confidences=[0.8])
        assert isinstance(result, CoverageResult)
        assert 0.0 <= result.score <= 1.0


class TestQuantityFactor:
    def test_single_item_partial_score(self):
        result = compute_coverage(
            evidence_items=[_ev()],
            mapping_confidences=[],
        )
        qty_factor = next(f for f in result.factors if f["factor"] == "quantity")
        assert qty_factor["score"] == pytest.approx(1 / _QUANTITY_SATURATION)

    def test_saturation_at_five_items(self):
        items = [_ev() for _ in range(_QUANTITY_SATURATION)]
        result = compute_coverage(evidence_items=items, mapping_confidences=[])
        qty_factor = next(f for f in result.factors if f["factor"] == "quantity")
        assert qty_factor["score"] == 1.0

    def test_more_than_saturation_capped(self):
        items = [_ev() for _ in range(10)]
        result = compute_coverage(evidence_items=items, mapping_confidences=[])
        qty_factor = next(f for f in result.factors if f["factor"] == "quantity")
        assert qty_factor["score"] == 1.0


class TestQualityFactor:
    def test_perfect_quality_score(self):
        items = [_ev(reliability=1.0), _ev(reliability=1.0)]
        result = compute_coverage(evidence_items=items, mapping_confidences=[])
        qual_factor = next(f for f in result.factors if f["factor"] == "quality")
        assert qual_factor["score"] == pytest.approx(1.0)

    def test_average_quality(self):
        items = [_ev(reliability=0.6), _ev(reliability=0.4)]
        result = compute_coverage(evidence_items=items, mapping_confidences=[])
        qual_factor = next(f for f in result.factors if f["factor"] == "quality")
        assert qual_factor["score"] == pytest.approx(0.5)

    def test_missing_reliability_score_defaults_to_0_5(self):
        items = [{"evidence_type": "Document"}]  # no reliability_score
        result = compute_coverage(evidence_items=items, mapping_confidences=[])
        qual_factor = next(f for f in result.factors if f["factor"] == "quality")
        assert qual_factor["score"] == pytest.approx(0.5)

    def test_zero_quality_if_no_evidence(self):
        result = compute_coverage(evidence_items=[], mapping_confidences=[])
        qual_factor = next(f for f in result.factors if f["factor"] == "quality")
        assert qual_factor["score"] == 0.0


class TestDiversityFactor:
    def test_single_evidence_type(self):
        result = compute_coverage(evidence_items=[_ev(ev_type="Document")], mapping_confidences=[])
        div_factor = next(f for f in result.factors if f["factor"] == "diversity")
        assert div_factor["raw"] == 1

    def test_all_evidence_types_gives_full_diversity(self):
        all_types = ["Document", "Report", "Publication", "Website", "Data", "Testimony"]
        items = [_ev(ev_type=t) for t in all_types]
        result = compute_coverage(evidence_items=items, mapping_confidences=[])
        div_factor = next(f for f in result.factors if f["factor"] == "diversity")
        assert div_factor["score"] == pytest.approx(1.0)

    def test_unknown_type_not_counted(self):
        items = [_ev(ev_type="Unknown")]
        result = compute_coverage(evidence_items=items, mapping_confidences=[])
        div_factor = next(f for f in result.factors if f["factor"] == "diversity")
        assert div_factor["raw"] == 0

    def test_duplicate_types_counted_once(self):
        items = [_ev(ev_type="Document"), _ev(ev_type="Document")]
        result = compute_coverage(evidence_items=items, mapping_confidences=[])
        div_factor = next(f for f in result.factors if f["factor"] == "diversity")
        assert div_factor["raw"] == 1


class TestConfidenceFactor:
    def test_single_high_confidence(self):
        result = compute_coverage(evidence_items=[], mapping_confidences=[0.9])
        conf_factor = next(f for f in result.factors if f["factor"] == "confidence")
        assert conf_factor["score"] == pytest.approx(0.9)

    def test_average_confidence(self):
        result = compute_coverage(evidence_items=[], mapping_confidences=[0.8, 0.6])
        conf_factor = next(f for f in result.factors if f["factor"] == "confidence")
        assert conf_factor["score"] == pytest.approx(0.7)

    def test_zero_confidence_if_no_mappings(self):
        result = compute_coverage(evidence_items=[], mapping_confidences=[])
        conf_factor = next(f for f in result.factors if f["factor"] == "confidence")
        assert conf_factor["score"] == 0.0


class TestCategoryThresholds:
    def test_score_below_25_is_weak(self):
        assert _categorise(0.10) == "Weak"
        assert _categorise(0.24) == "Weak"

    def test_score_25_to_50_is_moderate(self):
        assert _categorise(0.25) == "Moderate"
        assert _categorise(0.49) == "Moderate"

    def test_score_50_to_75_is_strong(self):
        assert _categorise(0.50) == "Strong"
        assert _categorise(0.74) == "Strong"

    def test_score_75_and_above_is_complete(self):
        assert _categorise(0.75) == "Complete"
        assert _categorise(1.0) == "Complete"


class TestExplainability:
    def test_all_four_factors_present(self):
        result = compute_coverage(evidence_items=[_ev()], mapping_confidences=[0.8])
        factor_names = {f["factor"] for f in result.factors}
        assert factor_names == {"quantity", "quality", "diversity", "confidence"}

    def test_each_factor_has_contribution_field(self):
        result = compute_coverage(evidence_items=[_ev()], mapping_confidences=[0.8])
        for f in result.factors:
            assert "contribution" in f
            assert "weight" in f
            assert "score" in f

    def test_contributions_sum_to_total(self):
        result = compute_coverage(
            evidence_items=[_ev(reliability=0.8), _ev(ev_type="Report")],
            mapping_confidences=[0.9],
        )
        total_from_factors = sum(f["contribution"] for f in result.factors)
        assert abs(total_from_factors - result.score) < 0.001
