"""Source Credibility Engine — FR-006 / FR-007.

Deterministic mapping: source_name → (credibility_level, credibility_reason).

Credibility levels:
  High   — Official intergovernmental or government bodies with legal mandate.
            Data is authoritative, legally binding, regularly audited.
  Medium — Established institutions or aggregators with editorial oversight.
            Data is reliable but may lag, be incomplete, or require verification.
  Low    — Media aggregators, single articles, unverified or user-generated sources.
            Signals require independent corroboration before action.

Rule: never return an empty reason — FR-007 requires explicit explanation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CredibilityProfile:
    level: str   # "High" | "Medium" | "Low"
    reason: str  # Human-readable explanation for UI / audit trail


_CREDIBILITY_MATRIX: dict[str, CredibilityProfile] = {
    # ── High credibility — official sanctions & governance bodies ─────────────
    "eu_sanctions": CredibilityProfile(
        level="High",
        reason=(
            "EU Consolidated Financial Sanctions List (EEAS/FSF) — official EU legal instrument. "
            "Maintained by the European External Action Service under EU regulations. "
            "Entries are legally binding within EU jurisdiction."
        ),
    ),
    "ofac": CredibilityProfile(
        level="High",
        reason=(
            "OFAC SDN List (US Treasury) — official US government sanctions database. "
            "Maintained by the Office of Foreign Assets Control under US federal law. "
            "Violations carry criminal penalties; entries are legally authoritative."
        ),
    ),
    "un_sanctions": CredibilityProfile(
        level="High",
        reason=(
            "UN Security Council Consolidated Sanctions List — official UN legal instrument. "
            "Adopted under Chapter VII of the UN Charter. "
            "Binding on all 193 UN member states."
        ),
    ),
    "world_bank": CredibilityProfile(
        level="High",
        reason=(
            "World Bank Worldwide Governance Indicators (WGI) — official multilateral data. "
            "Published annually by the World Bank Group; covers 215 economies. "
            "Methodology peer-reviewed and publicly documented."
        ),
    ),
    "transparency_international": CredibilityProfile(
        level="High",
        reason=(
            "Transparency International Corruption Perceptions Index — globally recognised "
            "anti-corruption benchmark. Composite index based on expert surveys and "
            "institutional assessments from 13 independent sources."
        ),
    ),
    "ilo": CredibilityProfile(
        level="High",
        reason=(
            "International Labour Organization (ILO) — UN specialised agency. "
            "Labour standards data is treaty-based and ratified by member states. "
            "Authoritative source for CSDDD Annex I protected labour rights."
        ),
    ),
    "un_human_rights": CredibilityProfile(
        level="High",
        reason=(
            "UN Human Rights Office (OHCHR) — official UN human rights body. "
            "Reports and findings are based on UN treaty monitoring and special rapporteurs. "
            "Recognised as authoritative under CSDDD and LkSG."
        ),
    ),
    # ── Medium credibility — established institutions, multi-source aggregators ─
    "unicef": CredibilityProfile(
        level="Medium",
        reason=(
            "UNICEF — UN children's fund with established research methodology. "
            "Data covers child labour and child rights violations. "
            "Credible but may not reflect real-time conditions; verify against current reports."
        ),
    ),
    "fragile_states_index": CredibilityProfile(
        level="Medium",
        reason=(
            "Fragile States Index (Fund for Peace) — established NGO index. "
            "Composite of 12 social, economic, and political indicators. "
            "Methodology is documented; data updated annually."
        ),
    ),
    "sector_esg_benchmark": CredibilityProfile(
        level="Medium",
        reason=(
            "EIOS internal sector ESG benchmark — derived from aggregated assessment data. "
            "Based on CSDDD Annex I risk register and NACE sector classification. "
            "Deterministic and reproducible; limited to data in the EIOS system."
        ),
    ),
    "sector_risk_classification": CredibilityProfile(
        level="Medium",
        reason=(
            "EIOS sector risk classification — internal CSDDD Annex I risk matrix. "
            "Based on ILO/OECD source data; calibrated offline via RAG pipeline. "
            "Deterministic scoring; review base matrix for methodology details."
        ),
    ),
    "climate_vulnerability": CredibilityProfile(
        level="Medium",
        reason=(
            "Climate vulnerability index — composite of published climate risk datasets. "
            "Based on ND-GAIN and similar peer-reviewed sources. "
            "Methodology varies by underlying dataset; treat as indicative."
        ),
    ),
    "water_stress": CredibilityProfile(
        level="Medium",
        reason=(
            "Water stress data — based on WRI Aqueduct or equivalent published datasets. "
            "Methodology is documented; data updated periodically. "
            "Physical risk indicator; verify against local assessments for procurement decisions."
        ),
    ),
    "biodiversity_risk": CredibilityProfile(
        level="Medium",
        reason=(
            "Biodiversity risk index — derived from IBAT or equivalent datasets. "
            "Covers proximity to protected areas and biodiversity hotspots. "
            "Indicative risk; site-level assessment recommended for high-risk locations."
        ),
    ),
    # ── Low credibility — media aggregators, single sources ──────────────────
    "gdelt_news": CredibilityProfile(
        level="Low",
        reason=(
            "GDELT Project — automated news aggregator covering 65+ languages. "
            "Individual articles may be unverified, editorial, or sensational. "
            "Use as early-warning signal only; independent corroboration required before action."
        ),
    ),
    "gdelt": CredibilityProfile(
        level="Low",
        reason=(
            "GDELT Project — automated news aggregator covering 65+ languages. "
            "Individual articles may be unverified, editorial, or sensational. "
            "Use as early-warning signal only; independent corroboration required before action."
        ),
    ),
    "sector_incident_statistics": CredibilityProfile(
        level="Low",
        reason=(
            "Sector incident statistics — aggregated from media and NGO reports. "
            "Statistical estimates with uncertainty; not linked to specific verified incidents. "
            "Use for sector-level risk prioritisation only."
        ),
    ),
}

_DEFAULT = CredibilityProfile(
    level="Low",
    reason=(
        "Source not in EIOS credibility registry — treat as unverified. "
        "No formal assessment of data quality or editorial oversight available."
    ),
)


def get_credibility(source_name: str) -> CredibilityProfile:
    """Return the credibility profile for a given source_name.

    Always returns a profile — never raises. Unknown sources return Low/unverified.
    """
    return _CREDIBILITY_MATRIX.get(source_name, _DEFAULT)


def credibility_badge_class(level: str) -> str:
    """CSS hint for frontend — not used by backend but useful as contract."""
    return {"High": "emerald", "Medium": "amber", "Low": "red"}.get(level, "slate")
