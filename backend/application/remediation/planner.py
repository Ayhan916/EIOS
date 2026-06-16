"""
Remediation Plan Generator

Produces a structured, priority-ordered remediation plan from compliance gaps
and their linked recommendations. Gaps are bucketed by severity/timeline.

Design:
  - Pure: no I/O
  - Timeline buckets are deterministic from regulatory_exposure
  - Each action surfaces the gap explanation and concrete remediation steps
"""

from __future__ import annotations

from dataclasses import dataclass, field

from application.compliance.gaps import ComplianceGap
from application.remediation.matcher import GapRecommendationLink

_TIMELINE_IMMEDIATE = "immediate (< 30 days)"
_TIMELINE_SHORT = "short-term (30–90 days)"
_TIMELINE_MEDIUM = "medium-term (90–180 days)"


@dataclass
class RemediationAction:
    priority_rank: int
    article_code: str
    framework: str
    article: str
    gap_title: str
    gap_severity: str
    regulatory_exposure: float
    timeline_label: str
    explanation: str
    remediation_hint: str
    linked_recommendation_ids: list[str] = field(default_factory=list)
    linked_recommendation_titles: list[str] = field(default_factory=list)


@dataclass
class RemediationPlan:
    assessment_id: str
    total_gaps: int
    immediate_actions: list[RemediationAction]
    short_term_actions: list[RemediationAction]
    medium_term_actions: list[RemediationAction]
    linked_gap_count: int
    unlinked_gap_count: int


def _timeline_for(regulatory_exposure: float) -> str:
    if regulatory_exposure >= 0.90:
        return _TIMELINE_IMMEDIATE
    if regulatory_exposure >= 0.75:
        return _TIMELINE_SHORT
    return _TIMELINE_MEDIUM


def compute_remediation_plan(
    assessment_id: str,
    gaps: list[ComplianceGap],
    links: list[GapRecommendationLink],
) -> RemediationPlan:
    """
    Build a time-bucketed remediation plan from gaps and gap-recommendation links.

    Args:
        assessment_id: The assessment this plan belongs to.
        gaps: List of ComplianceGap objects from compute_gaps().
        links: List of GapRecommendationLink objects from compute_matches().
    """
    # Index links by gap code
    links_by_gap: dict[str, list[GapRecommendationLink]] = {}
    for link in links:
        links_by_gap.setdefault(link.gap_code, []).append(link)

    linked_gap_codes: set[str] = set(links_by_gap.keys())

    immediate: list[RemediationAction] = []
    short_term: list[RemediationAction] = []
    medium_term: list[RemediationAction] = []

    rank = 1
    for gap in gaps:
        gap_links = links_by_gap.get(gap.article_code, [])
        action = RemediationAction(
            priority_rank=rank,
            article_code=gap.article_code,
            framework=gap.framework,
            article=gap.article,
            gap_title=gap.title,
            gap_severity=gap.gap_severity,
            regulatory_exposure=gap.regulatory_exposure,
            timeline_label=_timeline_for(gap.regulatory_exposure),
            explanation=gap.explanation,
            remediation_hint=gap.remediation_hint,
            linked_recommendation_ids=[lk.recommendation_id for lk in gap_links],
            linked_recommendation_titles=[lk.recommendation_title for lk in gap_links],
        )
        timeline = action.timeline_label
        if timeline == _TIMELINE_IMMEDIATE:
            immediate.append(action)
        elif timeline == _TIMELINE_SHORT:
            short_term.append(action)
        else:
            medium_term.append(action)
        rank += 1

    return RemediationPlan(
        assessment_id=assessment_id,
        total_gaps=len(gaps),
        immediate_actions=immediate,
        short_term_actions=short_term,
        medium_term_actions=medium_term,
        linked_gap_count=len(linked_gap_codes & {g.article_code for g in gaps}),
        unlinked_gap_count=sum(1 for g in gaps if g.article_code not in linked_gap_codes),
    )
