"""Risk Score Explainability Service (E5-F1).

Converts a `RiskScore` Value Object (from E2-F1) into a human-readable,
structured explanation ready for API serialisation and UI factor-bar rendering.

No LLM. No I/O. Pure transformation of the already-computed RiskScore.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects import FactorScore, RiskScore

# Human-readable labels for each factor (for UI display)
_FACTOR_LABELS: dict[str, str] = {
    "critical_findings": "Critical Findings",
    "high_findings": "High Findings",
    "medium_findings": "Medium Findings",
    "low_findings": "Low Findings",
    "critical_risks": "Critical Risks",
    "high_risks": "High Risks",
    "medium_risks": "Medium Risks",
    "overdue_actions": "Overdue Actions",
    "open_actions": "Open Actions",
}

# Impact tier for UI colour coding
_FACTOR_IMPACT: dict[str, str] = {
    "critical_findings": "critical",
    "high_findings": "high",
    "medium_findings": "medium",
    "low_findings": "low",
    "critical_risks": "critical",
    "high_risks": "high",
    "medium_risks": "medium",
    "overdue_actions": "high",
    "open_actions": "medium",
}


@dataclass(frozen=True)
class FactorExplanation:
    """Single factor in the risk score explanation.

    Attributes:
        factor:        Machine-readable factor name.
        label:         Human-readable label for the UI.
        count:         Raw count of this factor.
        weight:        Per-unit weight in the formula.
        contribution:  Normalised contribution to the composite score.
        pct_of_total:  Contribution as percentage of composite_score (0–100).
        impact:        "critical" | "high" | "medium" | "low" for UI colour.
    """

    factor: str
    label: str
    count: int
    weight: float
    contribution: float
    pct_of_total: float
    impact: str


@dataclass(frozen=True)
class RiskScoreExplanation:
    """Full explanation of a supplier's composite risk score.

    Attributes:
        composite_score:    0–100, higher = more risk.
        band:               "Low" | "Moderate" | "High" | "Critical".
        formula_version:    e.g. "RiskScore-v1.0" — identifies the formula used.
        factors:            All 9 factors with their individual contributions.
        top_drivers:        Top 3 non-zero factors by contribution (for summary UI).
        confidence_level:   "Low" | "Medium" | "High".
        confidence_score:   0–1.
        confidence_basis:   Why this confidence level was assigned.
        limitations:        Known gaps affecting score reliability.
    """

    composite_score: float
    band: str
    formula_version: str
    factors: tuple[FactorExplanation, ...]
    top_drivers: tuple[FactorExplanation, ...]
    confidence_level: str
    confidence_score: float
    confidence_basis: str
    limitations: tuple[str, ...]


def _pct(contribution: float, composite: float) -> float:
    if composite == 0.0:
        return 0.0
    return round(contribution / composite * 100, 1)


def _factor_explanation(fs: FactorScore, composite: float) -> FactorExplanation:
    return FactorExplanation(
        factor=fs.factor,
        label=_FACTOR_LABELS.get(fs.factor, fs.factor),
        count=fs.count,
        weight=fs.weight,
        contribution=fs.contribution,
        pct_of_total=_pct(fs.contribution, composite),
        impact=_FACTOR_IMPACT.get(fs.factor, "medium"),
    )


class ExplainabilityService:
    """Convert a RiskScore VO into a structured explanation.

    Stateless — no I/O, no dependencies, fully testable.
    """

    def explain(self, risk_score: RiskScore) -> RiskScoreExplanation:
        """Produce a RiskScoreExplanation from a computed RiskScore."""
        composite = risk_score.composite_score
        factors = tuple(
            _factor_explanation(fs, composite) for fs in risk_score.factor_breakdown
        )
        top_drivers = tuple(
            sorted(
                (f for f in factors if f.count > 0),
                key=lambda f: f.contribution,
                reverse=True,
            )[:3]
        )
        return RiskScoreExplanation(
            composite_score=composite,
            band=risk_score.band.value,
            formula_version=risk_score.formula_version,
            factors=factors,
            top_drivers=top_drivers,
            confidence_level=risk_score.confidence.level.value,
            confidence_score=risk_score.confidence.score,
            confidence_basis=risk_score.confidence.basis,
            limitations=risk_score.confidence.limitations,
        )
