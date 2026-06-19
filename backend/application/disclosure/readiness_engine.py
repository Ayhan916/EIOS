"""M32 Disclosure Readiness Engine.

Determines whether a disclosure is ready for review, approval, or publication.
Every decision is accompanied by a human-readable rationale string.

State machine:
  Not Started → Draft → Ready for Review → Ready for Approval → Ready for Publication

Thresholds (configurable constants — no hidden weights):
  REVIEW_COVERAGE_THRESHOLD    = 0.25   (25% evidence coverage to submit for review)
  APPROVAL_COVERAGE_THRESHOLD  = 0.50   (50% evidence coverage at approval decision)
  PUBLISH_COVERAGE_THRESHOLD   = 0.75   (75% evidence coverage before publication)
"""

from __future__ import annotations

REVIEW_COVERAGE_THRESHOLD = 0.25
APPROVAL_COVERAGE_THRESHOLD = 0.50
PUBLISH_COVERAGE_THRESHOLD = 0.75


def determine_readiness(
    *,
    disclosure_status: str,
    narrative_text: str,
    evidence_coverage: float,
    critical_gap_count: int = 0,
) -> tuple[str, str]:
    """Return ``(readiness_status, rationale)`` given current disclosure state."""

    # Not Started: no draft text yet
    if disclosure_status == "Not Started" or not narrative_text.strip():
        return (
            "Not Started",
            "No draft narrative has been prepared. Start drafting to begin the disclosure workflow.",
        )

    # Draft: text exists but hasn't been submitted for review
    if disclosure_status == "Draft":
        pct = f"{evidence_coverage:.0%}"
        if evidence_coverage >= REVIEW_COVERAGE_THRESHOLD:
            return (
                "Ready for Review",
                f"Draft narrative complete; evidence coverage {pct} meets the {REVIEW_COVERAGE_THRESHOLD:.0%} threshold for review submission.",
            )
        return (
            "Draft",
            f"Evidence coverage {pct} is below the {REVIEW_COVERAGE_THRESHOLD:.0%} threshold required to submit for review. Attach more evidence.",
        )

    # In Review: a reviewer is evaluating
    if disclosure_status == "In Review":
        pct = f"{evidence_coverage:.0%}"
        if evidence_coverage >= APPROVAL_COVERAGE_THRESHOLD:
            return (
                "Ready for Approval",
                f"Disclosure is under review; coverage {pct} meets the {APPROVAL_COVERAGE_THRESHOLD:.0%} threshold for an approval decision.",
            )
        return (
            "Blocked",
            f"Evidence coverage {pct} is below the {APPROVAL_COVERAGE_THRESHOLD:.0%} threshold. Approval cannot proceed; return to Draft and add evidence.",
        )

    # Approved: awaiting publication decision
    if disclosure_status == "Approved":
        if critical_gap_count > 0:
            return (
                "Blocked",
                f"Publication blocked: {critical_gap_count} critical compliance gap(s) remain open. Resolve all critical gaps before publishing.",
            )
        pct = f"{evidence_coverage:.0%}"
        if evidence_coverage >= PUBLISH_COVERAGE_THRESHOLD:
            return (
                "Ready for Publication",
                f"Approved; evidence coverage {pct} meets the {PUBLISH_COVERAGE_THRESHOLD:.0%} publication threshold; no critical compliance gaps.",
            )
        return (
            "Blocked",
            f"Evidence coverage {pct} is below the {PUBLISH_COVERAGE_THRESHOLD:.0%} publication threshold. Strengthen evidence before publishing.",
        )

    # Published
    if disclosure_status == "Published":
        return (
            "Ready for Publication",
            "This disclosure has already been published.",
        )

    return ("Blocked", f"Disclosure is in an unrecognised state: '{disclosure_status}'.")
