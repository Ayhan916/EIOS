"""M48.2 G-032 — Supplier Benchmarking (Branchenvergleich).

Computes a supplier's ESG score relative to sector peers within the org.
All calculations are deterministic and auditable — no generative AI.

Methodology:
  - Peer group: suppliers in the same industry/sector within the org.
  - Percentile rank: position within peer distribution.
  - Performance tiers: Top Quartile / Above Average / Below Average / Bottom Quartile.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BenchmarkResult:
    supplier_id: str
    supplier_name: str
    organization_id: str
    # Supplier's own scores
    overall_score: float | None
    environmental_score: float | None
    social_score: float | None
    governance_score: float | None
    # Peer group stats
    peer_count: int
    peer_industry: str | None
    # Percentile ranks (0–100)
    overall_percentile: float | None
    environmental_percentile: float | None
    social_percentile: float | None
    governance_percentile: float | None
    # Classification
    performance_tier: str  # Top Quartile | Above Average | Below Average | Bottom Quartile
    # Insight
    strengths: list[str]
    improvement_areas: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "organization_id": self.organization_id,
            "scores": {
                "overall": self.overall_score,
                "environmental": self.environmental_score,
                "social": self.social_score,
                "governance": self.governance_score,
            },
            "peer_group": {
                "count": self.peer_count,
                "industry": self.peer_industry,
            },
            "percentile_ranks": {
                "overall": self.overall_percentile,
                "environmental": self.environmental_percentile,
                "social": self.social_percentile,
                "governance": self.governance_percentile,
            },
            "performance_tier": self.performance_tier,
            "strengths": self.strengths,
            "improvement_areas": self.improvement_areas,
        }


def _percentile_rank(value: float, peer_values: list[float]) -> float:
    """Compute percentile rank of value within peer_values (0–100)."""
    if not peer_values:
        return 50.0
    below = sum(1 for v in peer_values if v < value)
    equal = sum(1 for v in peer_values if v == value)
    n = len(peer_values)
    return round((below + 0.5 * equal) / n * 100, 1)


def _tier(percentile: float | None) -> str:
    if percentile is None:
        return "Insufficient Data"
    if percentile >= 75:
        return "Top Quartile"
    if percentile >= 50:
        return "Above Average"
    if percentile >= 25:
        return "Below Average"
    return "Bottom Quartile"


def compute_benchmark(
    *,
    supplier_id: str,
    supplier_name: str,
    organization_id: str,
    supplier_scores: dict[str, Any],
    peers: list[dict[str, Any]],
    peer_industry: str | None = None,
) -> BenchmarkResult:
    """Compute benchmark position for a supplier against its peer group.

    Args:
        supplier_scores: {overall_esg_score, environmental_score, social_score, governance_score}
        peers: list of peer supplier score dicts (same structure, excluding the target supplier)
    """
    def score(d: dict, key: str) -> float | None:
        v = d.get(key)
        return float(v) if v is not None else None

    own_overall = score(supplier_scores, "overall_esg_score")
    own_env = score(supplier_scores, "environmental_score")
    own_social = score(supplier_scores, "social_score")
    own_gov = score(supplier_scores, "governance_score")

    peer_overall = [v for p in peers if (v := score(p, "overall_esg_score")) is not None]
    peer_env = [v for p in peers if (v := score(p, "environmental_score")) is not None]
    peer_social = [v for p in peers if (v := score(p, "social_score")) is not None]
    peer_gov = [v for p in peers if (v := score(p, "governance_score")) is not None]

    overall_pct = _percentile_rank(own_overall, peer_overall) if own_overall is not None else None
    env_pct = _percentile_rank(own_env, peer_env) if own_env is not None else None
    social_pct = _percentile_rank(own_social, peer_social) if own_social is not None else None
    gov_pct = _percentile_rank(own_gov, peer_gov) if own_gov is not None else None

    tier = _tier(overall_pct)

    # Derive strengths and improvement areas
    dimension_pcts = {
        "Environmental": env_pct,
        "Social": social_pct,
        "Governance": gov_pct,
    }
    strengths = [d for d, p in dimension_pcts.items() if p is not None and p >= 70]
    improvements = [d for d, p in dimension_pcts.items() if p is not None and p < 40]

    return BenchmarkResult(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        organization_id=organization_id,
        overall_score=own_overall,
        environmental_score=own_env,
        social_score=own_social,
        governance_score=own_gov,
        peer_count=len(peers),
        peer_industry=peer_industry,
        overall_percentile=overall_pct,
        environmental_percentile=env_pct,
        social_percentile=social_pct,
        governance_percentile=gov_pct,
        performance_tier=tier,
        strengths=strengths,
        improvement_areas=improvements,
    )
