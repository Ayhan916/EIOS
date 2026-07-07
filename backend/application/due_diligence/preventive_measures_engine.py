"""Preventive Measures Register Engine — M32.1.

Categorises controls into preventive measure types and assigns effectiveness status.
All functions are pure: no I/O, no side effects.
"""

from __future__ import annotations

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "policy": ["policy", "code of conduct", "standard", "procedure", "guideline"],
    "supplier_control": ["supplier", "vendor", "procurement", "due diligence", "onboarding"],
    "training": ["training", "awareness", "capacity building", "education", "workshop"],
    "monitoring": ["monitoring", "surveillance", "tracking", "kpi", "indicator"],
    "audit": ["audit", "inspection", "assessment", "verification", "certification review"],
    "certification": ["certification", "certificate", "iso", "sa8000", "rainforest", "fairtrade"],
}


def _classify_control(control: dict) -> str:
    title = (control.get("title") or "").lower()
    description = (control.get("description") or "").lower()
    text = title + " " + description
    for category, kws in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return category
    return "other"


def _assign_effectiveness(control: dict) -> str:
    effectiveness = control.get("effectiveness")
    (control.get("status") or "").lower()

    if effectiveness is None:
        return "Unknown"
    if effectiveness >= 0.75:
        return "Effective"
    if effectiveness >= 0.40:
        return "Partially Effective"
    return "Ineffective"


def build_preventive_measures_report(
    *,
    organization_id: str,
    controls: list[dict],
) -> dict:
    """Build Preventive Measures Register.

    Args:
        controls: list of {id, title, description, control_type, effectiveness, status}
            - control_type: "Preventive" | "Detective" | "Corrective"
            - effectiveness: float 0.0–1.0 or None
            - status: entity status string

    Returns:
        Serialisable snapshot dict.
    """
    preventive = [c for c in controls if c.get("control_type") == "Preventive"]
    detective = [c for c in controls if c.get("control_type") == "Detective"]
    corrective = [c for c in controls if c.get("control_type") == "Corrective"]

    # Categorise preventive controls
    by_category: dict[str, list[dict]] = {}
    for c in controls:
        cat = _classify_control(c)
        by_category.setdefault(cat, []).append(c)

    # Assign effectiveness to all controls
    eff_counts = {"Effective": 0, "Partially Effective": 0, "Ineffective": 0, "Unknown": 0}
    for c in controls:
        eff = _assign_effectiveness(c)
        eff_counts[eff] += 1

    # Build category summaries
    category_summaries = []
    for category, items in sorted(by_category.items()):
        eff_breakdown = {"Effective": 0, "Partially Effective": 0, "Ineffective": 0, "Unknown": 0}
        for c in items:
            eff = _assign_effectiveness(c)
            eff_breakdown[eff] += 1
        category_summaries.append(
            {
                "category": category,
                "display_name": category.replace("_", " ").title(),
                "total": len(items),
                "by_effectiveness": eff_breakdown,
                "items": [
                    {
                        "id": c.get("id", ""),
                        "title": c.get("title", ""),
                        "control_type": c.get("control_type", ""),
                        "effectiveness_score": c.get("effectiveness"),
                        "effectiveness_status": _assign_effectiveness(c),
                    }
                    for c in items
                ],
            }
        )

    return {
        "meta": {
            "organization_id": organization_id,
            "report_type": "preventive_measures",
        },
        "summary": {
            "total_controls": len(controls),
            "preventive": len(preventive),
            "detective": len(detective),
            "corrective": len(corrective),
            "by_effectiveness": eff_counts,
        },
        "by_category": category_summaries,
    }
