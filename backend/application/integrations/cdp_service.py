"""M48.1 G-059 — CDP Reporting Integration (Basic).

Generates a CDP-aligned response structure for the Climate Change questionnaire.
Full CDP submission requires the CDP API (enterprise tier) or manual upload to
cdp.net — this module prepares the structured data for export.

CDP Climate Change C-questionnaire (2024) mapping:
  C1:  Governance
  C2:  Risks and opportunities
  C4:  Targets and performance
  C6:  Energy
  C7:  Emissions methodology
  C8:  Emissions data (Scope 1, 2, 3)
  C10: Verification
  C11: Carbon pricing

This is a data-structure builder — no AI, deterministic, auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CDPResponse:
    module_code: str
    question_number: str
    question_text: str
    response: Any
    status: str = "complete"
    comments: str = ""


def build_cdp_climate_report(
    *,
    organization_name: str,
    reporting_year: int,
    # C1: Governance
    board_oversight: str = "",
    management_approach: str = "",
    # C4: Targets
    science_based_target: bool = False,
    net_zero_year: int | None = None,
    # C6: Energy
    total_energy_mwh: float | None = None,
    renewable_energy_mwh: float | None = None,
    # C8: Emissions
    scope1_tco2e: float | None = None,
    scope2_market_tco2e: float | None = None,
    scope2_location_tco2e: float | None = None,
    scope3_tco2e: float | None = None,
    scope3_categories: list[str] | None = None,
    # C10: Verification
    scope1_verified: bool = False,
    scope2_verified: bool = False,
    verifier_name: str | None = None,
) -> dict[str, Any]:
    """Build a CDP-aligned response package for the Climate Change questionnaire.

    Returns a structured dict ready for JSON export or manual CDP portal upload.
    """
    responses: list[dict[str, Any]] = []

    # ── C1: Governance ────────────────────────────────────────────────────────
    responses.append({
        "module": "C1",
        "question": "C1.1",
        "text": "Is there board-level oversight of climate-related issues?",
        "response": "Yes" if board_oversight else "No",
        "comments": board_oversight[:1000] if board_oversight else "",
        "status": "complete" if board_oversight else "incomplete",
    })
    responses.append({
        "module": "C1",
        "question": "C1.2",
        "text": "Provide the highest management-level position responsible for climate change.",
        "response": management_approach[:500] if management_approach else "Not defined",
        "status": "complete" if management_approach else "incomplete",
    })

    # ── C4: Targets ───────────────────────────────────────────────────────────
    responses.append({
        "module": "C4",
        "question": "C4.1",
        "text": "Did you have an emissions target that was active in the reporting year?",
        "response": "Yes" if (science_based_target or net_zero_year) else "No",
        "status": "complete",
    })
    if science_based_target:
        responses.append({
            "module": "C4",
            "question": "C4.1a",
            "text": "Is your target a Science Based Target?",
            "response": "Yes — submitted to SBTi",
            "status": "complete",
        })
    if net_zero_year:
        responses.append({
            "module": "C4",
            "question": "C4.1c",
            "text": "Net-zero target year",
            "response": str(net_zero_year),
            "status": "complete",
        })

    # ── C6: Energy ────────────────────────────────────────────────────────────
    responses.append({
        "module": "C6",
        "question": "C6.1",
        "text": "Total energy consumption (MWh)",
        "response": total_energy_mwh if total_energy_mwh is not None else "Data not available",
        "unit": "MWh",
        "status": "complete" if total_energy_mwh is not None else "data_gap",
    })
    if total_energy_mwh and renewable_energy_mwh:
        pct = round(renewable_energy_mwh / total_energy_mwh * 100, 1)
        responses.append({
            "module": "C6",
            "question": "C6.2",
            "text": "Percentage of electricity from renewable sources",
            "response": pct,
            "unit": "%",
            "status": "complete",
        })

    # ── C8: Emissions ─────────────────────────────────────────────────────────
    responses.append({
        "module": "C8",
        "question": "C8.1",
        "text": "Gross global Scope 1 emissions (tCO2e)",
        "response": scope1_tco2e if scope1_tco2e is not None else "Data not available",
        "unit": "tCO2e",
        "status": "complete" if scope1_tco2e is not None else "data_gap",
    })
    responses.append({
        "module": "C8",
        "question": "C8.2a",
        "text": "Scope 2 emissions — market-based (tCO2e)",
        "response": scope2_market_tco2e if scope2_market_tco2e is not None else "Data not available",
        "unit": "tCO2e",
        "status": "complete" if scope2_market_tco2e is not None else "data_gap",
    })
    responses.append({
        "module": "C8",
        "question": "C8.2b",
        "text": "Scope 2 emissions — location-based (tCO2e)",
        "response": scope2_location_tco2e if scope2_location_tco2e is not None else "Data not available",
        "unit": "tCO2e",
        "status": "complete" if scope2_location_tco2e is not None else "data_gap",
    })
    responses.append({
        "module": "C8",
        "question": "C8.3a",
        "text": "Gross Scope 3 emissions (tCO2e)",
        "response": scope3_tco2e if scope3_tco2e is not None else "Data not available",
        "unit": "tCO2e",
        "status": "complete" if scope3_tco2e is not None else "data_gap",
        "scope3_categories": scope3_categories or [],
    })

    # ── C10: Verification ─────────────────────────────────────────────────────
    responses.append({
        "module": "C10",
        "question": "C10.1",
        "text": "Scope 1 third-party verification",
        "response": "Verified" if scope1_verified else "Not verified",
        "verifier": verifier_name or "",
        "status": "complete",
    })
    responses.append({
        "module": "C10",
        "question": "C10.2",
        "text": "Scope 2 third-party verification",
        "response": "Verified" if scope2_verified else "Not verified",
        "verifier": verifier_name or "",
        "status": "complete",
    })

    complete = sum(1 for r in responses if r.get("status") == "complete")
    gaps = sum(1 for r in responses if r.get("status") == "data_gap")

    return {
        "metadata": {
            "organization": organization_name,
            "reporting_year": reporting_year,
            "framework": "CDP Climate Change 2024",
            "generator": "EIOS CDP Exporter 1.0",
        },
        "responses": responses,
        "summary": {
            "total_questions": len(responses),
            "complete": complete,
            "incomplete": len(responses) - complete - gaps,
            "data_gaps": gaps,
            "completion_pct": round(complete / len(responses) * 100, 1) if responses else 0,
        },
    }
