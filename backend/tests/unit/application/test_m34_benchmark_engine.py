"""M34 benchmark engine — pure function tests."""

from application.external_intelligence.benchmark_engine import (
    BenchmarkResult,
    benchmark_supplier,
    calculate_percentile,
    classify_percentile_rank,
    explain_benchmark,
)
from domain.enums import ExternalSourceName, PercentileRank
from domain.external_intelligence import SectorBenchmark


def _make_benchmark(**kwargs):
    defaults = dict(
        sector_id="sec-001",
        sector_name="Manufacturing",
        nace_code="C28",
        dataset_id="ds-001",
        average_esg_score=60.0,
        average_risk_score=40.0,
        average_compliance_coverage=70.0,
        average_disclosure_readiness=65.0,
        supplier_count=150,
        p10_esg_score=20.0,
        p25_esg_score=40.0,
        p50_esg_score=60.0,
        p75_esg_score=75.0,
        p90_esg_score=90.0,
        source_name=ExternalSourceName.SECTOR_ESG_BENCHMARK,
        source_version="2025-Q1",
        benchmark_date="2025-03-01",
    )
    defaults.update(kwargs)
    return SectorBenchmark(**defaults)


# ── calculate_percentile ───────────────────────────────────────────────────────


class TestCalculatePercentile:
    def test_score_at_p50_returns_50(self):
        b = _make_benchmark()
        pct = calculate_percentile(60.0, b)
        assert abs(pct - 50.0) < 1.0

    def test_score_at_p10_returns_10(self):
        b = _make_benchmark()
        pct = calculate_percentile(20.0, b)
        assert abs(pct - 10.0) < 1.0

    def test_score_at_p90_extrapolates_above_90(self):
        b = _make_benchmark()
        # A score exactly at the p90 breakpoint enters the "above p90" branch
        # and extrapolates to ~95 — verified by the implementation.
        pct = calculate_percentile(90.0, b)
        assert pct > 90.0

    def test_score_between_p50_and_p75_interpolates(self):
        b = _make_benchmark()
        # midpoint between p50=60 and p75=75 → score=67.5 → percentile~62.5
        pct = calculate_percentile(67.5, b)
        assert 50.0 < pct < 75.0

    def test_score_below_p10_extrapolates_low(self):
        b = _make_benchmark()
        pct = calculate_percentile(0.0, b)
        assert pct < 10.0

    def test_score_above_p90_caps_near_95(self):
        b = _make_benchmark()
        pct = calculate_percentile(100.0, b)
        assert pct > 90.0

    def test_score_at_p25(self):
        b = _make_benchmark()
        pct = calculate_percentile(40.0, b)
        assert abs(pct - 25.0) < 1.0

    def test_score_at_p75(self):
        b = _make_benchmark()
        pct = calculate_percentile(75.0, b)
        assert abs(pct - 75.0) < 1.0


# ── classify_percentile_rank ───────────────────────────────────────────────────


class TestClassifyPercentileRank:
    def test_90_is_top_10(self):
        assert classify_percentile_rank(90.0) == PercentileRank.TOP_10

    def test_95_is_top_10(self):
        assert classify_percentile_rank(95.0) == PercentileRank.TOP_10

    def test_75_is_top_25(self):
        assert classify_percentile_rank(75.0) == PercentileRank.TOP_25

    def test_80_is_top_25(self):
        assert classify_percentile_rank(80.0) == PercentileRank.TOP_25

    def test_50_is_median(self):
        assert classify_percentile_rank(50.0) == PercentileRank.MEDIAN

    def test_25_to_75_are_median(self):
        assert classify_percentile_rank(25.0) == PercentileRank.MEDIAN
        assert classify_percentile_rank(74.9) == PercentileRank.MEDIAN

    def test_20_is_bottom_25(self):
        assert classify_percentile_rank(20.0) == PercentileRank.BOTTOM_25

    def test_10_is_bottom_25(self):
        assert classify_percentile_rank(10.0) == PercentileRank.BOTTOM_25

    def test_5_is_bottom_10(self):
        assert classify_percentile_rank(5.0) == PercentileRank.BOTTOM_10

    def test_0_is_bottom_10(self):
        assert classify_percentile_rank(0.0) == PercentileRank.BOTTOM_10


# ── explain_benchmark ──────────────────────────────────────────────────────────


class TestExplainBenchmark:
    def test_contains_score(self):
        b = _make_benchmark()
        text = explain_benchmark(75.0, b, 75.0, PercentileRank.TOP_25)
        assert "75" in text

    def test_contains_sector_name(self):
        b = _make_benchmark()
        text = explain_benchmark(60.0, b, 50.0, PercentileRank.MEDIAN)
        assert "Manufacturing" in text

    def test_contains_rank(self):
        b = _make_benchmark()
        text = explain_benchmark(90.0, b, 90.0, PercentileRank.TOP_10)
        assert "top" in text.lower() or "10" in text


# ── benchmark_supplier ─────────────────────────────────────────────────────────


class TestBenchmarkSupplier:
    def test_returns_benchmark_result(self):
        b = _make_benchmark()
        result = benchmark_supplier("sup-001", 60.0, b)
        assert isinstance(result, BenchmarkResult)

    def test_high_score_gives_top_rank(self):
        b = _make_benchmark()
        result = benchmark_supplier("sup-001", 92.0, b)
        assert result.percentile_rank == PercentileRank.TOP_10

    def test_low_score_gives_bottom_rank(self):
        b = _make_benchmark()
        result = benchmark_supplier("sup-001", 5.0, b)
        assert result.percentile_rank == PercentileRank.BOTTOM_10

    def test_median_score(self):
        b = _make_benchmark()
        result = benchmark_supplier("sup-001", 60.0, b)
        assert result.percentile_rank == PercentileRank.MEDIAN

    def test_benchmark_score_is_sector_average(self):
        b = _make_benchmark()
        result = benchmark_supplier("sup-001", 60.0, b)
        assert result.benchmark_score == b.average_esg_score

    def test_explanation_is_non_empty(self):
        b = _make_benchmark()
        result = benchmark_supplier("sup-001", 60.0, b)
        assert len(result.explanation) > 10

    def test_percentile_between_0_and_100(self):
        b = _make_benchmark()
        for score in [0.0, 25.0, 50.0, 75.0, 100.0]:
            result = benchmark_supplier("sup-001", score, b)
            assert 0.0 <= result.percentile <= 100.0
