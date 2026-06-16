"""
EIOS Compliance Framework Library

Structured definitions of regulatory framework articles relevant to ESG
due diligence. Used for compliance coverage analysis and audit reporting.

Coverage:
  CSDDD  — EU Corporate Sustainability Due Diligence Directive (2024)
  LkSG   — German Supply Chain Due Diligence Act (2023)
  ESRS   — European Sustainability Reporting Standards (CSRD, 2024)
  GRI    — Global Reporting Initiative Standards (2021–2023)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FrameworkArticle:
    code: str
    framework: str
    article: str
    title: str
    obligation_type: str  # "mandatory" | "recommended"
    esg_categories: tuple[str, ...]
    keywords: tuple[str, ...]


# ---------------------------------------------------------------------------
# CSDDD — EU Corporate Sustainability Due Diligence Directive
# ---------------------------------------------------------------------------

CSDDD = [
    FrameworkArticle(
        code="CSDDD-Art-5",
        framework="CSDDD",
        article="Art. 5",
        title="Integrating due diligence into corporate policy",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("CSDDD Art. 5", "Art 5", "due diligence policy", "corporate policy"),
    ),
    FrameworkArticle(
        code="CSDDD-Art-6",
        framework="CSDDD",
        article="Art. 6",
        title="Identification of actual and potential adverse impacts",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("CSDDD Art. 6", "Art 6", "identification of adverse impacts", "adverse impact identification"),
    ),
    FrameworkArticle(
        code="CSDDD-Art-7",
        framework="CSDDD",
        article="Art. 7",
        title="Prevention and mitigation of potential adverse impacts",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("CSDDD Art. 7", "Art 7", "preventive measures", "mitigation", "prevention"),
    ),
    FrameworkArticle(
        code="CSDDD-Art-8",
        framework="CSDDD",
        article="Art. 8",
        title="Bringing actual adverse impacts to an end",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("CSDDD Art. 8", "Art 8", "remediation", "bringing to an end", "corrective action"),
    ),
    FrameworkArticle(
        code="CSDDD-Art-9",
        framework="CSDDD",
        article="Art. 9",
        title="Remediation of actual adverse impacts",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("CSDDD Art. 9", "Art 9", "remedy", "remediation"),
    ),
    FrameworkArticle(
        code="CSDDD-Art-10",
        framework="CSDDD",
        article="Art. 10",
        title="Grievance mechanisms and procedures",
        obligation_type="mandatory",
        esg_categories=("Governance", "Social"),
        keywords=("CSDDD Art. 10", "Art 10", "grievance mechanism", "complaint procedure", "grievance"),
    ),
    FrameworkArticle(
        code="CSDDD-Art-11",
        framework="CSDDD",
        article="Art. 11",
        title="Monitoring the effectiveness of due diligence",
        obligation_type="mandatory",
        esg_categories=("Governance",),
        keywords=("CSDDD Art. 11", "Art 11", "monitoring", "effectiveness"),
    ),
    FrameworkArticle(
        code="CSDDD-Art-12",
        framework="CSDDD",
        article="Art. 12",
        title="Communication and public reporting",
        obligation_type="mandatory",
        esg_categories=("Governance",),
        keywords=("CSDDD Art. 12", "Art 12", "reporting", "public communication", "transparency"),
    ),
    FrameworkArticle(
        code="CSDDD-Art-22",
        framework="CSDDD",
        article="Art. 22",
        title="Directors' duty of care for sustainability",
        obligation_type="mandatory",
        esg_categories=("Governance",),
        keywords=("CSDDD Art. 22", "Art 22", "directors", "duty of care", "board responsibility"),
    ),
]

# ---------------------------------------------------------------------------
# LkSG — Lieferkettensorgfaltspflichtengesetz (German Supply Chain Act)
# ---------------------------------------------------------------------------

LKSG = [
    FrameworkArticle(
        code="LkSG-3",
        framework="LkSG",
        article="§ 3",
        title="Due diligence obligations",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("LkSG § 3", "§ 3", "LkSG S. 3", "Sorgfaltspflicht"),
    ),
    FrameworkArticle(
        code="LkSG-4",
        framework="LkSG",
        article="§ 4",
        title="Risk analysis",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("LkSG § 4", "§ 4", "risk analysis", "Risikoanalyse"),
    ),
    FrameworkArticle(
        code="LkSG-5",
        framework="LkSG",
        article="§ 5",
        title="Preventive measures",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("LkSG § 5", "§ 5", "preventive measures", "Präventionsmaßnahmen"),
    ),
    FrameworkArticle(
        code="LkSG-6",
        framework="LkSG",
        article="§ 6",
        title="Remediation measures",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("LkSG § 6", "§ 6", "remediation", "Abhilfemaßnahmen"),
    ),
    FrameworkArticle(
        code="LkSG-7",
        framework="LkSG",
        article="§ 7",
        title="Complaint mechanisms",
        obligation_type="mandatory",
        esg_categories=("Governance", "Social"),
        keywords=("LkSG § 7", "§ 7", "Beschwerdeverfahren", "complaint mechanism"),
    ),
    FrameworkArticle(
        code="LkSG-8",
        framework="LkSG",
        article="§ 8",
        title="Documentation and reporting obligations",
        obligation_type="mandatory",
        esg_categories=("Governance",),
        keywords=("LkSG § 8", "§ 8", "Dokumentation", "reporting obligation"),
    ),
    FrameworkArticle(
        code="LkSG-10",
        framework="LkSG",
        article="§ 10",
        title="Due diligence obligations for indirect suppliers",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("LkSG § 10", "§ 10", "indirect supplier", "mittelbarer Zulieferer"),
    ),
]

# ---------------------------------------------------------------------------
# ESRS — European Sustainability Reporting Standards (CSRD)
# ---------------------------------------------------------------------------

ESRS = [
    FrameworkArticle(
        code="ESRS-E1",
        framework="ESRS",
        article="ESRS E1",
        title="Climate change",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("ESRS E1", "climate change", "GHG emissions", "carbon", "net zero", "Scope 3"),
    ),
    FrameworkArticle(
        code="ESRS-E2",
        framework="ESRS",
        article="ESRS E2",
        title="Pollution",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("ESRS E2", "pollution", "chemical", "hazardous substances"),
    ),
    FrameworkArticle(
        code="ESRS-E3",
        framework="ESRS",
        article="ESRS E3",
        title="Water and marine resources",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("ESRS E3", "water", "wastewater", "effluent", "marine", "CSRD E3"),
    ),
    FrameworkArticle(
        code="ESRS-E4",
        framework="ESRS",
        article="ESRS E4",
        title="Biodiversity and ecosystems",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("ESRS E4", "biodiversity", "ecosystems", "habitat", "deforestation"),
    ),
    FrameworkArticle(
        code="ESRS-E5",
        framework="ESRS",
        article="ESRS E5",
        title="Resource use and circular economy",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("ESRS E5", "resource use", "circular economy", "waste", "recycling"),
    ),
    FrameworkArticle(
        code="ESRS-S1",
        framework="ESRS",
        article="ESRS S1",
        title="Own workforce",
        obligation_type="mandatory",
        esg_categories=("Social",),
        keywords=("ESRS S1", "own workforce", "employees", "working conditions", "labour rights"),
    ),
    FrameworkArticle(
        code="ESRS-S2",
        framework="ESRS",
        article="ESRS S2",
        title="Workers in the value chain",
        obligation_type="mandatory",
        esg_categories=("Social",),
        keywords=("ESRS S2", "value chain workers", "supply chain workers", "forced labour", "child labour"),
    ),
    FrameworkArticle(
        code="ESRS-S3",
        framework="ESRS",
        article="ESRS S3",
        title="Affected communities",
        obligation_type="mandatory",
        esg_categories=("Social",),
        keywords=("ESRS S3", "affected communities", "indigenous peoples", "community impact"),
    ),
    FrameworkArticle(
        code="ESRS-G1",
        framework="ESRS",
        article="ESRS G1",
        title="Business conduct",
        obligation_type="mandatory",
        esg_categories=("Governance",),
        keywords=("ESRS G1", "business conduct", "anti-corruption", "bribery", "whistleblower"),
    ),
]

# ---------------------------------------------------------------------------
# GRI Standards
# ---------------------------------------------------------------------------

GRI = [
    FrameworkArticle(
        code="GRI-2",
        framework="GRI",
        article="GRI 2",
        title="General disclosures — governance",
        obligation_type="recommended",
        esg_categories=("Governance",),
        keywords=("GRI 2", "GRI Standards 2", "general disclosures"),
    ),
    FrameworkArticle(
        code="GRI-303",
        framework="GRI",
        article="GRI 303",
        title="Water and effluents",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("GRI 303", "water effluent", "wastewater discharge", "water withdrawal"),
    ),
    FrameworkArticle(
        code="GRI-304",
        framework="GRI",
        article="GRI 304",
        title="Biodiversity",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("GRI 304", "biodiversity impact", "protected areas"),
    ),
    FrameworkArticle(
        code="GRI-305",
        framework="GRI",
        article="GRI 305",
        title="Emissions",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("GRI 305", "GHG", "greenhouse gas", "Scope 1", "Scope 2"),
    ),
    FrameworkArticle(
        code="GRI-403",
        framework="GRI",
        article="GRI 403",
        title="Occupational health and safety",
        obligation_type="recommended",
        esg_categories=("Social",),
        keywords=("GRI 403", "occupational health", "health and safety", "workplace safety"),
    ),
    FrameworkArticle(
        code="GRI-408",
        framework="GRI",
        article="GRI 408",
        title="Child labor",
        obligation_type="recommended",
        esg_categories=("Social",),
        keywords=("GRI 408", "child labor", "child labour", "child worker"),
    ),
    FrameworkArticle(
        code="GRI-409",
        framework="GRI",
        article="GRI 409",
        title="Forced or compulsory labor",
        obligation_type="recommended",
        esg_categories=("Social",),
        keywords=("GRI 409", "forced labour", "forced labor", "compulsory labor", "modern slavery"),
    ),
    FrameworkArticle(
        code="GRI-414",
        framework="GRI",
        article="GRI 414",
        title="Supplier social assessment",
        obligation_type="recommended",
        esg_categories=("Social",),
        keywords=("GRI 414", "supplier social assessment", "supplier audit", "supply chain audit"),
    ),
]

# ---------------------------------------------------------------------------
# Unified catalog and lookup
# ---------------------------------------------------------------------------

ALL_ARTICLES: list[FrameworkArticle] = CSDDD + LKSG + ESRS + GRI

_BY_CODE: dict[str, FrameworkArticle] = {a.code: a for a in ALL_ARTICLES}
_BY_FRAMEWORK: dict[str, list[FrameworkArticle]] = {}
for _article in ALL_ARTICLES:
    _BY_FRAMEWORK.setdefault(_article.framework, []).append(_article)


def get_article(code: str) -> FrameworkArticle | None:
    return _BY_CODE.get(code)


def get_by_framework(framework: str) -> list[FrameworkArticle]:
    upper = framework.upper()
    for key, articles in _BY_FRAMEWORK.items():
        if key.upper() == upper:
            return articles
    return []


def all_frameworks() -> list[str]:
    return list(_BY_FRAMEWORK.keys())
