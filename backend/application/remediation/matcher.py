"""
Gap-Recommendation Matcher

Deterministically links compliance gaps to existing recommendations
via keyword overlap. No LLM, no embeddings — fully transparent and auditable.

Match logic:
  For each gap, build a match vocabulary from:
    - The framework article's keywords
    - Significant tokens from the gap's remediation_hint
  For each recommendation, score overlap against this vocabulary.
  Matches above a minimum overlap threshold are recorded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from application.compliance.frameworks import get_article
from application.compliance.gaps import ComplianceGap
from domain.recommendation import Recommendation

_MIN_TOKEN_LENGTH = 4
_MIN_OVERLAP_SCORE = 1


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens, filtering short words and stop words."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    stop = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "been",
        "will",
        "shall",
        "must",
        "should",
        "which",
        "their",
        "where",
        "when",
        "each",
        "into",
        "also",
        "such",
        "more",
        "than",
        "they",
        "them",
        "these",
        "those",
        "other",
        "some",
        "over",
        "under",
        "both",
        "only",
        "upon",
        "used",
        "need",
        "make",
        "take",
        "give",
        "does",
        "done",
        "relevant",
        "required",
        "applicable",
    }
    return {w for w in words if len(w) >= _MIN_TOKEN_LENGTH and w not in stop}


@dataclass
class GapRecommendationLink:
    gap_code: str
    gap_title: str
    recommendation_id: str
    recommendation_title: str
    match_score: int  # count of overlapping terms
    match_confidence: float  # normalised 0.0-1.0


def compute_matches(
    gaps: list[ComplianceGap],
    recommendations: list[Recommendation],
) -> list[GapRecommendationLink]:
    """
    Return all gap-recommendation links where keyword overlap >= threshold.
    A gap may match multiple recommendations; a recommendation may match multiple gaps.
    """
    if not gaps or not recommendations:
        return []

    # Build recommendation token sets once
    rec_tokens: list[tuple[Recommendation, set[str]]] = []
    for rec in recommendations:
        text = f"{rec.title} {rec.description} {rec.reasoning or ''}"
        rec_tokens.append((rec, _tokenize(text)))

    links: list[GapRecommendationLink] = []

    for gap in gaps:
        # Build gap vocabulary: article keywords + remediation hint tokens
        article = get_article(gap.article_code)
        keyword_tokens: set[str] = set()
        if article:
            for kw in article.keywords:
                keyword_tokens.update(_tokenize(kw))
        keyword_tokens.update(_tokenize(gap.remediation_hint))
        keyword_tokens.update(_tokenize(gap.title))

        for rec, rtokens in rec_tokens:
            overlap = len(keyword_tokens & rtokens)
            if overlap >= _MIN_OVERLAP_SCORE:
                confidence = round(min(1.0, overlap / 6), 4)
                links.append(
                    GapRecommendationLink(
                        gap_code=gap.article_code,
                        gap_title=gap.title,
                        recommendation_id=rec.id,
                        recommendation_title=rec.title,
                        match_score=overlap,
                        match_confidence=confidence,
                    )
                )

    # Sort: highest confidence first
    links.sort(key=lambda lk: lk.match_confidence, reverse=True)
    return links
