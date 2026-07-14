"""Deterministic RiskScore calculator (ADR-002).

This module is the single source of truth for composite risk scoring.
It wraps the pure `calculate_risk_score()` function and produces a fully-auditable
`RiskScore` Value Object that carries:
  - the composite 0–100 score and band
  - the exact formula version (bumped whenever weights change)
  - a per-factor breakdown for auditability and UI display
  - a `ConfidenceCard` expressing the reliability of the score given data completeness

No LLM is involved (ADR-001 / ADR-002). All inputs are integers; all outputs are
deterministic — same inputs → identical `RiskScore` every time.
"""

from __future__ import annotations

from domain.enums import ConfidenceLevel
from domain.value_objects import ConfidenceCard, FactorScore, RiskScore

from .supplier_scorer import ScoreInputs, calculate_risk_score

FORMULA_VERSION = "RiskScore-v1.0"

# Factor weights mirror the formula in supplier_scorer.calculate_risk_score().
# Update FORMULA_VERSION whenever any weight changes.
_FACTOR_WEIGHTS: list[tuple[str, float]] = [
    ("critical_findings", 20.0),
    ("high_findings", 10.0),
    ("medium_findings", 3.0),
    ("low_findings", 1.0),
    ("critical_risks", 15.0),
    ("high_risks", 7.0),
    ("medium_risks", 2.0),
    ("overdue_actions", 8.0),
    ("open_actions", 3.0),
]

# Normalisation divisor — matches `raw / 5.0` in calculate_risk_score()
_NORMALISER = 5.0


def _derive_confidence(inputs: ScoreInputs) -> ConfidenceCard:
    """Derive a ConfidenceCard from data completeness.

    HIGH  — at least one assessment AND ≥3 total findings across all severities
    MEDIUM — at least one assessment AND ≥1 finding
    LOW   — no assessments or no findings at all
    """
    total_findings = (
        inputs.critical_findings
        + inputs.high_findings
        + inputs.medium_findings
        + inputs.low_findings
    )

    if inputs.total_assessments >= 1 and total_findings >= 3:
        return ConfidenceCard(
            level=ConfidenceLevel.HIGH,
            score=0.85,
            basis="Multiple validated findings across severity levels",
        )

    if inputs.total_assessments >= 1 and total_findings >= 1:
        return ConfidenceCard(
            level=ConfidenceLevel.MEDIUM,
            score=0.65,
            basis="Limited findings — score may underrepresent actual risk",
            limitations=("Fewer than 3 findings — risk may be underestimated",),
        )

    return ConfidenceCard(
        level=ConfidenceLevel.LOW,
        score=0.35,
        basis="Insufficient evidence — risk score based on absent data",
        limitations=(
            "No completed findings recorded",
            "Score defaults may not reflect actual supplier risk",
        ),
    )


def _build_factor_breakdown(inputs: ScoreInputs) -> tuple[FactorScore, ...]:
    counts: dict[str, int] = {
        "critical_findings": inputs.critical_findings,
        "high_findings": inputs.high_findings,
        "medium_findings": inputs.medium_findings,
        "low_findings": inputs.low_findings,
        "critical_risks": inputs.critical_risks,
        "high_risks": inputs.high_risks,
        "medium_risks": inputs.medium_risks,
        "overdue_actions": inputs.overdue_actions,
        "open_actions": inputs.open_actions,
    }
    return tuple(
        FactorScore(
            factor=factor,
            count=counts[factor],
            weight=weight,
            contribution=round(counts[factor] * weight / _NORMALISER, 2),
        )
        for factor, weight in _FACTOR_WEIGHTS
    )


def calculate(inputs: ScoreInputs) -> RiskScore:
    """Return a deterministic, versioned RiskScore for the given ScoreInputs.

    The result is a frozen Value Object — safe to cache, compare, and serialise.
    """
    composite_score, band = calculate_risk_score(inputs)
    return RiskScore(
        composite_score=composite_score,
        band=band,
        formula_version=FORMULA_VERSION,
        factor_breakdown=_build_factor_breakdown(inputs),
        confidence=_derive_confidence(inputs),
    )
