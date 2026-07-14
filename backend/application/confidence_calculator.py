"""ConfidenceCalculator — standardised ConfidenceCard computation (ADR-015 / E4-F1).

Replaces ad-hoc confidence logic scattered across services with a single,
testable function. All callers (RiskScore, Copilot, Finding) should use this
to produce their ConfidenceCard instead of building one inline.

Scoring model:
    base = data_completeness × 0.5
         + source_score      × 0.3   (capped at 1.0 with ≥3 independent sources)
         + recency_score     × 0.2   (full score if ≤30 days old)

    penalty = contradiction_penalty (0–0.3 deducted)
    final   = max(0, base - penalty)

Thresholds:
    final >= 0.75 → HIGH
    final >= 0.45 → MEDIUM
    final <  0.45 → LOW

No LLM. No side effects. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.enums import ConfidenceLevel
from domain.value_objects import ConfidenceCard

# Source recency threshold in days — older sources reduce recency_score linearly
_RECENCY_FULL_DAYS = 30
_RECENCY_ZERO_DAYS = 365

_HIGH_THRESHOLD = 0.75
_MEDIUM_THRESHOLD = 0.45


@dataclass(frozen=True)
class ConfidenceInputs:
    """Evidence quality inputs for ConfidenceCalculator.calculate().

    Attributes:
        source_count:          Total number of independent evidence sources.
        data_completeness:     Fraction of expected data fields present (0.0–1.0).
        source_recency_days:   Average age of sources in days (0 = today).
        cross_validation_score: Agreement between independent sources (0.0–1.0).
                               Use 1.0 if only one source (no cross-validation).
        contradiction_penalty: Manual penalty for known contradictions (0.0–0.3).
        missing_information:   Explicit gaps — shown as warnings in the UI.
    """

    source_count: int = 0
    data_completeness: float = 0.0
    source_recency_days: int = 0
    cross_validation_score: float = 1.0
    contradiction_penalty: float = 0.0
    missing_information: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.data_completeness <= 1.0:
            raise ValueError(f"data_completeness must be 0–1, got {self.data_completeness}")
        if not 0.0 <= self.cross_validation_score <= 1.0:
            raise ValueError(f"cross_validation_score must be 0–1, got {self.cross_validation_score}")
        if not 0.0 <= self.contradiction_penalty <= 0.3:
            raise ValueError(f"contradiction_penalty must be 0–0.3, got {self.contradiction_penalty}")
        if self.source_recency_days < 0:
            raise ValueError(f"source_recency_days must be >= 0, got {self.source_recency_days}")


def _source_score(count: int, cross_validation: float) -> float:
    """0–1 score: grows with independent sources, scaled by cross-validation."""
    if count == 0:
        return 0.0
    raw = min(1.0, count / 3.0)   # saturates at 3 sources
    return round(raw * cross_validation, 4)


def _recency_score(days: int) -> float:
    """1.0 for fresh data (≤30 days), 0.0 for very old (≥365 days), linear between."""
    if days <= _RECENCY_FULL_DAYS:
        return 1.0
    if days >= _RECENCY_ZERO_DAYS:
        return 0.0
    span = _RECENCY_ZERO_DAYS - _RECENCY_FULL_DAYS
    return round(1.0 - (days - _RECENCY_FULL_DAYS) / span, 4)


def _derive_level(score: float) -> ConfidenceLevel:
    if score >= _HIGH_THRESHOLD:
        return ConfidenceLevel.HIGH
    if score >= _MEDIUM_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _build_basis(inputs: ConfidenceInputs, score: float, level: ConfidenceLevel) -> str:
    parts = [f"{inputs.source_count} source(s)"]
    if inputs.data_completeness < 1.0:
        parts.append(f"{round(inputs.data_completeness * 100)}% data completeness")
    if inputs.source_recency_days > _RECENCY_FULL_DAYS:
        parts.append(f"avg source age {inputs.source_recency_days}d")
    if inputs.contradiction_penalty > 0:
        parts.append("contradictions detected")
    return f"{level.value} confidence ({round(score, 2)}): {', '.join(parts)}"


_LEVEL_TO_SCORE: dict[ConfidenceLevel, float] = {
    ConfidenceLevel.HIGH: 0.85,
    ConfidenceLevel.MEDIUM: 0.60,
    ConfidenceLevel.LOW: 0.30,
}


def build_confidence_card_from_level(level: ConfidenceLevel) -> ConfidenceCard:
    """Build a minimal ConfidenceCard from a ConfidenceLevel enum (backwards-compat helper).

    Used when full evidence quality inputs are not available — e.g. when reading
    a Finding or Risk from DB that was created before E4-F1.
    """
    score = _LEVEL_TO_SCORE.get(level, 0.60)
    return ConfidenceCard(
        level=level,
        score=score,
        basis=f"Confidence assessed as {level.value}",
        limitations=(),
    )


class ConfidenceCalculator:
    """Compute a standardised ConfidenceCard from evidence quality inputs (ADR-015).

    Stateless — instantiate once and reuse.

    Example:
        calc = ConfidenceCalculator()
        card = calc.calculate(ConfidenceInputs(
            source_count=3,
            data_completeness=0.9,
            source_recency_days=15,
        ))
        # ConfidenceCard(level=HIGH, score=0.78, ...)
    """

    def calculate(self, inputs: ConfidenceInputs) -> ConfidenceCard:
        """Return a ConfidenceCard for the given evidence quality inputs."""
        base = (
            inputs.data_completeness * 0.5
            + _source_score(inputs.source_count, inputs.cross_validation_score) * 0.3
            + _recency_score(inputs.source_recency_days) * 0.2
        )
        final = round(max(0.0, base - inputs.contradiction_penalty), 4)
        level = _derive_level(final)
        return ConfidenceCard(
            level=level,
            score=final,
            basis=_build_basis(inputs, final, level),
            limitations=inputs.missing_information,
        )
