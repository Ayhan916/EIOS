"""M47.1 G-038 — TCFD Report Builder.

Structures EIOS data into the four TCFD pillars:
  1. Governance   — oversight, management role
  2. Strategy     — climate risks/opportunities, resilience
  3. Risk Mgmt    — risk identification, assessment, integration
  4. Metrics & Targets — GHG, targets, climate KPIs

Output: structured dict ready for PDF rendering or JSON export.
PDF rendering is out of scope (requires an external PDF library).
"""

from __future__ import annotations

from typing import Any


_TCFD_PILLARS = [
    {
        "code": "governance",
        "name": "Governance",
        "disclosures": [
            {"id": "a", "label": "Board oversight of climate-related risks and opportunities"},
            {"id": "b", "label": "Management's role in assessing and managing climate risks"},
        ],
    },
    {
        "code": "strategy",
        "name": "Strategy",
        "disclosures": [
            {"id": "a", "label": "Climate-related risks and opportunities over short, medium, and long term"},
            {"id": "b", "label": "Impact of climate risks on the organization's businesses, strategy, financial planning"},
            {"id": "c", "label": "Resilience of the organization's strategy under different climate scenarios"},
        ],
    },
    {
        "code": "risk_management",
        "name": "Risk Management",
        "disclosures": [
            {"id": "a", "label": "Processes for identifying and assessing climate-related risks"},
            {"id": "b", "label": "Processes for managing climate-related risks"},
            {"id": "c", "label": "Integration of climate risk processes into overall risk management"},
        ],
    },
    {
        "code": "metrics_targets",
        "name": "Metrics & Targets",
        "disclosures": [
            {"id": "a", "label": "Metrics used to assess climate-related risks and opportunities"},
            {"id": "b", "label": "Scope 1, 2, and 3 GHG emissions (where applicable)"},
            {"id": "c", "label": "Targets used to manage climate-related risks and opportunities"},
        ],
    },
]


def build_tcfd_report(
    *,
    organization_name: str,
    reporting_year: int,
    # Governance
    board_oversight_narrative: str = "",
    management_role_narrative: str = "",
    # Strategy
    climate_risks: list[dict[str, Any]] | None = None,
    scenario_analysis_narrative: str = "",
    # Risk Management
    risk_identification_narrative: str = "",
    risk_integration_narrative: str = "",
    # Metrics & Targets
    emissions: dict[str, Any] | None = None,
    climate_targets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a structured TCFD report dict.

    Args:
        climate_risks: list of {title, type (physical|transition), time_horizon, description}
        emissions: {scope1, scope2_market, scope2_location, scope3, carbon_intensity}
        climate_targets: list of {name, target_year, baseline_year, reduction_pct, progress_pct}

    Returns:
        dict with keys: metadata, pillars (list), metrics_snapshot.
    """
    pillars = []

    # ── Governance ─────────────────────────────────────────────────────────────
    pillars.append({
        "code": "governance",
        "name": "Governance",
        "disclosures": [
            {
                "id": "a",
                "label": "Board oversight of climate-related risks and opportunities",
                "narrative": board_oversight_narrative or "Not yet disclosed.",
                "status": "reported" if board_oversight_narrative else "omitted",
            },
            {
                "id": "b",
                "label": "Management's role in assessing and managing climate risks",
                "narrative": management_role_narrative or "Not yet disclosed.",
                "status": "reported" if management_role_narrative else "omitted",
            },
        ],
    })

    # ── Strategy ───────────────────────────────────────────────────────────────
    risk_table = [
        {
            "title": r.get("title", ""),
            "type": r.get("risk_type", "transition"),
            "time_horizon": r.get("time_horizon", "medium"),
            "description": r.get("description", ""),
            "financial_impact": r.get("financial_impact", "Not quantified"),
        }
        for r in (climate_risks or [])
    ]
    pillars.append({
        "code": "strategy",
        "name": "Strategy",
        "disclosures": [
            {
                "id": "a",
                "label": "Climate-related risks and opportunities",
                "risks": risk_table,
                "status": "reported" if risk_table else "partial",
            },
            {
                "id": "c",
                "label": "Scenario analysis and resilience",
                "narrative": scenario_analysis_narrative or "Scenario analysis not yet completed.",
                "status": "reported" if scenario_analysis_narrative else "partial",
            },
        ],
    })

    # ── Risk Management ────────────────────────────────────────────────────────
    pillars.append({
        "code": "risk_management",
        "name": "Risk Management",
        "disclosures": [
            {
                "id": "a",
                "label": "Risk identification and assessment process",
                "narrative": risk_identification_narrative or "Not yet disclosed.",
                "status": "reported" if risk_identification_narrative else "omitted",
            },
            {
                "id": "c",
                "label": "Integration into enterprise risk management",
                "narrative": risk_integration_narrative or "Not yet disclosed.",
                "status": "reported" if risk_integration_narrative else "omitted",
            },
        ],
    })

    # ── Metrics & Targets ─────────────────────────────────────────────────────
    ghg_snapshot = None
    if emissions:
        ghg_snapshot = {
            "scope1_tco2e": emissions.get("scope1"),
            "scope2_market_tco2e": emissions.get("scope2_market"),
            "scope2_location_tco2e": emissions.get("scope2_location"),
            "scope3_tco2e": emissions.get("scope3"),
            "carbon_intensity": emissions.get("carbon_intensity"),
        }

    target_list = [
        {
            "name": t.get("name", ""),
            "target_year": t.get("target_year"),
            "baseline_year": t.get("baseline_year"),
            "reduction_pct": t.get("reduction_pct"),
            "progress_pct": t.get("progress_pct"),
        }
        for t in (climate_targets or [])
    ]

    pillars.append({
        "code": "metrics_targets",
        "name": "Metrics & Targets",
        "disclosures": [
            {
                "id": "b",
                "label": "GHG Emissions (Scope 1/2/3)",
                "ghg_snapshot": ghg_snapshot,
                "status": "reported" if ghg_snapshot else "omitted",
            },
            {
                "id": "c",
                "label": "Climate targets and progress",
                "targets": target_list,
                "status": "reported" if target_list else "partial",
            },
        ],
    })

    # Overall completeness
    all_disclosures = [d for p in pillars for d in p["disclosures"]]
    reported = sum(1 for d in all_disclosures if d.get("status") == "reported")
    total = len(all_disclosures)

    return {
        "metadata": {
            "organization": organization_name,
            "reporting_year": reporting_year,
            "framework": "TCFD 2023",
            "generator": "EIOS TCFD Exporter 1.0",
        },
        "pillars": pillars,
        "metrics_snapshot": {
            "ghg_emissions": ghg_snapshot,
            "climate_targets_count": len(target_list),
            "climate_risks_count": len(risk_table),
        },
        "summary": {
            "total_disclosures": total,
            "reported": reported,
            "completeness_pct": round(reported / total * 100, 1) if total else 0,
        },
    }
