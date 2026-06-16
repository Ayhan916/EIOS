"""
Decision Brief Generator

Produces a structured, human-readable decision brief from assessment data.

Design principles:
  - Pure: no I/O, no LLM
  - Factual and descriptive — avoids legal conclusions
  - Every claim is traceable to an input field
  - Mandatory disclaimer separates decision support from legal advice
"""

from __future__ import annotations

from dataclasses import dataclass

from application.compliance.gaps import ComplianceGap
from application.compliance.verdict import ComplianceVerdict
from domain.assessment import Assessment

_DISCLAIMER = (
    "This brief provides decision support information only and does not constitute "
    "legal advice. It should not be relied upon as a definitive assessment of legal "
    "compliance obligations. Regulatory compliance should be assessed with qualified "
    "legal counsel familiar with the applicable jurisdictions and sector context."
)


@dataclass
class DecisionBrief:
    assessment_id: str
    assessment_title: str
    assessment_status: str
    compliance_verdict: str
    mandatory_coverage_pct: int
    quality_score: float | None
    finding_count: int
    risk_count: int
    recommendation_count: int
    critical_gap_count: int
    immediate_action_count: int
    executive_summary: str
    key_findings: list[str]
    top_critical_gaps: list[str]
    top_recommendations: list[str]
    disclaimer: str


def compute_brief(
    assessment: Assessment,
    verdict: ComplianceVerdict,
    top_critical_gaps: list[ComplianceGap],
    finding_titles: list[str],
    recommendation_titles: list[str],
    immediate_action_count: int,
) -> DecisionBrief:
    """
    Generate a DecisionBrief from structured inputs.

    Args:
        assessment: The Assessment domain object.
        verdict: Computed ComplianceVerdict from compute_verdict().
        top_critical_gaps: The highest-exposure uncovered mandatory gaps (up to 3).
        finding_titles: Titles of findings linked to this assessment (up to 3 shown).
        recommendation_titles: Titles of recommendations (up to 3 shown).
        immediate_action_count: Number of immediate-timeline remediation actions.
    """
    pct = round(verdict.mandatory_coverage_ratio * 100)

    summary = _build_summary(
        verdict.status,
        pct,
        verdict.critical_gap_count,
        len(finding_titles),
        immediate_action_count,
    )

    return DecisionBrief(
        assessment_id=assessment.id,
        assessment_title=assessment.title,
        assessment_status=assessment.status.value,
        compliance_verdict=verdict.status,
        mandatory_coverage_pct=pct,
        quality_score=assessment.quality_score,
        finding_count=len(finding_titles),
        risk_count=verdict.total_mandatory_articles - verdict.covered_mandatory_count,
        recommendation_count=len(recommendation_titles),
        critical_gap_count=verdict.critical_gap_count,
        immediate_action_count=immediate_action_count,
        executive_summary=summary,
        key_findings=finding_titles[:3],
        top_critical_gaps=[g.title for g in top_critical_gaps[:3]],
        top_recommendations=recommendation_titles[:3],
        disclaimer=_DISCLAIMER,
    )


def _build_summary(
    status: str,
    pct: int,
    critical_gap_count: int,
    finding_count: int,
    immediate_action_count: int,
) -> str:
    if status == "compliant":
        return (
            f"The assessment demonstrates substantive regulatory coverage ({pct}% of mandatory "
            f"obligations addressed) with no critical compliance gaps identified. "
            f"{finding_count} finding{'s were' if finding_count != 1 else ' was'} recorded."
        )
    if status == "non_compliant":
        return (
            f"The assessment identifies significant regulatory gaps: only {pct}% of mandatory "
            f"obligations are addressed. {critical_gap_count} critical gap"
            f"{'s require' if critical_gap_count != 1 else ' requires'} immediate attention, "
            f"with {immediate_action_count} action"
            f"{'s' if immediate_action_count != 1 else ''} classified as immediate priority."
        )
    return (
        f"The assessment demonstrates partial regulatory coverage ({pct}% of mandatory obligations "
        f"addressed). {critical_gap_count} critical gap"
        f"{'s were' if critical_gap_count != 1 else ' was'} identified. "
        f"{immediate_action_count} remediation action"
        f"{'s are' if immediate_action_count != 1 else ' is'} classified as immediate priority."
    )
