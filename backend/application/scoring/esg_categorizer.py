"""
ESG Pillar Classifier

Maps finding/risk category strings to one of three ESG pillars.
Classification is keyword-based on the category field (and optionally title).
The Governance pillar is the default — everything that is not explicitly
Environmental or Social falls there.

Design note: keyword lists are intentionally broad to handle free-text
categories entered by analysts.  False positives (e.g. "health and safety"
classified as Social rather than Environmental) are acceptable at v1.0.
"""

from __future__ import annotations

ESG_PILLAR_ENVIRONMENTAL = "Environmental"
ESG_PILLAR_SOCIAL = "Social"
ESG_PILLAR_GOVERNANCE = "Governance"

_ENV_KEYWORDS = frozenset(
    {
        "environment",
        "environmental",
        "climate",
        "energy",
        "emission",
        "carbon",
        "greenhouse",
        "ghg",
        "waste",
        "water",
        "pollution",
        "biodiversity",
        "deforestation",
        "land use",
        "resource",
        "renewable",
        "ecological",
        "scope 1",
        "scope 2",
        "scope 3",
    }
)

_SOC_KEYWORDS = frozenset(
    {
        "social",
        "labor",
        "labour",
        "human rights",
        "human right",
        "health",
        "safety",
        "community",
        "diversity",
        "inclusion",
        "worker",
        "employee",
        "child",
        "forced",
        "discrimination",
        "wage",
        "salary",
        "supply chain",
        "modern slavery",
        "trafficking",
        "workplace",
        "occupational",
    }
)


def categorize_pillar(category: str, title: str = "") -> str:
    """Return 'Environmental', 'Social', or 'Governance' for a given category string."""
    text = (category + " " + title).lower()
    if any(kw in text for kw in _ENV_KEYWORDS):
        return ESG_PILLAR_ENVIRONMENTAL
    if any(kw in text for kw in _SOC_KEYWORDS):
        return ESG_PILLAR_SOCIAL
    return ESG_PILLAR_GOVERNANCE
