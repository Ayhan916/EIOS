"""
Supplier Scoring Engine — M28

All functions are pure (no I/O, no side effects).

Scoring Methodology v1.0
────────────────────────

RISK SCORE (0-100, higher = more risk)
  raw = critical_findings × 20
      + high_findings     × 10
      + medium_findings   ×  3
      + low_findings      ×  1
      + critical_risks    × 15
      + high_risks        ×  7
      + medium_risks      ×  2
      + overdue_actions   ×  8
      + open_actions      ×  3

  risk_score = min(100, raw / 5)

  Risk Bands:
    Low       0 – 25
    Moderate 26 – 50
    High     51 – 75
    Critical 76 – 100

ESG SCORE (0-100, higher = better)
  Per-pillar:
    deduction = critical × 12 + high × 6 + medium × 2 + low × 0.5
    pillar_score = max(0, 100 – deduction)

  ESG Total = (environmental + social + governance) / 3

TREND
  delta = current_esg_score − previous_esg_score
  Improving     if delta > +3
  Deteriorating if delta < −3
  Stable        otherwise

BENCHMARKING
  Percentile = (suppliers_with_higher_risk_score / total_peers) × 100
  A high percentile means the supplier has LOWER risk than peers
  (i.e. lower risk_score = better = higher percentile).
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums import RiskBand, TrendDirection

SCORE_VERSION = "1.0"


@dataclass(frozen=True)
class ScoreInputs:
    total_assessments: int = 0
    approved_assessments: int = 0

    # Findings by severity
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0

    # Risks by level
    critical_risks: int = 0
    high_risks: int = 0
    medium_risks: int = 0
    low_risks: int = 0

    # Recommendations / actions
    open_actions: int = 0
    overdue_actions: int = 0

    # Findings by ESG pillar (Environmental)
    env_critical: int = 0
    env_high: int = 0
    env_medium: int = 0
    env_low: int = 0

    # Findings by ESG pillar (Social)
    social_critical: int = 0
    social_high: int = 0
    social_medium: int = 0
    social_low: int = 0

    # Findings by ESG pillar (Governance)
    gov_critical: int = 0
    gov_high: int = 0
    gov_medium: int = 0
    gov_low: int = 0


def calculate_risk_score(inputs: ScoreInputs) -> tuple[float, RiskBand]:
    raw = (
        inputs.critical_findings * 20
        + inputs.high_findings * 10
        + inputs.medium_findings * 3
        + inputs.low_findings * 1
        + inputs.critical_risks * 15
        + inputs.high_risks * 7
        + inputs.medium_risks * 2
        + inputs.overdue_actions * 8
        + inputs.open_actions * 3
    )
    score = round(min(100.0, raw / 5.0), 1)
    if score <= 25.0:
        band = RiskBand.LOW
    elif score <= 50.0:
        band = RiskBand.MODERATE
    elif score <= 75.0:
        band = RiskBand.HIGH
    else:
        band = RiskBand.CRITICAL
    return score, band


def _pillar_score(critical: int, high: int, medium: int, low: int) -> float:
    deduction = critical * 12.0 + high * 6.0 + medium * 2.0 + low * 0.5
    return round(max(0.0, 100.0 - deduction), 1)


def calculate_esg_scores(inputs: ScoreInputs) -> tuple[float, float, float, float]:
    """Return (total, environmental, social, governance) — all 0-100, higher = better."""
    env = _pillar_score(inputs.env_critical, inputs.env_high, inputs.env_medium, inputs.env_low)
    social = _pillar_score(
        inputs.social_critical, inputs.social_high, inputs.social_medium, inputs.social_low
    )
    gov = _pillar_score(inputs.gov_critical, inputs.gov_high, inputs.gov_medium, inputs.gov_low)
    total = round((env + social + gov) / 3.0, 1)
    return total, env, social, gov


def calculate_trend(
    current_esg: float,
    previous_esg: float | None,
) -> tuple[TrendDirection, float]:
    """Return (direction, delta) where delta = current - previous."""
    if previous_esg is None:
        return TrendDirection.STABLE, 0.0
    delta = round(current_esg - previous_esg, 1)
    if delta > 3.0:
        return TrendDirection.IMPROVING, delta
    if delta < -3.0:
        return TrendDirection.DETERIORATING, delta
    return TrendDirection.STABLE, delta


def build_drivers(inputs: ScoreInputs) -> list[dict]:
    """
    Produce a human-readable list of score drivers, ordered by impact.

    Each entry has: factor, count, impact (high/medium/low), description.
    Only populated for non-zero counts so the list is always actionable.
    """
    drivers: list[dict] = []

    def _add(factor: str, count: int, impact: str, description: str) -> None:
        if count > 0:
            drivers.append(
                {
                    "factor": factor,
                    "count": count,
                    "impact": impact,
                    "description": description,
                }
            )

    _add(
        "Critical Findings",
        inputs.critical_findings,
        "high",
        f"{inputs.critical_findings} critical finding(s) require immediate attention",
    )
    _add(
        "Overdue Actions",
        inputs.overdue_actions,
        "high",
        f"{inputs.overdue_actions} action(s) are past their due date",
    )
    _add(
        "Critical Risks",
        inputs.critical_risks,
        "high",
        f"{inputs.critical_risks} critical risk(s) have been identified",
    )
    _add(
        "High Findings",
        inputs.high_findings,
        "medium",
        f"{inputs.high_findings} high-severity finding(s) need resolution",
    )
    _add(
        "High Risks",
        inputs.high_risks,
        "medium",
        f"{inputs.high_risks} high-level risk(s) identified",
    )
    _add(
        "Open Actions",
        inputs.open_actions,
        "low",
        f"{inputs.open_actions} action(s) are pending resolution",
    )
    _add(
        "Medium Findings",
        inputs.medium_findings,
        "low",
        f"{inputs.medium_findings} medium-severity finding(s)",
    )
    _add(
        "Medium Risks",
        inputs.medium_risks,
        "low",
        f"{inputs.medium_risks} medium-level risk(s)",
    )
    return drivers
