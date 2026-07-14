"""CSDDD Obligation domain value objects (ADR-010).

CsdddObligation — immutable representation of one CSDDD article obligation.
ObligationMatch  — immutable result of the rule engine for one finding.

No LLM is involved. Matching is deterministic keyword/category-based logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CsdddObligation:
    """A single CSDDD article obligation with its trigger conditions.

    Attributes:
        article_id:           Stable internal ID (e.g. "csddd-art-8").
        article_number:       Human-readable article reference (e.g. "Art. 8").
        obligation_text:      Short description of what the obligation requires.
        trigger_conditions:   Keywords matched against finding category and title.
                              All lowercase. A single match is sufficient.
        evidence_requirements: What evidence types are expected to fulfil this obligation.
        severity_threshold:   Minimum finding severity to trigger this obligation.
                              None = triggers for any severity.
    """

    article_id: str
    article_number: str
    obligation_text: str
    trigger_conditions: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    severity_threshold: str | None = None


@dataclass(frozen=True)
class ObligationMatch:
    """Result of the rule engine for a single finding × obligation pair.

    Attributes:
        article_id:         Matched obligation's stable ID.
        article_number:     Human-readable article reference.
        obligation_text:    Short description of the matched obligation.
        match_type:         "exact" — category matched; "partial" — title/description matched.
        confidence:         "High" for exact match, "Medium" for partial match.
        matched_conditions: The specific trigger conditions that fired.
    """

    article_id: str
    article_number: str
    obligation_text: str
    match_type: str
    confidence: str
    matched_conditions: tuple[str, ...]
