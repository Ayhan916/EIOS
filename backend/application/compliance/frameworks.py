"""
EIOS Compliance Framework Library

Structured definitions of regulatory framework articles relevant to ESG
due diligence. Used for compliance coverage analysis and audit reporting.

Coverage:
  CSDDD      — EU Corporate Sustainability Due Diligence Directive (2024)
  LkSG       — German Supply Chain Due Diligence Act (2023)
  ESRS       — European Sustainability Reporting Standards (CSRD, 2024)
  GRI        — Global Reporting Initiative Standards (2021–2023)
  CSRD       — EU Corporate Sustainability Reporting Directive (2022)
  EU_TAXONOMY — EU Taxonomy Regulation (2020)
  ISSB       — IFRS Sustainability Disclosure Standards S1/S2 (2023)
  TCFD       — Task Force on Climate-related Financial Disclosures (2017/2021)
"""

from __future__ import annotations

from dataclasses import dataclass


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
        keywords=(
            "CSDDD Art. 6",
            "Art 6",
            "identification of adverse impacts",
            "adverse impact identification",
        ),
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
        keywords=(
            "CSDDD Art. 8",
            "Art 8",
            "remediation",
            "bringing to an end",
            "corrective action",
        ),
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
        keywords=(
            "CSDDD Art. 10",
            "Art 10",
            "grievance mechanism",
            "complaint procedure",
            "grievance",
        ),
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
        keywords=(
            "ESRS S2",
            "value chain workers",
            "supply chain workers",
            "forced labour",
            "child labour",
        ),
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
# CSRD — EU Corporate Sustainability Reporting Directive
# ---------------------------------------------------------------------------

CSRD = [
    FrameworkArticle(
        code="CSRD-Art-19a",
        framework="CSRD",
        article="Art. 19a",
        title="Sustainability reporting — large companies",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("CSRD Art. 19a", "Art 19a", "sustainability reporting", "CSRD disclosure"),
    ),
    FrameworkArticle(
        code="CSRD-Art-29a",
        framework="CSRD",
        article="Art. 29a",
        title="Consolidated sustainability reporting",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("CSRD Art. 29a", "Art 29a", "consolidated sustainability", "group reporting"),
    ),
    FrameworkArticle(
        code="CSRD-Art-19b",
        framework="CSRD",
        article="Art. 19b",
        title="Double materiality assessment",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("double materiality", "materiality assessment", "CSRD materiality", "impact materiality", "financial materiality"),
    ),
    FrameworkArticle(
        code="CSRD-Art-8",
        framework="CSRD",
        article="Art. 8",
        title="Non-financial information — value chain",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social"),
        keywords=("CSRD Art. 8", "value chain disclosure", "supply chain reporting", "value chain sustainability"),
    ),
    FrameworkArticle(
        code="CSRD-Taxonomy",
        framework="CSRD",
        article="Art. 8 (Taxonomy)",
        title="EU Taxonomy alignment disclosure",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("taxonomy alignment", "eligible activities", "taxonomy turnover", "taxonomy capex", "taxonomy opex"),
    ),
    FrameworkArticle(
        code="CSRD-Audit",
        framework="CSRD",
        article="Art. 26a",
        title="Assurance of sustainability reporting",
        obligation_type="mandatory",
        esg_categories=("Governance",),
        keywords=("CSRD assurance", "limited assurance", "sustainability audit", "third-party assurance"),
    ),
]

# ---------------------------------------------------------------------------
# EU Taxonomy — Taxonomy Regulation (EU) 2020/852
# ---------------------------------------------------------------------------

EU_TAXONOMY = [
    FrameworkArticle(
        code="EUTAX-CCM",
        framework="EU_TAXONOMY",
        article="Annex I",
        title="Climate change mitigation — technical screening",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("climate change mitigation", "CCM", "EU taxonomy mitigation", "net-zero transition", "Scope 1 Scope 2"),
    ),
    FrameworkArticle(
        code="EUTAX-CCA",
        framework="EU_TAXONOMY",
        article="Annex II",
        title="Climate change adaptation — technical screening",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("climate change adaptation", "CCA", "EU taxonomy adaptation", "physical risk", "climate resilience"),
    ),
    FrameworkArticle(
        code="EUTAX-WMR",
        framework="EU_TAXONOMY",
        article="Annex III",
        title="Sustainable use of water and marine resources",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("water taxonomy", "marine resources taxonomy", "sustainable water", "water stewardship"),
    ),
    FrameworkArticle(
        code="EUTAX-CE",
        framework="EU_TAXONOMY",
        article="Annex IV",
        title="Circular economy",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("circular economy taxonomy", "waste prevention", "product lifecycle", "repair reuse recycle taxonomy"),
    ),
    FrameworkArticle(
        code="EUTAX-PPC",
        framework="EU_TAXONOMY",
        article="Annex V",
        title="Pollution prevention and control",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("pollution prevention taxonomy", "hazardous substances taxonomy", "DNSH pollution"),
    ),
    FrameworkArticle(
        code="EUTAX-BIO",
        framework="EU_TAXONOMY",
        article="Annex VI",
        title="Protection and restoration of biodiversity and ecosystems",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("biodiversity taxonomy", "ecosystem taxonomy", "nature-positive", "DNSH biodiversity"),
    ),
    FrameworkArticle(
        code="EUTAX-MSC",
        framework="EU_TAXONOMY",
        article="Art. 18",
        title="Minimum social safeguards (MSC)",
        obligation_type="mandatory",
        esg_categories=("Social", "Governance"),
        keywords=("minimum social safeguards", "MSC", "OECD guidelines taxonomy", "UN guiding principles taxonomy"),
    ),
    FrameworkArticle(
        code="EUTAX-DNSH",
        framework="EU_TAXONOMY",
        article="Art. 17",
        title="Do No Significant Harm (DNSH) principle",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("do no significant harm", "DNSH", "taxonomy DNSH", "significant harm"),
    ),
]

# ---------------------------------------------------------------------------
# ISSB — IFRS Sustainability Disclosure Standards S1 & S2 (2023)
# ---------------------------------------------------------------------------

ISSB = [
    FrameworkArticle(
        code="ISSB-S1-Core",
        framework="ISSB",
        article="IFRS S1",
        title="General sustainability-related financial disclosures",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("IFRS S1", "ISSB S1", "sustainability-related financial", "general sustainability disclosures"),
    ),
    FrameworkArticle(
        code="ISSB-S1-Gov",
        framework="ISSB",
        article="IFRS S1 — Governance",
        title="Governance of sustainability risks and opportunities",
        obligation_type="mandatory",
        esg_categories=("Governance",),
        keywords=("ISSB governance", "S1 governance", "board sustainability oversight", "sustainability governance body"),
    ),
    FrameworkArticle(
        code="ISSB-S1-Strategy",
        framework="ISSB",
        article="IFRS S1 — Strategy",
        title="Strategy for sustainability risks and opportunities",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("ISSB strategy", "S1 strategy", "sustainability strategy", "business model sustainability"),
    ),
    FrameworkArticle(
        code="ISSB-S1-Risk",
        framework="ISSB",
        article="IFRS S1 — Risk Management",
        title="Risk management for sustainability risks",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("ISSB risk management", "S1 risk", "sustainability risk management process", "integrated risk management"),
    ),
    FrameworkArticle(
        code="ISSB-S1-Metrics",
        framework="ISSB",
        article="IFRS S1 — Metrics",
        title="Metrics and targets — general sustainability",
        obligation_type="mandatory",
        esg_categories=("Environmental", "Social", "Governance"),
        keywords=("ISSB metrics", "S1 metrics", "sustainability KPIs", "sustainability targets"),
    ),
    FrameworkArticle(
        code="ISSB-S2-Core",
        framework="ISSB",
        article="IFRS S2",
        title="Climate-related financial disclosures",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("IFRS S2", "ISSB S2", "climate-related financial", "climate disclosure S2"),
    ),
    FrameworkArticle(
        code="ISSB-S2-Transition",
        framework="ISSB",
        article="IFRS S2 — Transition Plan",
        title="Climate transition plan",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("ISSB transition plan", "S2 transition", "climate transition plan", "net zero plan"),
    ),
    FrameworkArticle(
        code="ISSB-S2-Scenario",
        framework="ISSB",
        article="IFRS S2 — Scenario Analysis",
        title="Climate scenario analysis",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("ISSB scenario", "S2 scenario", "climate scenario analysis", "1.5C scenario", "2C scenario"),
    ),
    FrameworkArticle(
        code="ISSB-S2-GHG",
        framework="ISSB",
        article="IFRS S2 — GHG",
        title="GHG emissions disclosure (Scope 1, 2, 3)",
        obligation_type="mandatory",
        esg_categories=("Environmental",),
        keywords=("ISSB GHG", "S2 emissions", "Scope 1 2 3 ISSB", "greenhouse gas S2", "carbon footprint ISSB"),
    ),
]

# ---------------------------------------------------------------------------
# TCFD — Task Force on Climate-related Financial Disclosures
# ---------------------------------------------------------------------------

TCFD = [
    FrameworkArticle(
        code="TCFD-Gov",
        framework="TCFD",
        article="Governance",
        title="Board oversight of climate-related risks and opportunities",
        obligation_type="recommended",
        esg_categories=("Governance",),
        keywords=("TCFD governance", "board climate oversight", "management role climate", "climate governance"),
    ),
    FrameworkArticle(
        code="TCFD-Strategy-A",
        framework="TCFD",
        article="Strategy (a)",
        title="Climate-related risks and opportunities identified",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("TCFD strategy", "climate risks identified", "climate opportunities", "transition risk", "physical risk"),
    ),
    FrameworkArticle(
        code="TCFD-Strategy-B",
        framework="TCFD",
        article="Strategy (b)",
        title="Impact of climate risks on business, strategy and financial planning",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("TCFD financial impact", "climate financial planning", "climate business strategy", "strategic climate"),
    ),
    FrameworkArticle(
        code="TCFD-Strategy-C",
        framework="TCFD",
        article="Strategy (c)",
        title="Climate resilience of strategy and business model",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("TCFD resilience", "climate resilience", "2 degree scenario", "well below 2C", "scenario analysis TCFD"),
    ),
    FrameworkArticle(
        code="TCFD-Risk-A",
        framework="TCFD",
        article="Risk Management (a)",
        title="Process for identifying and assessing climate-related risks",
        obligation_type="recommended",
        esg_categories=("Environmental", "Governance"),
        keywords=("TCFD risk identification", "TCFD risk assessment", "climate risk process", "climate risk management"),
    ),
    FrameworkArticle(
        code="TCFD-Risk-B",
        framework="TCFD",
        article="Risk Management (b)",
        title="Process for managing climate-related risks",
        obligation_type="recommended",
        esg_categories=("Environmental", "Governance"),
        keywords=("TCFD risk management", "managing climate risk", "climate risk mitigation", "TCFD risk response"),
    ),
    FrameworkArticle(
        code="TCFD-Risk-C",
        framework="TCFD",
        article="Risk Management (c)",
        title="Integration of climate risk into enterprise risk management",
        obligation_type="recommended",
        esg_categories=("Governance",),
        keywords=("TCFD integrated risk", "ERM climate", "enterprise risk climate", "climate ERM"),
    ),
    FrameworkArticle(
        code="TCFD-Metrics-A",
        framework="TCFD",
        article="Metrics & Targets (a)",
        title="Climate-related metrics used to assess risks and opportunities",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("TCFD metrics", "climate KPIs", "climate indicators", "carbon metrics"),
    ),
    FrameworkArticle(
        code="TCFD-Metrics-B",
        framework="TCFD",
        article="Metrics & Targets (b)",
        title="Scope 1, 2 and 3 GHG emissions",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("TCFD Scope 1", "TCFD Scope 2", "TCFD Scope 3", "GHG emissions TCFD", "carbon footprint TCFD"),
    ),
    FrameworkArticle(
        code="TCFD-Metrics-C",
        framework="TCFD",
        article="Metrics & Targets (c)",
        title="Climate-related targets",
        obligation_type="recommended",
        esg_categories=("Environmental",),
        keywords=("TCFD targets", "climate targets", "net zero target", "science based targets", "SBTi"),
    ),
]

# ---------------------------------------------------------------------------
# Unified catalog and lookup
# ---------------------------------------------------------------------------

ALL_ARTICLES: list[FrameworkArticle] = CSDDD + LKSG + ESRS + GRI + CSRD + EU_TAXONOMY + ISSB + TCFD

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
