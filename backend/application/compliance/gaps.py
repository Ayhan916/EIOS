"""
Compliance Gap Analysis

Identifies which mandatory (and high-exposure recommended) regulatory
obligations are not addressed in an assessment, and explains each gap
with a severity classification and concrete remediation guidance.

Design:
  - Pure function: no I/O, no LLM
  - Explanation and remediation hints are deterministic per article
  - Gaps are sorted by regulatory_exposure descending (highest risk first)
"""

from __future__ import annotations

from dataclasses import dataclass

from .coverage import ComplianceCoverageReport
from .frameworks import ALL_ARTICLES, FrameworkArticle
from .weights import exposure


@dataclass
class ComplianceGap:
    article_code: str
    framework: str
    article: str
    title: str
    obligation_type: str
    esg_categories: tuple[str, ...]
    regulatory_exposure: float
    gap_severity: str        # "critical" | "high" | "medium"
    explanation: str         # why this gap is significant
    remediation_hint: str    # concrete action to address it


# ---------------------------------------------------------------------------
# Per-article explanations and remediation hints
# ---------------------------------------------------------------------------

_EXPLANATIONS: dict[str, str] = {
    "CSDDD-Art-5": (
        "No evidence of a formal due diligence policy integrating sustainability obligations. "
        "CSDDD requires this policy to be reviewed annually and embedded in company procedures."
    ),
    "CSDDD-Art-6": (
        "The assessment does not address identification of actual and potential adverse impacts "
        "across operations and supply chain tiers. This is the foundational CSDDD obligation "
        "from which all subsequent steps derive."
    ),
    "CSDDD-Art-7": (
        "No preventive measures or action plans are documented for potential adverse impacts. "
        "CSDDD Art. 7 requires contractual assurances from business partners and verified "
        "preventive action before impacts materialise."
    ),
    "CSDDD-Art-8": (
        "Where actual adverse impacts have been confirmed, no evidence of corrective measures "
        "bringing those impacts to an end is present. CSDDD requires a correction plan with "
        "clear timelines."
    ),
    "CSDDD-Art-9": (
        "Remediation for affected stakeholders is not addressed. CSDDD Art. 9 requires "
        "companies to provide or co-operate in remediation when they caused or contributed "
        "to an adverse impact."
    ),
    "CSDDD-Art-10": (
        "Grievance mechanisms accessible to affected persons and trade unions are not "
        "documented. CSDDD requires companies to maintain effective and transparent "
        "complaint procedures."
    ),
    "CSDDD-Art-11": (
        "No monitoring process is described for assessing the effectiveness of due diligence "
        "measures. CSDDD requires at-least-annual reviews."
    ),
    "CSDDD-Art-12": (
        "Public disclosure of due diligence approach, impacts identified, and actions taken "
        "is absent. CSDDD Art. 12 requires annual publication on the company website."
    ),
    "CSDDD-Art-22": (
        "The board's duty of care for integrating sustainability risks into corporate strategy "
        "is not addressed. Directors may face personal liability under CSDDD Art. 22."
    ),
    "LkSG-3": (
        "Overall due diligence obligations under the German Supply Chain Act are not "
        "documented. LkSG § 3 is the overarching obligation from which all LkSG "
        "compliance requirements flow."
    ),
    "LkSG-4": (
        "Risk analysis of own business area and direct suppliers as required by LkSG § 4 "
        "is missing. This is the mandatory starting point; enforcement actions and fines "
        "under the LkSG typically begin with § 4 non-compliance."
    ),
    "LkSG-5": (
        "Preventive measures in the company's own operations and towards direct suppliers "
        "are not evidenced. LkSG § 5 requires these to flow directly from the § 4 "
        "risk analysis."
    ),
    "LkSG-6": (
        "Remediation measures when human rights or environmental violations are confirmed "
        "are not addressed. LkSG § 6 requires an immediate remediation plan."
    ),
    "LkSG-7": (
        "Complaint procedures for employees and supply chain workers to report violations "
        "are not described. LkSG § 7 mandates an accessible and confidential process."
    ),
    "LkSG-8": (
        "Documentation of due diligence measures and annual reporting to BAFA "
        "(Federal Office for Economic Affairs) are not mentioned. LkSG § 8 requires "
        "public reporting starting 7 years after issuance."
    ),
    "LkSG-10": (
        "Due diligence obligations triggered by substantiated knowledge of indirect supplier "
        "violations (LkSG § 10) are not addressed. This is increasingly a focus of BAFA "
        "enforcement guidance."
    ),
    "ESRS-E1": (
        "Climate change impacts, transition plans, and GHG emission targets (including Scope 3) "
        "are not covered. ESRS E1 is the highest-profile CSRD disclosure topic with mandatory "
        "narrative and metric requirements."
    ),
    "ESRS-E2": (
        "Pollution risks and prevention measures across operations and supply chain are absent. "
        "ESRS E2 covers air, water, soil, and microplastics."
    ),
    "ESRS-E3": (
        "Water consumption, withdrawal, and effluent quality disclosures are missing. "
        "ESRS E3 requires site-level reporting in water-stressed areas."
    ),
    "ESRS-E4": (
        "Biodiversity impacts, species exposure, and ecosystem dependencies are not addressed. "
        "ESRS E4 is particularly relevant for companies with operations near protected areas."
    ),
    "ESRS-E5": (
        "Resource use, waste generation, and circular economy strategy are not covered. "
        "ESRS E5 requires disclosure of waste volumes by type and treatment method."
    ),
    "ESRS-S1": (
        "Working conditions, health and safety, and labour rights in the company's own "
        "workforce are not documented. ESRS S1 requires both narrative and metrics."
    ),
    "ESRS-S2": (
        "Value chain worker rights including forced and child labour risks are not assessed. "
        "ESRS S2 is mandatory and often the most material social topic for sourcing companies."
    ),
    "ESRS-S3": (
        "Impacts on affected communities near operations or along the value chain are not "
        "considered. ESRS S3 includes indigenous peoples' rights and land-related impacts."
    ),
    "ESRS-G1": (
        "Business conduct disclosures including anti-corruption, bribery risk, and "
        "whistleblower channels are absent. ESRS G1 requires quantitative corruption "
        "incident reporting."
    ),
    "GRI-2": (
        "General governance disclosures (board composition, remuneration, stakeholder "
        "engagement) following GRI 2 are not provided. These form the narrative backbone "
        "of sustainability reports."
    ),
    "GRI-303": (
        "Water withdrawal, recycling and discharge data per GRI 303 are not reported. "
        "Increasingly required by investors and sector benchmarks."
    ),
    "GRI-304": (
        "Biodiversity impacts on IUCN Red List species and protected habitats are not "
        "disclosed per GRI 304."
    ),
    "GRI-305": (
        "GHG emissions (Scope 1, 2 and, where applicable, Scope 3) are not quantified "
        "per GRI 305. This is the most commonly requested disclosure in investor ESG surveys."
    ),
    "GRI-403": (
        "Occupational health and safety management system, incident rates and "
        "hazard identification processes are not reported per GRI 403."
    ),
    "GRI-408": (
        "Child labour screening and remediation are not addressed per GRI 408. "
        "Despite being a GRI voluntary standard, child labour disclosures are increasingly "
        "required under customer codes of conduct and national law."
    ),
    "GRI-409": (
        "Forced labour risks and supplier screening are not disclosed per GRI 409. "
        "Modern slavery reporting is a legal requirement in multiple jurisdictions "
        "and expected by most institutional investors."
    ),
    "GRI-414": (
        "Supplier social assessment process — percentage of suppliers screened and "
        "significant negative impacts identified — is not reported per GRI 414."
    ),
}

_REMEDIATION_HINTS: dict[str, str] = {
    "CSDDD-Art-5": (
        "Develop and publish a board-approved Human Rights and Environmental Due Diligence "
        "Policy that explicitly references CSDDD obligations. Integrate into supplier codes "
        "of conduct and contract templates."
    ),
    "CSDDD-Art-6": (
        "Conduct a structured adverse impact identification across all operations and "
        "Tier 1–3 supply chain using sector-specific risk mapping. Document identified "
        "impacts in a risk register linked to the assessment."
    ),
    "CSDDD-Art-7": (
        "Develop preventive action plans for each identified potential adverse impact. "
        "Require contractual sustainability commitments from business partners. "
        "Implement supplier capacity building programmes."
    ),
    "CSDDD-Art-8": (
        "Create a corrective action plan for each confirmed adverse impact with assigned "
        "ownership, milestones and a target resolution date. Track progress quarterly."
    ),
    "CSDDD-Art-9": (
        "Establish a remediation procedure specifying how affected stakeholders will receive "
        "remedy (financial compensation, reinstatement, apology). Document co-operation "
        "with state-based grievance mechanisms."
    ),
    "CSDDD-Art-10": (
        "Implement an accessible grievance channel (hotline, web portal) available to "
        "workers, communities and civil society in relevant languages. Publish procedural "
        "rules and commit to acknowledgement within 72 hours."
    ),
    "CSDDD-Art-11": (
        "Define KPIs for each due diligence measure and schedule an annual effectiveness "
        "review with board-level sign-off. Document outcomes and adjustments made."
    ),
    "CSDDD-Art-12": (
        "Publish an annual due diligence statement on the company website covering "
        "impacts identified, measures taken, and outcomes. Align format with CSDDD "
        "Commission guidance once issued."
    ),
    "CSDDD-Art-22": (
        "Ensure the board formally integrates ESG and human rights risks into strategy "
        "reviews and executive remuneration. Document board ESG competence and training."
    ),
    "LkSG-3": (
        "Assign a Human Rights Officer (Menschenrechtsbeauftragter) and establish "
        "due diligence procedures meeting all LkSG §§ 4–10 requirements. Seek "
        "external legal review of the compliance programme."
    ),
    "LkSG-4": (
        "Conduct a risk analysis of the company's own business area and all direct "
        "suppliers using the LkSG risk catalogue. Prioritise by risk potential "
        "(likelihood × severity). Document and update annually or on material change."
    ),
    "LkSG-5": (
        "Implement preventive measures derived from the § 4 risk analysis: "
        "supplier declarations, training, audit protocols and contractual clauses. "
        "Document which measures address which identified risks."
    ),
    "LkSG-6": (
        "Draft a remediation concept with concrete steps to end ongoing violations, "
        "compensate victims where possible, and prevent recurrence. Submit to BAFA "
        "if required."
    ),
    "LkSG-7": (
        "Establish or join an industry grievance mechanism meeting the effectiveness "
        "criteria of § 7. Publish contact details and ensure accessibility in relevant "
        "supplier-country languages."
    ),
    "LkSG-8": (
        "Implement a documentation system covering all due diligence measures. "
        "Prepare an annual report for publication and BAFA submission. Retain "
        "records for 7 years."
    ),
    "LkSG-10": (
        "Establish a trigger protocol for § 10: when substantiated knowledge of "
        "indirect supplier violations is obtained, initiate risk analysis and "
        "preventive/corrective measures within the defined timeframe."
    ),
    "ESRS-E1": (
        "Perform a climate risk and opportunity assessment (physical and transition). "
        "Set science-based emissions reduction targets. Disclose Scope 1, 2 and "
        "material Scope 3 GHG categories in the sustainability report."
    ),
    "ESRS-E2": (
        "Inventory pollutant emissions (air, water, soil) and assess material chemical "
        "use against SVHC lists. Define targets and monitoring processes."
    ),
    "ESRS-E3": (
        "Identify water-stressed operational sites. Report withdrawal, consumption "
        "and discharge by source. Set water efficiency and quality targets."
    ),
    "ESRS-E4": (
        "Conduct a biodiversity impact and dependency assessment using TNFD/SBTN "
        "frameworks. Map sites in or adjacent to biodiversity-sensitive areas."
    ),
    "ESRS-E5": (
        "Implement circular economy strategy with waste reduction targets. Report "
        "waste generation, treatment method and recycled input rates."
    ),
    "ESRS-S1": (
        "Conduct a working conditions review in own operations. Disclose health and "
        "safety incident rates, collective bargaining coverage and living wage commitment."
    ),
    "ESRS-S2": (
        "Map supply chain tiers for forced and child labour exposure. Implement "
        "on-site audits, worker voice surveys and remediation protocols for "
        "value chain workers."
    ),
    "ESRS-S3": (
        "Engage affected communities through free, prior and informed consent (FPIC) "
        "processes where applicable. Disclose community grievances and how they "
        "were resolved."
    ),
    "ESRS-G1": (
        "Implement anti-corruption training, a conflicts-of-interest policy and a "
        "confidential whistleblower channel. Disclose confirmed corruption incidents "
        "and legal proceedings."
    ),
    "GRI-2": (
        "Report governance structure, board skills matrix, stakeholder engagement "
        "approach and remuneration link to sustainability performance per GRI 2."
    ),
    "GRI-303": (
        "Report water withdrawal by source, recycling rates and quality of "
        "discharges per GRI 303."
    ),
    "GRI-304": (
        "Report IUCN Red List species interactions and operational footprint near "
        "protected habitats per GRI 304."
    ),
    "GRI-305": (
        "Report Scope 1, Scope 2 (market and location-based) and at least the most "
        "material Scope 3 categories per GRI 305. Use GHG Protocol methodology."
    ),
    "GRI-403": (
        "Report occupational injury rates (TRIR, LTIFR), dangerous occurrences and "
        "hazard identification processes per GRI 403."
    ),
    "GRI-408": (
        "Conduct child labour risk assessment across operations and supply chain. "
        "Report percentage of operations and suppliers assessed, and remediation "
        "actions taken per GRI 408."
    ),
    "GRI-409": (
        "Conduct forced labour risk assessment and supplier screening. Publish "
        "a modern slavery statement and remediation outcomes per GRI 409."
    ),
    "GRI-414": (
        "Report percentage of suppliers screened using social criteria and significant "
        "negative social impacts identified and addressed per GRI 414."
    ),
}

_DEFAULT_EXPLANATION = "This regulatory obligation is not addressed in the current assessment."
_DEFAULT_HINT = "Review the relevant regulatory text and integrate this obligation into the due diligence programme."


def _gap_severity(regulatory_exposure: float) -> str:
    if regulatory_exposure >= 0.90:
        return "critical"
    if regulatory_exposure >= 0.75:
        return "high"
    return "medium"


def compute_gaps(
    coverage_report: ComplianceCoverageReport,
    include_recommended: bool = False,
) -> list[ComplianceGap]:
    """
    Return a list of ComplianceGaps for all uncovered articles.

    By default only mandatory articles are included; set include_recommended=True
    to also surface high-exposure recommended articles (exposure >= 0.70).

    Gaps are sorted by regulatory_exposure descending (highest risk first).
    """
    covered = set(coverage_report.covered_article_codes)
    gaps: list[ComplianceGap] = []

    for article in ALL_ARTICLES:
        if article.code in covered:
            continue
        if article.obligation_type == "recommended" and not include_recommended:
            continue
        if article.obligation_type == "recommended":
            exp = exposure(article.code)
            if exp < 0.70:
                continue

        exp = exposure(article.code)
        gaps.append(
            ComplianceGap(
                article_code=article.code,
                framework=article.framework,
                article=article.article,
                title=article.title,
                obligation_type=article.obligation_type,
                esg_categories=article.esg_categories,
                regulatory_exposure=exp,
                gap_severity=_gap_severity(exp),
                explanation=_EXPLANATIONS.get(article.code, _DEFAULT_EXPLANATION),
                remediation_hint=_REMEDIATION_HINTS.get(article.code, _DEFAULT_HINT),
            )
        )

    gaps.sort(key=lambda g: g.regulatory_exposure, reverse=True)
    return gaps
