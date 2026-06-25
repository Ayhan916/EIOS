"""M47.1 G-039 — SFDR PAI (Principal Adverse Impact) Calculator.

Implements the 14 mandatory PAIs from SFDR Annex I (as of RTS 2022/1288).
Two opt-in PAIs from the additional indicators list are also included.

PAI data is sourced from EIOS entities where available:
  - GHG emissions → GHGCalculationModel (Scope 1/2/3)
  - Workforce metrics → SustainabilityObjectiveModel + ESGKPIModel
  - Governance → DisclosureResponseModel (ESRS-G1 responses)

When data is not available, the PAI is reported with:
  data_available: false
  value: null
  explanation: "Data not yet collected for this indicator."

This meets the SFDR transparency requirement (must disclose WHY data is missing,
not just omit the indicator).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PAIIndicator:
    """A single SFDR PAI entry."""

    indicator_number: int          # 1–14 mandatory; 15–16 opt-in
    category: str                  # Climate | Social | Governance | Additional
    name: str
    metric: str                    # What is measured
    unit: str
    value: float | None            # None = data not available
    data_available: bool
    explanation: str               # Methodology or reason for data gap
    is_mandatory: bool = True


def calculate_pai(
    *,
    organization_name: str,
    reference_period_start: str,
    reference_period_end: str,
    # Climate inputs
    scope1_tco2e: float | None = None,
    scope2_tco2e: float | None = None,
    scope3_tco2e: float | None = None,
    enterprise_value_eur: float | None = None,
    revenue_eur: float | None = None,
    fossil_fuel_exposure_pct: float | None = None,
    non_renewable_energy_pct: float | None = None,
    energy_intensity_mwh_per_meur: float | None = None,
    biodiversity_sensitive_exposure: bool | None = None,
    water_emissions_tonnes: float | None = None,
    # Social inputs
    ungc_violations: int | None = None,
    no_ungc_compliance_process: bool | None = None,
    gender_pay_gap_pct: float | None = None,
    board_female_pct: float | None = None,
    controversial_weapons_exposure: bool | None = None,
    # Governance inputs
    bribery_convictions: int | None = None,
    # Opt-in
    water_usage_m3: float | None = None,
    waste_tonnes: float | None = None,
) -> dict[str, Any]:
    """Calculate all SFDR PAIs and return a structured report.

    Returns:
        dict with: metadata, mandatory_pais, optional_pais, summary.
    """
    # ── PAI 1: GHG Emissions ──────────────────────────────────────────────────
    total_ghg = _sum_optional(scope1_tco2e, scope2_tco2e, scope3_tco2e)
    # Carbon footprint = Total GHG / Enterprise Value * 1M (per SFDR formula)
    carbon_footprint = (
        round(total_ghg / enterprise_value_eur * 1_000_000, 4)
        if total_ghg is not None and enterprise_value_eur
        else None
    )
    # GHG intensity = Total GHG / Revenue * 1M
    ghg_intensity = (
        round(total_ghg / revenue_eur * 1_000_000, 4)
        if total_ghg is not None and revenue_eur
        else None
    )

    mandatory: list[PAIIndicator] = [
        PAIIndicator(1, "Climate", "GHG emissions",
                     "Scope 1 + 2 + 3 GHG emissions of investee companies", "tCO2e",
                     total_ghg, total_ghg is not None,
                     "Calculated from GHG Protocol Scope 1/2/3 data." if total_ghg is not None
                     else "Scope 3 data partially unavailable."),
        PAIIndicator(2, "Climate", "Carbon footprint",
                     "Carbon footprint relative to enterprise value (€M)", "tCO2e/€M",
                     carbon_footprint, carbon_footprint is not None,
                     "Calculated as total GHG / enterprise value * 1M." if carbon_footprint is not None
                     else "Enterprise value not provided."),
        PAIIndicator(3, "Climate", "GHG intensity of investee companies",
                     "GHG per unit of revenue (€M)", "tCO2e/€M revenue",
                     ghg_intensity, ghg_intensity is not None,
                     "Calculated as total GHG / revenue * 1M." if ghg_intensity is not None
                     else "Revenue data not provided."),
        PAIIndicator(4, "Climate", "Exposure to companies in the fossil fuel sector",
                     "Portfolio share invested in fossil fuel companies", "%",
                     fossil_fuel_exposure_pct, fossil_fuel_exposure_pct is not None,
                     "Measured against IEA/SBTi fossil fuel classification." if fossil_fuel_exposure_pct is not None
                     else "Fossil fuel exposure screening not yet completed."),
        PAIIndicator(5, "Climate", "Share of non-renewable energy consumption and production",
                     "% of energy from non-renewable sources", "%",
                     non_renewable_energy_pct, non_renewable_energy_pct is not None,
                     "Derived from energy consumption data." if non_renewable_energy_pct is not None
                     else "Energy mix data not yet collected."),
        PAIIndicator(6, "Climate", "Energy consumption intensity per high-impact climate sector",
                     "MWh per €M revenue in high-impact sectors", "MWh/€M",
                     energy_intensity_mwh_per_meur, energy_intensity_mwh_per_meur is not None,
                     "High-impact sectors per NACE Rev.2 classification." if energy_intensity_mwh_per_meur is not None
                     else "Sector-level energy data not available."),
        PAIIndicator(7, "Environment", "Activities negatively affecting biodiversity-sensitive areas",
                     "Whether investee has operations in/near protected areas", "boolean",
                     (1.0 if biodiversity_sensitive_exposure else 0.0) if biodiversity_sensitive_exposure is not None else None,
                     biodiversity_sensitive_exposure is not None,
                     "Assessed against WDPA/RAMSAR protected area databases." if biodiversity_sensitive_exposure is not None
                     else "Biodiversity screening not yet completed."),
        PAIIndicator(8, "Environment", "Emissions to water",
                     "Tonnes of pollutants emitted to water bodies", "tonnes",
                     water_emissions_tonnes, water_emissions_tonnes is not None,
                     "Sum of reportable water pollutant emissions." if water_emissions_tonnes is not None
                     else "Water emissions data not yet collected."),
        PAIIndicator(9, "Social", "Violations of UN Global Compact principles and OECD Guidelines",
                     "Number of investees with confirmed UNGC violations", "count",
                     float(ungc_violations) if ungc_violations is not None else None,
                     ungc_violations is not None,
                     "Assessed via ESG controversy screening." if ungc_violations is not None
                     else "UNGC screening not completed."),
        PAIIndicator(10, "Social", "Lack of UNGC/OECD compliance processes",
                     "% of investees without compliance policies", "%",
                     (100.0 if no_ungc_compliance_process else 0.0) if no_ungc_compliance_process is not None else None,
                     no_ungc_compliance_process is not None,
                     "Based on supplier policy assessment." if no_ungc_compliance_process is not None
                     else "Policy screening not completed."),
        PAIIndicator(11, "Social", "Gender pay gap",
                     "Difference in average gross hourly earnings women vs men", "%",
                     gender_pay_gap_pct, gender_pay_gap_pct is not None,
                     "Measured per EU Directive 2023/970 methodology." if gender_pay_gap_pct is not None
                     else "Gender pay gap data not yet collected."),
        PAIIndicator(12, "Social", "Board gender diversity",
                     "% of board seats held by women", "%",
                     board_female_pct, board_female_pct is not None,
                     "Governance data from annual reporting." if board_female_pct is not None
                     else "Board composition data not collected."),
        PAIIndicator(13, "Social", "Exposure to controversial weapons",
                     "Whether portfolio includes controversial weapons manufacturers", "boolean",
                     (1.0 if controversial_weapons_exposure else 0.0) if controversial_weapons_exposure is not None else None,
                     controversial_weapons_exposure is not None,
                     "Screened against cluster munitions, landmines, bio/chem weapons exclusion lists." if controversial_weapons_exposure is not None
                     else "Controversial weapons screening not completed."),
        PAIIndicator(14, "Governance", "Exposure to companies with bribery/corruption convictions",
                     "Number of investees with confirmed violations", "count",
                     float(bribery_convictions) if bribery_convictions is not None else None,
                     bribery_convictions is not None,
                     "Sourced from public court records and ESG controversy data." if bribery_convictions is not None
                     else "Anti-corruption screening not completed."),
    ]

    # ── Opt-in PAIs ───────────────────────────────────────────────────────────
    optional: list[PAIIndicator] = [
        PAIIndicator(15, "Environment", "Water usage and recycling",
                     "Total water withdrawn (m³)", "m³",
                     water_usage_m3, water_usage_m3 is not None,
                     "Water metering data from operations." if water_usage_m3 is not None
                     else "Water metering not yet implemented.",
                     is_mandatory=False),
        PAIIndicator(16, "Environment", "Hazardous and radioactive waste",
                     "Total waste generated (tonnes)", "tonnes",
                     waste_tonnes, waste_tonnes is not None,
                     "Waste disposal records from facility management." if waste_tonnes is not None
                     else "Waste tracking not yet implemented.",
                     is_mandatory=False),
    ]

    def _pai_dict(p: PAIIndicator) -> dict:
        return {
            "indicator_number": p.indicator_number,
            "category": p.category,
            "name": p.name,
            "metric": p.metric,
            "unit": p.unit,
            "value": p.value,
            "data_available": p.data_available,
            "explanation": p.explanation,
        }

    covered = sum(1 for p in mandatory if p.data_available)
    total = len(mandatory)

    return {
        "metadata": {
            "organization": organization_name,
            "reference_period_start": reference_period_start,
            "reference_period_end": reference_period_end,
            "framework": "SFDR Annex I (RTS 2022/1288)",
            "generator": "EIOS SFDR PAI Calculator 1.0",
        },
        "mandatory_pais": [_pai_dict(p) for p in mandatory],
        "optional_pais": [_pai_dict(p) for p in optional],
        "summary": {
            "mandatory_indicators_total": total,
            "mandatory_data_available": covered,
            "mandatory_data_gaps": total - covered,
            "coverage_pct": round(covered / total * 100, 1) if total else 0,
        },
    }


def _sum_optional(*values: float | None) -> float | None:
    """Sum values; return None if ALL are None."""
    available = [v for v in values if v is not None]
    return sum(available) if available else None
