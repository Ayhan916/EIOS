"""Evidence-based Confidence Calculator — M33.2.

Computes a structured confidence level for every Copilot answer based on
retrieval coverage, citation count, source diversity, data freshness, and
contradiction presence. Never exposes raw model confidence.
Pure function — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums import CopilotConfidenceLevel

from .contradiction_detector import ContradictionRecord
from .freshness_tracker import FreshnessReport
from .retrieval.base import RetrievalResult

# Maximum score
_MAX_SCORE = 100.0

# Factor weights
_RETRIEVAL_COVERAGE_WEIGHT = 40.0
_CITATION_WEIGHT = 20.0
_DIVERSITY_WEIGHT = 15.0
_FRESHNESS_WEIGHT = 15.0
_DATA_PRESENCE_BONUS = 5.0
_CONTRADICTION_PENALTY = 5.0
_MAX_CONTRADICTION_PENALTY = 15.0

# Thresholds
_VERY_HIGH = 80.0
_HIGH = 60.0
_MODERATE = 40.0


@dataclass
class ConfidenceFactors:
    retrieval_coverage: float  # 0.0–1.0
    citation_count: int
    source_diversity: int  # unique citation types
    average_data_age_days: float
    contradiction_count: int
    raw_score: float
    level: str


def calculate_confidence(
    results: list[RetrievalResult],
    citations: list[dict],
    contradictions: list[ContradictionRecord],
    freshness: FreshnessReport,
) -> tuple[CopilotConfidenceLevel, dict]:
    """Return (level, factors_dict) for the given answer components.

    The score is evidence-based: it reflects the quality and completeness
    of the retrieved data, not the model's self-reported probability.
    """
    total_called = len(results)
    non_empty = sum(1 for r in results if r.data)
    retrieval_coverage = non_empty / total_called if total_called > 0 else 0.0

    citation_factor = min(len(citations) / 5.0, 1.0)

    unique_types = len({r.citation_type for r in results if r.data and r.citation_type})
    diversity_factor = min(unique_types / 4.0, 1.0)

    # Freshness: 0 age = 1.0, 90-day-old = 0.0
    avg_age = freshness.average_age_days
    freshness_factor = max(0.0, 1.0 - (avg_age / 90.0)) if avg_age > 0 else 1.0

    # Contradiction penalty (capped)
    penalty = min(len(contradictions) * _CONTRADICTION_PENALTY, _MAX_CONTRADICTION_PENALTY)

    # Data presence bonus
    data_bonus = _DATA_PRESENCE_BONUS if non_empty > 0 else 0.0

    raw_score = (
        retrieval_coverage * _RETRIEVAL_COVERAGE_WEIGHT
        + citation_factor * _CITATION_WEIGHT
        + diversity_factor * _DIVERSITY_WEIGHT
        + freshness_factor * _FRESHNESS_WEIGHT
        + data_bonus
        - penalty
    )
    raw_score = max(0.0, min(_MAX_SCORE, raw_score))

    if raw_score >= _VERY_HIGH:
        level = CopilotConfidenceLevel.VERY_HIGH
    elif raw_score >= _HIGH:
        level = CopilotConfidenceLevel.HIGH
    elif raw_score >= _MODERATE:
        level = CopilotConfidenceLevel.MODERATE
    else:
        level = CopilotConfidenceLevel.LOW

    factors = ConfidenceFactors(
        retrieval_coverage=round(retrieval_coverage, 3),
        citation_count=len(citations),
        source_diversity=unique_types,
        average_data_age_days=round(avg_age, 1),
        contradiction_count=len(contradictions),
        raw_score=round(raw_score, 1),
        level=level.value,
    )

    return level, {
        "retrieval_coverage": factors.retrieval_coverage,
        "citation_count": factors.citation_count,
        "source_diversity": factors.source_diversity,
        "average_data_age_days": factors.average_data_age_days,
        "contradiction_count": factors.contradiction_count,
        "raw_score": factors.raw_score,
        "level": factors.level,
    }
