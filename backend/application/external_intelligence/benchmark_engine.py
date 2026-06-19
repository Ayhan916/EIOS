"""Benchmark Engine — M34.

Pure-function engine that calculates supplier percentile rankings against
sector benchmarks. No I/O — receives a SectorBenchmark and a supplier's
ESG score, returns a PercentileRank and explanation.

The explainability principle: every benchmark conclusion must show the
supplier score, the benchmark breakpoints, and the derived rank.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums import PercentileRank
from domain.external_intelligence import SectorBenchmark


@dataclass
class BenchmarkResult:
    """Result of benchmarking a supplier against sector peers."""

    supplier_id: str
    supplier_esg_score: float
    sector_name: str
    nace_code: str
    percentile: float  # Estimated percentile 0–100 (higher = better)
    percentile_rank: str  # PercentileRank value
    benchmark_score: float  # Sector median for reference
    explanation: str
    dataset_id: str
    source_name: str
    source_version: str


def calculate_percentile(supplier_score: float, benchmark: SectorBenchmark) -> float:
    """Estimate supplier percentile (0–100) using benchmark breakpoints.

    Interpolates linearly between known percentile breakpoints.
    Returns 0–100 where 100 = best-in-sector.
    """
    # Breakpoints: (score, percentile_in_benchmark)
    # p10 = 10th percentile score (90% of suppliers score higher)
    # We convert so that percentile_rank = "how many suppliers are BELOW you"
    breakpoints = [
        (benchmark.p10_esg_score, 10.0),
        (benchmark.p25_esg_score, 25.0),
        (benchmark.p50_esg_score, 50.0),
        (benchmark.p75_esg_score, 75.0),
        (benchmark.p90_esg_score, 90.0),
    ]

    # Handle trivial cases
    if supplier_score <= breakpoints[0][0]:
        return max(0.0, breakpoints[0][1] * supplier_score / max(breakpoints[0][0], 0.001))
    if supplier_score >= breakpoints[-1][0]:
        return min(100.0, breakpoints[-1][1] + (100.0 - breakpoints[-1][1]) * 0.5)

    # Linear interpolation between nearest breakpoints
    for i in range(len(breakpoints) - 1):
        lo_score, lo_pct = breakpoints[i]
        hi_score, hi_pct = breakpoints[i + 1]
        if lo_score <= supplier_score <= hi_score:
            if hi_score == lo_score:
                return lo_pct
            frac = (supplier_score - lo_score) / (hi_score - lo_score)
            return lo_pct + frac * (hi_pct - lo_pct)

    return 50.0


def classify_percentile_rank(percentile: float) -> str:
    """Convert a numeric percentile (0–100) to a PercentileRank label."""
    if percentile >= 90.0:
        return PercentileRank.TOP_10
    elif percentile >= 75.0:
        return PercentileRank.TOP_25
    elif percentile >= 25.0:
        return PercentileRank.MEDIAN
    elif percentile >= 10.0:
        return PercentileRank.BOTTOM_25
    else:
        return PercentileRank.BOTTOM_10


def explain_benchmark(
    supplier_score: float,
    benchmark: SectorBenchmark,
    percentile: float,
    rank: str,
) -> str:
    """Generate a human-readable benchmark explanation."""
    rank_labels = {
        PercentileRank.TOP_10: "top 10% of sector peers",
        PercentileRank.TOP_25: "top 25% of sector peers",
        PercentileRank.MEDIAN: "median range of sector peers",
        PercentileRank.BOTTOM_25: "bottom 25% of sector peers",
        PercentileRank.BOTTOM_10: "bottom 10% of sector peers",
    }
    label = rank_labels.get(rank, "an unclassified range")
    return (
        f"Supplier ESG score: {supplier_score:.1f}/100. "
        f"Sector '{benchmark.sector_name}' median: {benchmark.p50_esg_score:.1f}/100 "
        f"(p25={benchmark.p25_esg_score:.1f}, p75={benchmark.p75_esg_score:.1f}). "
        f"Estimated percentile: {percentile:.0f}th — {label}. "
        f"Benchmark source: {benchmark.source_name} v{benchmark.source_version} "
        f"({benchmark.supplier_count} suppliers)."
    )


def benchmark_supplier(
    supplier_id: str,
    supplier_esg_score: float,
    benchmark: SectorBenchmark,
) -> BenchmarkResult:
    """Benchmark a supplier against a SectorBenchmark.

    Pure function — fully explainable, deterministic, no I/O.
    """
    percentile = calculate_percentile(supplier_esg_score, benchmark)
    rank = classify_percentile_rank(percentile)
    explanation = explain_benchmark(supplier_esg_score, benchmark, percentile, rank)

    return BenchmarkResult(
        supplier_id=supplier_id,
        supplier_esg_score=supplier_esg_score,
        sector_name=benchmark.sector_name,
        nace_code=benchmark.nace_code,
        percentile=round(percentile, 1),
        percentile_rank=rank,
        benchmark_score=benchmark.p50_esg_score,
        explanation=explanation,
        dataset_id=benchmark.dataset_id,
        source_name=benchmark.source_name,
        source_version=benchmark.source_version,
    )
