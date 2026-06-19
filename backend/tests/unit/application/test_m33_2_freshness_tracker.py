"""M33.2 — Data Freshness Layer Tests.

Validates per-retriever staleness thresholds, age calculations,
freshness report building, and prompt formatting.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from application.copilot.freshness_tracker import (
    FreshnessReport,
    analyze_freshness,
    format_freshness_for_prompt,
    freshness_summary_dict,
)
from application.copilot.retrieval.base import RetrievalResult


def _ts(days_ago: float) -> str:
    dt = datetime.now(UTC) - timedelta(days=days_ago)
    return dt.isoformat()


def _result_with_freshness(retriever: str, days_old: float) -> RetrievalResult:
    retrieved_at = _ts(0)
    updated_at = _ts(days_old)
    return RetrievalResult(
        retriever=retriever,
        provenance="test",
        data=[{"id": "x"}],
        source_ids=["x"],
        citation_type="Supplier",
        freshness_metadata=[
            {
                "object_id": "x",
                "object_type": "SupplierScore",
                "updated_at": updated_at,
                "retrieved_at": retrieved_at,
            }
        ],
    )


class TestAnalyzeFreshness:
    def test_empty_results_returns_zero_report(self):
        report = analyze_freshness([])
        assert report.average_age_days == 0.0
        assert report.has_stale_data is False

    def test_result_without_freshness_metadata_ignored(self):
        result = RetrievalResult(
            retriever="supplier_retriever",
            provenance="test",
            data=[{"id": "x"}],
            source_ids=["x"],
            citation_type="Supplier",
        )
        report = analyze_freshness([result])
        assert report.average_age_days == 0.0

    def test_fresh_supplier_data_not_stale(self):
        result = _result_with_freshness("supplier_retriever", days_old=3)
        report = analyze_freshness([result])
        assert "supplier_retriever" not in report.stale_retrievers
        assert report.has_stale_data is False

    def test_stale_supplier_data_flagged(self):
        result = _result_with_freshness("supplier_retriever", days_old=10)
        report = analyze_freshness([result])
        assert "supplier_retriever" in report.stale_retrievers
        assert report.has_stale_data is True

    def test_compliance_staleness_threshold_30_days(self):
        fresh = _result_with_freshness("compliance_retriever", days_old=25)
        stale = _result_with_freshness("compliance_retriever", days_old=35)
        fresh_report = analyze_freshness([fresh])
        stale_report = analyze_freshness([stale])
        assert "compliance_retriever" not in fresh_report.stale_retrievers
        assert "compliance_retriever" in stale_report.stale_retrievers

    def test_disclosure_staleness_threshold_14_days(self):
        fresh = _result_with_freshness("disclosure_retriever", days_old=10)
        stale = _result_with_freshness("disclosure_retriever", days_old=20)
        fresh_report = analyze_freshness([fresh])
        stale_report = analyze_freshness([stale])
        assert "disclosure_retriever" not in fresh_report.stale_retrievers
        assert "disclosure_retriever" in stale_report.stale_retrievers

    def test_due_diligence_threshold_60_days(self):
        fresh = _result_with_freshness("due_diligence_retriever", days_old=50)
        stale = _result_with_freshness("due_diligence_retriever", days_old=70)
        fresh_report = analyze_freshness([fresh])
        stale_report = analyze_freshness([stale])
        assert "due_diligence_retriever" not in fresh_report.stale_retrievers
        assert "due_diligence_retriever" in stale_report.stale_retrievers

    def test_age_computed_correctly(self):
        result = _result_with_freshness("supplier_retriever", days_old=5)
        report = analyze_freshness([result])
        assert 4.5 <= report.average_age_days <= 5.5

    def test_oldest_and_newest_age_correct(self):
        old = _result_with_freshness("compliance_retriever", days_old=20)
        new = _result_with_freshness("supplier_retriever", days_old=2)
        report = analyze_freshness([old, new])
        assert report.oldest_age_days > report.newest_age_days
        assert report.oldest_age_days >= 18

    def test_multiple_objects_average_age(self):
        retrieved_at = _ts(0)
        result = RetrievalResult(
            retriever="supplier_retriever",
            provenance="test",
            data=[{"id": "x"}, {"id": "y"}],
            source_ids=["x", "y"],
            citation_type="Supplier",
            freshness_metadata=[
                {"object_id": "x", "object_type": "S", "updated_at": _ts(4), "retrieved_at": retrieved_at},
                {"object_id": "y", "object_type": "S", "updated_at": _ts(6), "retrieved_at": retrieved_at},
            ],
        )
        report = analyze_freshness([result])
        assert 4.5 <= report.average_age_days <= 5.5

    def test_freshness_warning_populated_for_stale(self):
        result = _result_with_freshness("supplier_retriever", days_old=10)
        report = analyze_freshness([result])
        assert "STALE DATA WARNING" in report.freshness_warning
        assert "supplier" in report.freshness_warning

    def test_no_warning_when_fresh(self):
        result = _result_with_freshness("supplier_retriever", days_old=2)
        report = analyze_freshness([result])
        assert report.freshness_warning == ""


class TestFormatFreshnessForPrompt:
    def test_returns_empty_when_all_fresh(self):
        report = FreshnessReport(has_stale_data=False, freshness_warning="")
        assert format_freshness_for_prompt(report) == ""

    def test_returns_warning_when_stale(self):
        report = FreshnessReport(
            has_stale_data=True,
            freshness_warning="STALE DATA WARNING: supplier data (10 days old).",
        )
        result = format_freshness_for_prompt(report)
        assert "STALE DATA WARNING" in result


class TestFreshnessSummaryDict:
    def test_all_keys_present(self):
        result = _result_with_freshness("supplier_retriever", days_old=5)
        report = analyze_freshness([result])
        d = freshness_summary_dict(report)
        assert "oldest_age_days" in d
        assert "newest_age_days" in d
        assert "average_age_days" in d
        assert "has_stale_data" in d
        assert "stale_retrievers" in d
        assert "freshness_by_retriever" in d

    def test_values_are_serializable(self):
        import json
        result = _result_with_freshness("supplier_retriever", days_old=5)
        report = analyze_freshness([result])
        d = freshness_summary_dict(report)
        dumped = json.dumps(d)
        assert isinstance(dumped, str)

    def test_values_rounded_to_one_decimal(self):
        result = _result_with_freshness("supplier_retriever", days_old=5)
        report = analyze_freshness([result])
        d = freshness_summary_dict(report)
        assert d["average_age_days"] == round(d["average_age_days"], 1)
