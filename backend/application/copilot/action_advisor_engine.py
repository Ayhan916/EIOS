"""Action Advisor Engine — pure function, no I/O.

Scores and ranks actions by impact, then structures them for the LLM prompt.
No LLM calls here — this prepares the structured recommendation payload.
"""

from __future__ import annotations

_SEVERITY_WEIGHT = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
_PRIORITY_WEIGHT = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


def _impact_score(finding: dict) -> int:
    return _SEVERITY_WEIGHT.get(finding.get("severity", "Low"), 1)


def _action_score(rec: dict) -> int:
    score = _PRIORITY_WEIGHT.get(rec.get("priority", "Low"), 1)
    if rec.get("overdue"):
        score += 2
    return score


def build_action_advisor_payload(
    *,
    findings: list[dict],
    risks: list[dict],
    compliance_gaps: list[dict],
    recommendations: list[dict],
) -> dict:
    """Build a structured payload for the Action Advisor LLM prompt.

    Scores and ranks findings, risks, gaps, and open recommendations
    to identify highest-impact actions and fastest remediations.
    """
    # Top findings by severity
    top_findings = sorted(findings, key=_impact_score, reverse=True)[:10]

    # Top gaps by severity
    top_gaps = sorted(
        compliance_gaps,
        key=lambda g: _SEVERITY_WEIGHT.get(g.get("severity", "Low"), 1),
        reverse=True,
    )[:10]

    # Open recommendations by combined priority + overdue score
    open_recs = [r for r in recommendations if r.get("action_status") in ("open", "in_progress")]
    scored_recs = sorted(open_recs, key=_action_score, reverse=True)

    highest_impact = scored_recs[:5]

    # Fastest remediation = recs with explicit due date soonest + open status
    fastest = sorted(
        [r for r in open_recs if r.get("due_date")],
        key=lambda r: r.get("due_date", "9999-99-99"),
    )[:5]

    # Risk reduction priorities = critical risks with open mitigations
    critical_risks = [r for r in risks if r.get("risk_level") in ("Critical", "High")][:5]

    return {
        "highest_impact_actions": [
            {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "priority": r.get("priority", ""),
                "overdue": r.get("overdue", False),
                "rationale": (
                    f"Priority {r.get('priority', '?')} action"
                    + (" — OVERDUE" if r.get("overdue") else "")
                ),
            }
            for r in highest_impact
        ],
        "fastest_remediations": [
            {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "due_date": r.get("due_date", ""),
                "priority": r.get("priority", ""),
            }
            for r in fastest
        ],
        "risk_reduction_priorities": [
            {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "risk_level": r.get("risk_level", ""),
                "category": r.get("category", ""),
            }
            for r in critical_risks
        ],
        "top_compliance_gaps": [
            {
                "gap_id": g.get("gap_id", ""),
                "severity": g.get("severity", ""),
                "regulation": g.get("regulation_name", ""),
                "requirement": g.get("requirement_title", ""),
                "remediation_steps": g.get("remediation_steps", ""),
            }
            for g in top_gaps
        ],
        "finding_hotspots": [
            {
                "id": f.get("id", ""),
                "title": f.get("title", ""),
                "severity": f.get("severity", ""),
                "category": f.get("category", ""),
            }
            for f in top_findings
        ],
        "open_action_count": len(open_recs),
    }
