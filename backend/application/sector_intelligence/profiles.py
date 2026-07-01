"""
EIOS Sector ESG Risk Profiles

Static, curated ESG risk profiles for major NACE-classified industry sectors.
Each profile captures the inherent ESG exposure of a sector, independent of
any specific company or assessment. Used as the baseline for benchmarking.

Sources: CSDDD impact chain analysis, LkSG sector guidance, ESRS sector standards,
GRI sector standards, OECD sector-level human rights due diligence guidance.

Coverage: NACE sections A–S (most commercially significant sectors for ESG DD).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectorESGProfile:
    """Static ESG risk profile for a NACE sector section."""

    nace_section: str  # "A", "B", "C" …
    section_name: str  # Human-readable name
    environmental_risk: str  # Low | Medium | High | Critical
    social_risk: str
    governance_risk: str
    overall_risk: str  # Derived: max of the three
    key_risk_themes: tuple[str, ...]
    applicable_frameworks: tuple[str, ...]
    # Minimum mandatory compliance coverage expected for a credible assessment
    baseline_mandatory_coverage: float  # 0.0 – 1.0
    # How many material findings a credible assessment should surface (lower bound)
    expected_min_findings: int
    expected_min_risks: int
    regulatory_exposure_notes: str
    esg_priority_categories: tuple[str, ...]


# ---------------------------------------------------------------------------
# NACE Section profiles
# ---------------------------------------------------------------------------

_PROFILES: list[SectorESGProfile] = [
    SectorESGProfile(
        nace_section="A",
        section_name="Agriculture, Forestry and Fishing",
        environmental_risk="Critical",
        social_risk="High",
        governance_risk="Medium",
        overall_risk="Critical",
        key_risk_themes=(
            "Deforestation and biodiversity loss",
            "Pesticide and chemical use",
            "Water stress and depletion",
            "Child and forced labour in supply chains",
            "Land rights and community displacement",
            "Greenhouse gas emissions (Scope 1/2)",
        ),
        applicable_frameworks=("CSDDD", "LkSG", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.55,
        expected_min_findings=3,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "High CSDDD exposure for large agribusinesses; LkSG applies from 2024 "
            "to all German-nexus supply chains. ESRS E1 (climate) and S1 (own workforce) "
            "mandatory. Commodities regulation (EUDR) applies to forestry and soy/cocoa."
        ),
        esg_priority_categories=("Climate & Biodiversity", "Labour Rights", "Supply Chain"),
    ),
    SectorESGProfile(
        nace_section="B",
        section_name="Mining and Quarrying",
        environmental_risk="Critical",
        social_risk="Critical",
        governance_risk="High",
        overall_risk="Critical",
        key_risk_themes=(
            "Soil and water contamination",
            "Artisanal and small-scale mining (ASM) human rights",
            "Indigenous peoples and Free Prior and Informed Consent (FPIC)",
            "Tailings dam failure and environmental disasters",
            "Conflict minerals and supply chain traceability",
            "Greenhouse gas and methane emissions",
            "Community health and safety",
        ),
        applicable_frameworks=("CSDDD", "LkSG", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.65,
        expected_min_findings=4,
        expected_min_risks=3,
        regulatory_exposure_notes=(
            "Among the highest regulatory exposure sectors. EU Conflict Minerals Regulation, "
            "CSDDD priority sector, LkSG Chapter 2 obligations apply directly. "
            "Significant ESRS E2 (pollution), E4 (biodiversity), S3 (affected communities) exposure. "
            "OECD Due Diligence Guidance for Responsible Mineral Supply Chains applies."
        ),
        esg_priority_categories=(
            "Environmental Impact",
            "Human Rights",
            "Supply Chain",
            "Community",
        ),
    ),
    SectorESGProfile(
        nace_section="C",
        section_name="Manufacturing",
        environmental_risk="High",
        social_risk="High",
        governance_risk="Medium",
        overall_risk="High",
        key_risk_themes=(
            "Supply chain labour rights (Tier 2/3)",
            "Workplace health and safety",
            "Industrial emissions and pollution",
            "Hazardous chemicals and substances",
            "Carbon footprint and energy transition",
            "Packaging and waste",
        ),
        applicable_frameworks=("CSDDD", "LkSG", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.55,
        expected_min_findings=3,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "Core LkSG and CSDDD target sector. Supply chain traceability to raw material "
            "extraction is required. ESRS S2 (value chain workers) and E2 (pollution) key. "
            "Product safety and chemical regulation (REACH) relevant for chemical manufacturers."
        ),
        esg_priority_categories=("Supply Chain", "Labour Rights", "Environmental Impact"),
    ),
    SectorESGProfile(
        nace_section="D",
        section_name="Electricity, Gas, Steam and Air Conditioning Supply",
        environmental_risk="Critical",
        social_risk="Medium",
        governance_risk="High",
        overall_risk="Critical",
        key_risk_themes=(
            "Greenhouse gas emissions and energy transition",
            "Stranded asset risk",
            "Energy access and just transition",
            "Nuclear and radioactive waste",
            "Biodiversity impacts of infrastructure",
            "Grid and supply security",
        ),
        applicable_frameworks=("CSDDD", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.60,
        expected_min_findings=3,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "Highest climate (ESRS E1) exposure. EU Taxonomy alignment required for "
            "green finance. SFDR applies to institutional investors in this sector. "
            "Paris Agreement alignment and science-based targets expected by investors."
        ),
        esg_priority_categories=(
            "Climate & Energy Transition",
            "Environmental Impact",
            "Governance",
        ),
    ),
    SectorESGProfile(
        nace_section="F",
        section_name="Construction",
        environmental_risk="High",
        social_risk="High",
        governance_risk="Medium",
        overall_risk="High",
        key_risk_themes=(
            "Construction worker health and safety",
            "Migrant and contract labour exploitation",
            "Raw material sourcing (timber, minerals, sand)",
            "Energy efficiency and building emissions",
            "Waste and demolition materials",
            "Corruption and public procurement",
        ),
        applicable_frameworks=("CSDDD", "LkSG", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.50,
        expected_min_findings=2,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "High ILO Convention exposure for labour rights. EU Buildings Directive (EPBD) "
            "drives energy efficiency obligations. Timber Regulation and EUDR affect "
            "material sourcing. LkSG supply chain obligations apply to sub-contractors."
        ),
        esg_priority_categories=("Labour Rights", "Supply Chain", "Environmental Impact"),
    ),
    SectorESGProfile(
        nace_section="G",
        section_name="Wholesale and Retail Trade",
        environmental_risk="Medium",
        social_risk="High",
        governance_risk="Medium",
        overall_risk="High",
        key_risk_themes=(
            "Supply chain labour rights (global sourcing)",
            "Product safety and consumer protection",
            "Packaging and single-use plastics",
            "Living wages in retail workforce",
            "Food waste and responsible sourcing",
            "Tax transparency and pricing practices",
        ),
        applicable_frameworks=("CSDDD", "LkSG", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.50,
        expected_min_findings=2,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "Major LkSG target sector due to complex global supply chains. "
            "CSDDD requires mapping to Tier 1 and beyond for high-risk commodities. "
            "ESRS S2 (value chain workers) central. Textile and apparel sub-sectors "
            "face highest exposure (Rana Plaza legacy; EU due diligence regulation)."
        ),
        esg_priority_categories=("Supply Chain", "Labour Rights", "Consumer Protection"),
    ),
    SectorESGProfile(
        nace_section="H",
        section_name="Transportation and Storage",
        environmental_risk="High",
        social_risk="Medium",
        governance_risk="Medium",
        overall_risk="High",
        key_risk_themes=(
            "GHG emissions from transport (Scope 1)",
            "Driver and logistics worker rights",
            "Dangerous goods and spill risk",
            "Supply chain visibility and traceability",
            "Port and logistics labour standards",
            "Decarbonisation transition risk",
        ),
        applicable_frameworks=("CSDDD", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.45,
        expected_min_findings=2,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "EU Fit for 55 package drives emission reduction obligations. Maritime (IMO) "
            "and aviation (CORSIA) specific regulations. FuelEU Maritime applies from 2025. "
            "Platform economy labour classification risk for gig logistics workers."
        ),
        esg_priority_categories=("Climate & Emissions", "Labour Rights", "Environmental Impact"),
    ),
    SectorESGProfile(
        nace_section="J",
        section_name="Information and Communication",
        environmental_risk="Medium",
        social_risk="Medium",
        governance_risk="High",
        overall_risk="High",
        key_risk_themes=(
            "Data privacy and digital rights",
            "AI ethics and algorithmic bias",
            "Supply chain minerals and conflict minerals in devices",
            "Data centre energy consumption",
            "Cybersecurity and system resilience",
            "Content moderation and freedom of expression",
        ),
        applicable_frameworks=("CSDDD", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.40,
        expected_min_findings=2,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "EU AI Act, GDPR, and DSA create significant governance obligations. "
            "CSDDD applies to hardware supply chains (conflict minerals in chips/devices). "
            "ESRS G1 (business conduct) and S4 (consumers) central. "
            "Growing investor focus on AI governance and digital rights."
        ),
        esg_priority_categories=("Governance & Ethics", "Digital Rights", "Supply Chain"),
    ),
    SectorESGProfile(
        nace_section="K",
        section_name="Financial and Insurance Activities",
        environmental_risk="Medium",
        social_risk="Medium",
        governance_risk="Critical",
        overall_risk="High",
        key_risk_themes=(
            "Financed emissions (Scope 3 Category 15)",
            "Anti-money laundering and financial crime",
            "Responsible lending and insurance practices",
            "ESG integration in investment decisions",
            "Executive pay and board diversity",
            "Systemic risk and financial stability",
        ),
        applicable_frameworks=("ESRS", "GRI"),
        baseline_mandatory_coverage=0.40,
        expected_min_findings=2,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "SFDR (sustainable finance disclosure), EU Taxonomy, and EBA sustainability "
            "risk guidelines create significant reporting obligations. ESRS S1 (own workforce) "
            "and G1 (business conduct) central. Financed emissions increasingly material "
            "under PCAF methodology and Paris-alignment investor expectations."
        ),
        esg_priority_categories=(
            "Governance & Ethics",
            "Financed Emissions",
            "Responsible Business",
        ),
    ),
    SectorESGProfile(
        nace_section="Q",
        section_name="Human Health and Social Work Activities",
        environmental_risk="Low",
        social_risk="High",
        governance_risk="Medium",
        overall_risk="High",
        key_risk_themes=(
            "Patient rights and data privacy",
            "Healthcare worker rights and burnout",
            "Medical waste and pharmaceutical pollution",
            "Access to medicine and pricing practices",
            "Clinical trial ethics",
            "Supply chain quality (medical devices, pharmaceuticals)",
        ),
        applicable_frameworks=("CSDDD", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.40,
        expected_min_findings=2,
        expected_min_risks=2,
        regulatory_exposure_notes=(
            "CSDDD applies to pharmaceutical and medical device supply chains. "
            "ESRS S1 (own workforce) and S4 (consumers/patients) central. "
            "WHO guidance on access to medicine and responsible licensing relevant. "
            "Strong national regulatory frameworks (EMA, FDA) create additional obligations."
        ),
        esg_priority_categories=("Labour Rights", "Consumer Protection", "Environmental Impact"),
    ),
    # Generic fallback for unrecognised sectors
    SectorESGProfile(
        nace_section="*",
        section_name="General Industry",
        environmental_risk="Medium",
        social_risk="Medium",
        governance_risk="Medium",
        overall_risk="Medium",
        key_risk_themes=(
            "Supply chain due diligence",
            "Workplace health and safety",
            "Environmental impact management",
            "Business ethics and anti-corruption",
            "Data privacy",
        ),
        applicable_frameworks=("CSDDD", "LkSG", "ESRS", "GRI"),
        baseline_mandatory_coverage=0.40,
        expected_min_findings=2,
        expected_min_risks=1,
        regulatory_exposure_notes=(
            "Baseline ESG due diligence obligations apply across all sectors. "
            "CSDDD and LkSG supply chain requirements apply from specified thresholds. "
            "ESRS (CSRD) mandatory for large EU companies from 2025."
        ),
        esg_priority_categories=("Supply Chain", "Governance & Ethics", "Environmental Impact"),
    ),
]

_BY_SECTION: dict[str, SectorESGProfile] = {p.nace_section: p for p in _PROFILES}

_FALLBACK = _BY_SECTION["*"]


def get_profile(nace_code: str) -> SectorESGProfile:
    """Return the ESG profile for the given NACE code.

    Accepts both section letters ("C", "H") and 2-digit numeric codes ("29", "49").
    Falls back to the generic profile when the section is not covered.
    """
    if not nace_code:
        return _FALLBACK
    cleaned = nace_code.strip()
    # Numeric 2-digit code → resolve to section letter via taxonomy
    if cleaned[:1].isdigit():
        from application.sector_intelligence.nace_taxonomy import get_section
        result = get_section(cleaned)
        section = result[0] if result else cleaned[:1].upper()
    else:
        section = cleaned[0].upper()
    return _BY_SECTION.get(section, _FALLBACK)


def get_profile_by_section(section: str) -> SectorESGProfile:
    return _BY_SECTION.get(section.upper(), _FALLBACK)


def all_profiles() -> list[SectorESGProfile]:
    return [p for p in _PROFILES if p.nace_section != "*"]
