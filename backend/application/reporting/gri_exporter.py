"""M47.1 G-037 — GRI Report Export (JSON + CSV).

Maps EIOS disclosure responses to GRI Standards 2021 disclosures.

Supported GRI Standards (subset — production would cover all active standards):
  GRI 301: Materials
  GRI 302: Energy
  GRI 303: Water and Effluents
  GRI 305: Emissions (Scope 1/2/3)
  GRI 306: Waste
  GRI 401: Employment (headcount, turnover)
  GRI 405: Diversity and Equal Opportunity (gender pay gap, board diversity)
  GRI 2:   General Disclosures (org profile, governance, stakeholder engagement)

Output:
  - JSON: machine-readable, structured by GRI standard + disclosure
  - CSV: flat table with [standard_code, disclosure_id, title, value, narrative, status]
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any


@dataclass
class GRIDisclosure:
    standard_code: str  # e.g. "GRI 305"
    disclosure_id: str  # e.g. "305-1"
    title: str  # e.g. "Direct (Scope 1) GHG emissions"
    value: str | None  # quantitative value as string
    unit: str | None  # e.g. "tCO2e"
    narrative: str  # qualitative explanation
    status: str  # reported | partial | omitted
    omission_reason: str | None = None


def build_gri_report(
    *,
    organization_name: str,
    reporting_year: int,
    disclosures: list[dict[str, Any]],
    emissions: dict[str, Any] | None = None,
    workforce: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured GRI report dict.

    Args:
        organization_name: Legal entity name.
        reporting_year: Calendar year.
        disclosures: List of {requirement_code, narrative_text, disclosure_status}
                     from DisclosureResponseModel.
        emissions: Optional {scope1, scope2_market, scope3, energy_mwh}.
        workforce: Optional {headcount, turnover_pct, female_pct, pay_gap_pct}.

    Returns:
        Dict with keys: metadata, standards, disclosures_by_standard, summary.
    """
    items: list[GRIDisclosure] = []

    # ── GRI 2: General Disclosures ────────────────────────────────────────────
    items.append(
        GRIDisclosure(
            standard_code="GRI 2",
            disclosure_id="2-1",
            title="Organizational details",
            value=None,
            unit=None,
            narrative=f"Reporting organization: {organization_name}",
            status="reported",
        )
    )

    # ── GRI 305: Emissions ────────────────────────────────────────────────────
    if emissions:
        items.extend(
            [
                GRIDisclosure(
                    "GRI 305",
                    "305-1",
                    "Direct (Scope 1) GHG emissions",
                    str(emissions.get("scope1")) if emissions.get("scope1") is not None else None,
                    "tCO2e",
                    "Gross Scope 1 GHG emissions as calculated using GHG Protocol methodology.",
                    "reported" if emissions.get("scope1") is not None else "omitted",
                    None if emissions.get("scope1") is not None else "Data not yet measured",
                ),
                GRIDisclosure(
                    "GRI 305",
                    "305-2",
                    "Energy indirect (Scope 2) GHG emissions",
                    str(emissions.get("scope2_market"))
                    if emissions.get("scope2_market") is not None
                    else None,
                    "tCO2e",
                    "Market-based Scope 2 GHG emissions.",
                    "reported" if emissions.get("scope2_market") is not None else "omitted",
                    None if emissions.get("scope2_market") is not None else "Data not yet measured",
                ),
                GRIDisclosure(
                    "GRI 305",
                    "305-3",
                    "Other indirect (Scope 3) GHG emissions",
                    str(emissions.get("scope3")) if emissions.get("scope3") is not None else None,
                    "tCO2e",
                    "Scope 3 GHG emissions across applicable categories.",
                    "reported" if emissions.get("scope3") is not None else "partial",
                    None
                    if emissions.get("scope3") is not None
                    else "Not all Scope 3 categories measured",
                ),
            ]
        )

    # ── GRI 302: Energy ───────────────────────────────────────────────────────
    if emissions and emissions.get("energy_mwh") is not None:
        items.append(
            GRIDisclosure(
                "GRI 302",
                "302-1",
                "Energy consumption within the organization",
                str(emissions["energy_mwh"]),
                "MWh",
                "Total energy consumption from all sources.",
                "reported",
            )
        )

    # ── GRI 401/405: Workforce ────────────────────────────────────────────────
    if workforce:
        items.extend(
            [
                GRIDisclosure(
                    "GRI 401",
                    "401-1",
                    "New employee hires and employee turnover",
                    str(workforce.get("turnover_pct"))
                    if workforce.get("turnover_pct") is not None
                    else None,
                    "%",
                    "Annual employee turnover rate.",
                    "reported" if workforce.get("turnover_pct") is not None else "omitted",
                ),
                GRIDisclosure(
                    "GRI 405",
                    "405-2",
                    "Ratio of basic salary and remuneration of women to men",
                    str(workforce.get("pay_gap_pct"))
                    if workforce.get("pay_gap_pct") is not None
                    else None,
                    "%",
                    "Gender pay gap as percentage difference in median remuneration.",
                    "reported" if workforce.get("pay_gap_pct") is not None else "omitted",
                ),
            ]
        )

    # Map disclosure responses from EIOS framework to GRI
    for resp in disclosures:
        code = resp.get("requirement_code", "")
        if code.startswith("ESRS-E1") or code.startswith("GRI 305"):
            # Already covered above — skip duplicate
            continue
        items.append(
            GRIDisclosure(
                standard_code="GRI 2",
                disclosure_id=code or "custom",
                title=resp.get("title", "Custom disclosure"),
                value=None,
                unit=None,
                narrative=resp.get("narrative_text", ""),
                status=_map_status(resp.get("disclosure_status", "Not Started")),
            )
        )

    # Group by standard
    by_standard: dict[str, list[dict]] = {}
    for item in items:
        by_standard.setdefault(item.standard_code, []).append(
            {
                "disclosure_id": item.disclosure_id,
                "title": item.title,
                "value": item.value,
                "unit": item.unit,
                "narrative": item.narrative,
                "status": item.status,
                "omission_reason": item.omission_reason,
            }
        )

    reported = sum(1 for i in items if i.status == "reported")
    total = len(items)

    return {
        "metadata": {
            "organization": organization_name,
            "reporting_year": reporting_year,
            "framework": "GRI Standards 2021",
            "generator": "EIOS GRI Exporter 1.0",
        },
        "summary": {
            "total_disclosures": total,
            "reported": reported,
            "partial": sum(1 for i in items if i.status == "partial"),
            "omitted": sum(1 for i in items if i.status == "omitted"),
            "completeness_pct": round(reported / total * 100, 1) if total else 0,
        },
        "disclosures_by_standard": by_standard,
    }


def build_gri_csv(report: dict[str, Any]) -> str:
    """Convert a GRI report dict to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "standard_code",
            "disclosure_id",
            "title",
            "value",
            "unit",
            "status",
            "omission_reason",
            "narrative",
        ]
    )
    for standard, disclosures in report.get("disclosures_by_standard", {}).items():
        for d in disclosures:
            writer.writerow(
                [
                    standard,
                    d["disclosure_id"],
                    d["title"],
                    d["value"] or "",
                    d["unit"] or "",
                    d["status"],
                    d["omission_reason"] or "",
                    d["narrative"][:500] if d["narrative"] else "",
                ]
            )
    return output.getvalue()


def _map_status(eios_status: str) -> str:
    mapping = {
        "Completed": "reported",
        "In Progress": "partial",
        "Not Started": "omitted",
        "Approved": "reported",
        "Submitted": "partial",
    }
    return mapping.get(eios_status, "omitted")
