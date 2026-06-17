"""
Compliance Verdict Engine

Synthesises coverage data and gap analysis into a structured compliance verdict
with a human-readable explanation. All logic is deterministic and auditable.

Verdict thresholds:
  compliant      — mandatory_coverage >= 0.75 AND no critical gaps
  partial        — mandatory_coverage >= 0.40 OR (< 0.75 with no critical gaps)
  non_compliant  — mandatory_coverage < 0.40 OR critical gaps present with coverage < 0.50
"""

from __future__ import annotations

from dataclasses import dataclass

from .coverage import ComplianceCoverageReport
from .gaps import ComplianceGap


@dataclass
class ComplianceVerdict:
    status: str  # "compliant" | "partial" | "non_compliant"
    mandatory_coverage_ratio: float
    total_mandatory_articles: int
    covered_mandatory_count: int
    mandatory_gap_count: int
    critical_gap_count: int
    high_gap_count: int
    weighted_gap_score: float  # sum of exposures of uncovered mandatory articles, normalized 0-1
    explanation: str
    top_gap_codes: list[str]  # top 3 gap article codes by exposure


def compute_verdict(
    coverage_report: ComplianceCoverageReport,
    gaps: list[ComplianceGap],
) -> ComplianceVerdict:
    """Derive a structured compliance verdict from coverage and gap data."""
    mandatory_gaps = [g for g in gaps if g.obligation_type == "mandatory"]
    critical_gaps = [g for g in mandatory_gaps if g.gap_severity == "critical"]
    high_gaps = [g for g in mandatory_gaps if g.gap_severity == "high"]

    ratio = coverage_report.mandatory_coverage_ratio
    gap_count = len(mandatory_gaps)
    crit_count = len(critical_gaps)

    # Total mandatory articles (covered + uncovered)
    total_mandatory = sum(
        fc.total_articles
        for fc in coverage_report.framework_coverage
        if any(ac.obligation_type == "mandatory" for ac in fc.articles)
    )
    mandatory_articles_all = [
        ac
        for fc in coverage_report.framework_coverage
        for ac in fc.articles
        if ac.obligation_type == "mandatory"
    ]
    total_mandatory = len(mandatory_articles_all)
    covered_mandatory = sum(1 for ac in mandatory_articles_all if ac.covered)

    # Weighted gap score: normalised sum of regulatory_exposure for uncovered mandatory articles
    max_possible_gap = sum(g.regulatory_exposure for g in mandatory_gaps) if mandatory_gaps else 0.0
    total_possible = sum(
        ac_exp
        for fc in coverage_report.framework_coverage
        for ac in fc.articles
        if ac.obligation_type == "mandatory"
        for ac_exp in [_get_exposure_for_code(ac.code)]
    )
    weighted_gap = max_possible_gap / total_possible if total_possible > 0 else 0.0

    # Determine status
    if ratio >= 0.75 and crit_count == 0:
        status = "compliant"
    elif ratio < 0.40 or (crit_count > 0 and ratio < 0.50):
        status = "non_compliant"
    else:
        status = "partial"

    explanation = _build_explanation(
        status,
        ratio,
        covered_mandatory,
        total_mandatory,
        crit_count,
        len(high_gaps),
        critical_gaps[:3],
    )

    top_gap_codes = [g.article_code for g in mandatory_gaps[:3]]

    return ComplianceVerdict(
        status=status,
        mandatory_coverage_ratio=ratio,
        total_mandatory_articles=total_mandatory,
        covered_mandatory_count=covered_mandatory,
        mandatory_gap_count=gap_count,
        critical_gap_count=crit_count,
        high_gap_count=len(high_gaps),
        weighted_gap_score=round(weighted_gap, 4),
        explanation=explanation,
        top_gap_codes=top_gap_codes,
    )


def _get_exposure_for_code(code: str) -> float:
    from .weights import exposure

    return exposure(code)


def _build_explanation(
    status: str,
    ratio: float,
    covered: int,
    total: int,
    crit_count: int,
    high_count: int,
    top_critical: list[ComplianceGap],
) -> str:
    pct = round(ratio * 100)

    if status == "compliant":
        return (
            f"Compliant: {covered} of {total} mandatory obligations addressed ({pct}%). "
            "No critical regulatory gaps identified."
        )

    gap_names = "; ".join(f"{g.article} ({g.title})" for g in top_critical[:2])

    if status == "non_compliant":
        detail = f" Critical gaps: {gap_names}." if gap_names else ""
        return (
            f"Non-compliant: only {covered} of {total} mandatory obligations addressed ({pct}%). "
            f"{crit_count} critical gap{'s' if crit_count != 1 else ''} require immediate action.{detail}"
        )

    detail = f" Priority gaps: {gap_names}." if gap_names else ""
    return (
        f"Partial compliance: {covered} of {total} mandatory obligations addressed ({pct}%). "
        f"{crit_count} critical and {high_count} high-severity gap{'s' if (crit_count + high_count) != 1 else ''} remain.{detail}"
    )
