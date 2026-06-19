"""Executive Brief Engine — pure function, no I/O.

Structures platform data into a brief prompt payload for the LLM.
No LLM calls here — this prepares the structured input.
"""

from __future__ import annotations

_PRIORITY_LEVELS = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


def build_executive_brief_payload(
    *,
    risk_distribution: dict,
    critical_findings: list[dict],
    open_recommendations: int,
    compliance_gaps: list[dict],
    weak_disclosures: list[dict],
    overdue_actions: list[dict],
    critical_suppliers: list[dict],
) -> dict:
    """Build a structured payload for executive brief LLM prompt.

    Returns a dict that the copilot service passes to the LLM.
    Evidence-backed only — all fields come from retrieved platform data.
    """
    total_suppliers = sum(risk_distribution.values()) if risk_distribution else 0
    critical_supplier_count = risk_distribution.get("Critical", 0)
    high_supplier_count = risk_distribution.get("High", 0)

    key_risks = [
        {
            "finding_id": f.get("id", ""),
            "title": f.get("title", ""),
            "severity": f.get("severity", ""),
            "category": f.get("category", ""),
        }
        for f in critical_findings[:5]
    ]

    key_gaps = sorted(
        compliance_gaps,
        key=lambda g: _PRIORITY_LEVELS.get(g.get("severity", "Low"), 0),
        reverse=True,
    )[:5]

    reporting_blockers = [d for d in weak_disclosures if d.get("is_weak")][:5]

    top_overdue = sorted(
        overdue_actions,
        key=lambda a: _PRIORITY_LEVELS.get(a.get("priority", "Low"), 0),
        reverse=True,
    )[:5]

    return {
        "supplier_overview": {
            "total": total_suppliers,
            "critical": critical_supplier_count,
            "high": high_supplier_count,
            "critical_supplier_names": [s.get("supplier_name", "") for s in critical_suppliers[:5]],
        },
        "key_risks": key_risks,
        "compliance_concerns": [
            {
                "gap_id": g.get("gap_id", ""),
                "severity": g.get("severity", ""),
                "regulation": g.get("regulation_name", ""),
                "requirement": g.get("requirement_title", ""),
            }
            for g in key_gaps
        ],
        "reporting_blockers": [
            {
                "response_id": d.get("response_id", ""),
                "requirement": d.get("requirement_title", ""),
                "status": d.get("disclosure_status", ""),
            }
            for d in reporting_blockers
        ],
        "recommended_actions": [
            {
                "id": a.get("id", ""),
                "title": a.get("title", ""),
                "priority": a.get("priority", ""),
                "days_overdue": a.get("days_overdue", 0),
            }
            for a in top_overdue
        ],
        "open_recommendations_total": open_recommendations,
    }
