"""Domain Value Objects for EIOS.

Value Objects are immutable, equality-by-value, and carry no identity.
All fields use frozen dataclasses or NamedTuples.

ADR-015: ConfidenceCard is the standard confidence representation across the platform.
ADR-002: RiskScore is deterministic and versioned — never computed by an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums import ConfidenceLevel, RiskBand


@dataclass(frozen=True)
class ConfidenceCard:
    """Standard confidence representation for any AI-assisted output (ADR-015).

    Attributes:
        level:       Qualitative band (LOW / MEDIUM / HIGH).
        score:       Quantitative probability 0.0–1.0.
        basis:       Human-readable reason this confidence was assigned.
        limitations: Known gaps that reduce reliability.
    """

    level: ConfidenceLevel
    score: float
    basis: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"ConfidenceCard.score must be 0.0–1.0, got {self.score}")


@dataclass(frozen=True)
class FactorScore:
    """Single factor contribution to the composite RiskScore.

    Attributes:
        factor:       Machine-readable factor name (e.g. "critical_findings").
        count:        Raw count of this factor.
        weight:       Per-unit weight used in the formula.
        contribution: Normalised contribution to the composite score (count × weight / 5).
    """

    factor: str
    count: int
    weight: float
    contribution: float


@dataclass(frozen=True)
class RiskScore:
    """Deterministic, versioned composite risk score (ADR-002).

    Attributes:
        composite_score:  Normalised 0.0–100.0 (higher = more risk).
        band:             Qualitative band (LOW / MODERATE / HIGH / CRITICAL).
        formula_version:  Exact version string — changes when formula weights change.
        factor_breakdown: Immutable tuple of all factor contributions for auditability.
        confidence:       ConfidenceCard expressing data quality for this score.
    """

    composite_score: float
    band: RiskBand
    formula_version: str
    factor_breakdown: tuple[FactorScore, ...]
    confidence: ConfidenceCard

    def __post_init__(self) -> None:
        if not 0.0 <= self.composite_score <= 100.0:
            raise ValueError(
                f"RiskScore.composite_score must be 0–100, got {self.composite_score}"
            )
