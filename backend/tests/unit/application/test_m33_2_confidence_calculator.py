"""M33.2 — Confidence Calculator Tests.

Verifies score formula, threshold boundaries, and factor composition.
Pure function — no I/O.
"""

from __future__ import annotations

from application.copilot.confidence_calculator import calculate_confidence
from application.copilot.contradiction_detector import ContradictionRecord
from application.copilot.freshness_tracker import FreshnessReport
from application.copilot.retrieval.base import RetrievalResult
from domain.enums import ContradictionType, CopilotConfidenceLevel


def _result(retriever: str, has_data: bool = True, citation_type: str = "Supplier") -> RetrievalResult:
    return RetrievalResult(
        retriever=retriever,
        provenance="test",
        data=[{"id": "x"}] if has_data else [],
        source_ids=["x"] if has_data else [],
        citation_type=citation_type if has_data else "",
    )


def _fresh_report(avg_age_days: float = 0.0) -> FreshnessReport:
    return FreshnessReport(average_age_days=avg_age_days)


def _contradiction(t: str = ContradictionType.RISK_VS_COMPLIANCE) -> ContradictionRecord:
    return ContradictionRecord(contradiction_type=t, description="test")


class TestThresholds:
    def test_very_high_on_full_coverage(self):
        results = [
            _result("supplier_retriever", citation_type="Supplier"),
            _result("compliance_retriever", citation_type="ComplianceGap"),
            _result("disclosure_retriever", citation_type="Disclosure"),
            _result("executive_retriever", citation_type="ExecutiveSummary"),
        ]
        citations = [
            {"citation_type": "Supplier", "object_id": "s1"},
            {"citation_type": "ComplianceGap", "object_id": "g1"},
            {"citation_type": "Disclosure", "object_id": "d1"},
            {"citation_type": "ExecutiveSummary", "object_id": "e1"},
            {"citation_type": "Supplier", "object_id": "s2"},
        ]
        level, factors = calculate_confidence(results, citations, [], _fresh_report(0.0))
        assert level == CopilotConfidenceLevel.VERY_HIGH
        assert factors["raw_score"] >= 80.0

    def test_low_on_empty_context(self):
        results = [_result("supplier_retriever", has_data=False)]
        level, factors = calculate_confidence(results, [], [], _fresh_report())
        assert level == CopilotConfidenceLevel.LOW
        assert factors["raw_score"] < 40.0

    def test_moderate_on_partial_coverage(self):
        results = [
            _result("supplier_retriever", citation_type="Supplier"),
            _result("compliance_retriever", has_data=False),
        ]
        citations = [{"citation_type": "Supplier", "object_id": "s1"}]
        level, factors = calculate_confidence(results, citations, [], _fresh_report(30.0))
        assert level in (CopilotConfidenceLevel.MODERATE, CopilotConfidenceLevel.LOW)


class TestFactorComponents:
    def test_retrieval_coverage_correct(self):
        results = [
            _result("supplier_retriever"),
            _result("compliance_retriever", has_data=False),
        ]
        _, factors = calculate_confidence(results, [], [], _fresh_report())
        assert factors["retrieval_coverage"] == 0.5

    def test_full_retrieval_coverage(self):
        results = [_result("supplier_retriever"), _result("compliance_retriever")]
        _, factors = calculate_confidence(results, [], [], _fresh_report())
        assert factors["retrieval_coverage"] == 1.0

    def test_zero_coverage_zero_retrieval(self):
        results = [_result("supplier_retriever", has_data=False)]
        _, factors = calculate_confidence(results, [], [], _fresh_report())
        assert factors["retrieval_coverage"] == 0.0

    def test_citation_count_captured(self):
        citations = [{"citation_type": "Supplier", "object_id": f"s{i}"} for i in range(3)]
        _, factors = calculate_confidence([_result("supplier_retriever")], citations, [], _fresh_report())
        assert factors["citation_count"] == 3

    def test_source_diversity_captured(self):
        results = [
            _result("supplier_retriever", citation_type="Supplier"),
            _result("compliance_retriever", citation_type="ComplianceGap"),
        ]
        _, factors = calculate_confidence(results, [], [], _fresh_report())
        assert factors["source_diversity"] == 2

    def test_freshness_reduces_score_for_old_data(self):
        results = [_result("supplier_retriever")]
        citations = [{"citation_type": "Supplier", "object_id": "s1"}]
        _, fresh_factors = calculate_confidence(results, citations, [], _fresh_report(0.0))
        _, stale_factors = calculate_confidence(results, citations, [], _fresh_report(90.0))
        assert fresh_factors["raw_score"] > stale_factors["raw_score"]

    def test_contradiction_penalty_applied(self):
        results = [_result("supplier_retriever")]
        citations = [{"citation_type": "Supplier", "object_id": "s1"}]
        no_contradiction_level, no_factors = calculate_confidence(results, citations, [], _fresh_report())
        contradiction_level, with_factors = calculate_confidence(
            results, citations, [_contradiction()], _fresh_report()
        )
        assert with_factors["raw_score"] < no_factors["raw_score"]

    def test_contradiction_penalty_capped_at_15(self):
        results = [_result("supplier_retriever")]
        contradictions = [_contradiction() for _ in range(10)]
        _, factors = calculate_confidence(results, [], contradictions, _fresh_report())
        no_contradiction_score = (0 + 0 + 0 + 15.0 + 5.0)  # coverage=0, citation=0, diversity=0, fresh=15, presence=5
        assert no_contradiction_score - factors["raw_score"] <= 15.0

    def test_level_matches_factors_level_field(self):
        results = [_result("supplier_retriever")]
        level, factors = calculate_confidence(results, [], [], _fresh_report())
        assert factors["level"] == level.value

    def test_factors_rounded(self):
        results = [_result("supplier_retriever")]
        _, factors = calculate_confidence(results, [], [], _fresh_report(avg_age_days=33.33333))
        assert factors["average_data_age_days"] == round(33.33333, 1)


class TestBoundaryScores:
    def test_score_never_below_zero(self):
        results = []
        contradictions = [_contradiction() for _ in range(10)]
        _, factors = calculate_confidence(results, [], contradictions, _fresh_report(200.0))
        assert factors["raw_score"] >= 0.0

    def test_score_never_above_100(self):
        results = [_result(f"r{i}", citation_type="Supplier") for i in range(10)]
        citations = [{"citation_type": "Supplier", "object_id": f"s{i}"} for i in range(20)]
        _, factors = calculate_confidence(results, citations, [], _fresh_report(0.0))
        assert factors["raw_score"] <= 100.0

    def test_exactly_at_very_high_threshold(self):
        results = [
            _result("supplier_retriever", citation_type="Supplier"),
            _result("compliance_retriever", citation_type="ComplianceGap"),
        ]
        citations = [{"citation_type": "Supplier", "object_id": f"s{i}"} for i in range(5)]
        level, factors = calculate_confidence(results, citations, [], _fresh_report(0.0))
        if factors["raw_score"] >= 80.0:
            assert level == CopilotConfidenceLevel.VERY_HIGH
        elif factors["raw_score"] >= 60.0:
            assert level == CopilotConfidenceLevel.HIGH
