"""Copilot intent detection — keyword-based, pure function, no I/O."""

from __future__ import annotations

from domain.enums import CopilotIntentType

_RISK_KEYWORDS = frozenset(
    {
        "risk",
        "risks",
        "supplier risk",
        "deteriorat",
        "critical",
        "vulnerable",
        "worst",
        "danger",
        "threat",
        "exposure",
        "score",
        "band",
    }
)

_COMPLIANCE_KEYWORDS = frozenset(
    {
        "complian",
        "non-compliant",
        "gap",
        "gaps",
        "require",
        "regulation",
        "csrd",
        "esrs",
        "issb",
        "gri",
        "tcfd",
        "uncovered",
        "missing evidence",
        "evidence",
        "standard",
    }
)

_DISCLOSURE_KEYWORDS = frozenset(
    {
        "disclosur",
        "publish",
        "publication",
        "ready",
        "weak",
        "strong",
        "framework",
        "report package",
        "reporting package",
        "esrs",
        "datapoint",
    }
)

_DUE_DILIGENCE_KEYWORDS = frozenset(
    {
        "due diligence",
        "lksgg",
        "lksg",
        "csddd",
        "supply chain",
        "supplier exposure",
        "human rights",
        "environmental",
        "remediation",
        "overdue action",
        "preventive",
        "german act",
    }
)

_EXECUTIVE_KEYWORDS = frozenset(
    {
        "board",
        "executive",
        "brief",
        "change",
        "changed",
        "month",
        "quarter",
        "focus",
        "summary",
        "overview",
        "headline",
        "key",
        "this week",
        "since last",
        "what happened",
    }
)

_ACTION_KEYWORDS = frozenset(
    {
        "action",
        "should",
        "next step",
        "priorit",
        "recommend",
        "what to do",
        "fastest",
        "quickest",
        "reduce",
        "improve",
        "fix",
        "resolve",
        "remediat",
        "address",
        "tackle",
    }
)


def detect_intent(question: str) -> CopilotIntentType:
    """Classify a question into a copilot intent using keyword matching.

    Returns CopilotIntentType. Falls back to GENERAL when ambiguous.
    """
    q = question.lower()

    scores: dict[CopilotIntentType, int] = {
        CopilotIntentType.DUE_DILIGENCE: 0,
        CopilotIntentType.RISK: 0,
        CopilotIntentType.COMPLIANCE: 0,
        CopilotIntentType.DISCLOSURE: 0,
        CopilotIntentType.EXECUTIVE: 0,
        CopilotIntentType.ACTION: 0,
    }

    for kw in _DUE_DILIGENCE_KEYWORDS:
        if kw in q:
            scores[CopilotIntentType.DUE_DILIGENCE] += 2  # high weight — specific
    for kw in _RISK_KEYWORDS:
        if kw in q:
            scores[CopilotIntentType.RISK] += 1
    for kw in _COMPLIANCE_KEYWORDS:
        if kw in q:
            scores[CopilotIntentType.COMPLIANCE] += 1
    for kw in _DISCLOSURE_KEYWORDS:
        if kw in q:
            scores[CopilotIntentType.DISCLOSURE] += 1
    for kw in _EXECUTIVE_KEYWORDS:
        if kw in q:
            scores[CopilotIntentType.EXECUTIVE] += 1
    for kw in _ACTION_KEYWORDS:
        if kw in q:
            scores[CopilotIntentType.ACTION] += 1

    best_score = max(scores.values())
    if best_score == 0:
        return CopilotIntentType.GENERAL

    # Return highest-scoring intent; ties resolved by priority order
    priority = [
        CopilotIntentType.DUE_DILIGENCE,
        CopilotIntentType.COMPLIANCE,
        CopilotIntentType.RISK,
        CopilotIntentType.ACTION,
        CopilotIntentType.DISCLOSURE,
        CopilotIntentType.EXECUTIVE,
    ]
    for intent in priority:
        if scores[intent] == best_score:
            return intent

    return CopilotIntentType.GENERAL
