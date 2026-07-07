"""
M29 Executive Summary Generator

Deterministic, rule-based narrative generation.
No LLM calls.  Same inputs → same output, always.

Each sentence is generated from explicit threshold rules so any auditor
can trace exactly which data points produced which clause.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutiveSummaryInputs:
    total_suppliers: int = 0
    scored_suppliers: int = 0
    critical_risk_count: int = 0
    high_risk_count: int = 0
    moderate_risk_count: int = 0
    low_risk_count: int = 0
    improving_count: int = 0
    deteriorating_count: int = 0
    stable_count: int = 0
    avg_esg_score: float | None = None
    avg_risk_score: float | None = None
    open_actions: int = 0
    overdue_actions: int = 0
    resolved_actions: int = 0
    assessments_awaiting_review: int = 0
    assessments_approved: int = 0
    critical_findings_total: int = 0
    top_risk_country: str | None = None
    top_risk_sector: str | None = None
    period_label: str = "this period"


def generate_executive_summary(inputs: ExecutiveSummaryInputs) -> str:
    """
    Generate a deterministic narrative executive summary.

    Returns a single paragraph of 4–8 sentences, each grounded in the
    supplied metrics.  No randomness; suitable for regulatory audit.
    """
    parts: list[str] = []

    # 1. Portfolio overview
    if inputs.scored_suppliers == inputs.total_suppliers and inputs.total_suppliers > 0:
        parts.append(
            f"The supplier portfolio comprises {inputs.total_suppliers} active"
            f" supplier{'s' if inputs.total_suppliers != 1 else ''}, all of which"
            " have been assessed and scored."
        )
    elif inputs.scored_suppliers > 0:
        unscored = inputs.total_suppliers - inputs.scored_suppliers
        parts.append(
            f"The supplier portfolio comprises {inputs.total_suppliers} active"
            f" supplier{'s' if inputs.total_suppliers != 1 else ''};"
            f" {inputs.scored_suppliers} have been assessed and scored,"
            f" with {unscored} awaiting initial assessment."
        )
    else:
        parts.append(
            f"The supplier portfolio comprises {inputs.total_suppliers} active"
            f" supplier{'s' if inputs.total_suppliers != 1 else ''}."
            " No suppliers have been scored yet."
        )

    # 2. ESG performance
    if inputs.avg_esg_score is not None:
        if inputs.avg_esg_score >= 85:
            quality = "strong"
        elif inputs.avg_esg_score >= 70:
            quality = "adequate"
        elif inputs.avg_esg_score >= 55:
            quality = "below expectations"
        else:
            quality = "poor"
        parts.append(
            f"The portfolio average ESG score is {inputs.avg_esg_score:.1f}/100,"
            f" indicating {quality} ESG performance {inputs.period_label}."
        )

    # 3. Risk concentration
    high_and_critical = inputs.high_risk_count + inputs.critical_risk_count
    if high_and_critical == 0:
        parts.append("No suppliers are currently classified as High or Critical risk.")
    else:
        pct = round((high_and_critical / max(inputs.scored_suppliers, 1)) * 100)
        crit_clause = (
            f", including {inputs.critical_risk_count}"
            f" Critical{'s' if inputs.critical_risk_count != 1 else ''}"
            if inputs.critical_risk_count > 0
            else ""
        )
        parts.append(
            f"{high_and_critical} supplier{'s' if high_and_critical != 1 else ''}"
            f" ({pct}% of scored suppliers) are classified as High or"
            f" Critical risk{crit_clause}."
        )

    # 4. Trend direction
    if inputs.deteriorating_count > inputs.improving_count and inputs.deteriorating_count > 0:
        parts.append(
            f"Risk exposure is increasing: {inputs.deteriorating_count}"
            f" supplier{'s are' if inputs.deteriorating_count != 1 else ' is'}"
            f" deteriorating, compared to {inputs.improving_count} improving."
        )
    elif inputs.improving_count > inputs.deteriorating_count and inputs.improving_count > 0:
        parts.append(
            f"Portfolio risk is improving:"
            f" {inputs.improving_count}"
            f" supplier{'s are' if inputs.improving_count != 1 else ' is'}"
            " showing improvement,"
            f" compared to {inputs.deteriorating_count} deteriorating."
        )
    elif inputs.scored_suppliers > 0:
        parts.append("Portfolio risk levels are broadly stable.")

    # 5. Top geographic / sector concentration (if available)
    if inputs.top_risk_country and inputs.top_risk_sector:
        parts.append(
            f"The highest concentration of risk is in {inputs.top_risk_country}"
            f" within the {inputs.top_risk_sector} sector."
        )
    elif inputs.top_risk_country:
        parts.append(f"The highest geographic risk concentration is in {inputs.top_risk_country}.")

    # 6. Action health
    if inputs.overdue_actions > 0:
        parts.append(
            f"{inputs.overdue_actions}"
            f" action{'s are' if inputs.overdue_actions != 1 else ' is'}"
            " overdue and require immediate management attention,"
            f" out of {inputs.open_actions} total open"
            f" action{'s' if inputs.open_actions != 1 else ''}."
        )
    elif inputs.open_actions > 0:
        parts.append(
            f"{inputs.open_actions}"
            f" action{'s are' if inputs.open_actions != 1 else ' is'}"
            " open with no items overdue."
        )
    else:
        parts.append("All recommended actions have been resolved.")

    # 7. Governance status
    if inputs.assessments_awaiting_review > 0:
        parts.append(
            f"{inputs.assessments_awaiting_review}"
            f" assessment{'s are' if inputs.assessments_awaiting_review != 1 else ' is'}"
            " awaiting governance review approval."
        )

    # 8. Priority call to action
    if inputs.critical_risk_count > 0:
        parts.append(
            f"Management should prioritise immediate remediation of the"
            f" {inputs.critical_risk_count} Critical risk"
            f" supplier{'s' if inputs.critical_risk_count != 1 else ''}."
        )
    elif inputs.overdue_actions > 0:
        parts.append("Management should prioritise closure of overdue remediation actions.")
    elif inputs.deteriorating_count > 0:
        parts.append(
            "Management should monitor deteriorating suppliers and initiate targeted reassessments."
        )
    elif inputs.high_risk_count > 0:
        parts.append(
            "Management should schedule targeted assessments for"
            f" the {inputs.high_risk_count} High risk"
            f" supplier{'s' if inputs.high_risk_count != 1 else ''}."
        )

    return " ".join(parts)
