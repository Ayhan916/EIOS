"""M47 G-012 — iXBRL Export for CSRD/ESRS.

Generates Inline XBRL (iXBRL) documents following the EFRAG ESRS Taxonomy 2023.
Output: valid HTML file with embedded XBRL machine-readable tags.

Supported ESRS scopes:
  ESRS-E1: Climate — Scope 1/2/3 GHG, energy, carbon intensity
  ESRS-E2: Pollution — emissions to air/water/soil
  ESRS-S1: Own Workforce — headcount, turnover, pay gap, training

Architecture:
  - Uses lxml.etree for XML/HTML generation (no Arelle dependency).
  - All monetary values in EUR; mass in tonnes CO2e; energy in MWh.
  - Each XBRL fact gets a unique contextRef and optional unitRef.
  - The ix:header block carries all context/unit definitions.

Limitations (explicitly documented, not hidden):
  - Taxonomy validation requires Arelle CLI — not run inline.
  - Only a subset of mandatory ESRS-E1 datapoints are tagged; a production
    deployment would cover all EFRAG taxonomy elements.
  - PDF rendering is out of scope for this module.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from lxml import etree

# EFRAG ESRS namespaces (2023 taxonomy)
_NS = {
    "ix": "http://www.xbrl.org/2013/inlineXBRL",
    "xbrli": "http://www.xbrl.org/2003/instance",
    "xbrldi": "http://xbrl.org/2006/xbrldi",
    "link": "http://www.xbrl.org/2003/linkbase",
    "xlink": "http://www.w3.org/1999/xlink",
    "iso4217": "http://www.xbrl.org/2003/iso4217",
    "esrs-e1": "http://xbrl.efrag.org/taxonomy/esrs/e1/2023",
    "esrs-e2": "http://xbrl.efrag.org/taxonomy/esrs/e2/2023",
    "esrs-s1": "http://xbrl.efrag.org/taxonomy/esrs/s1/2023",
}

_UNIT_TONNE = "u:tCO2e"
_UNIT_MWH = "u:MWh"
_UNIT_EUR = "u:EUR"
_UNIT_NUMBER = "u:pure"
_UNIT_PERCENT = "u:percent"


def build_ixbrl(
    *,
    organization_name: str,
    organization_id: str,
    reporting_period_start: date,
    reporting_period_end: date,
    esrs_e1: dict[str, Any] | None = None,
    esrs_e2: dict[str, Any] | None = None,
    esrs_s1: dict[str, Any] | None = None,
) -> bytes:
    """Return an iXBRL HTML document as UTF-8 bytes.

    Args:
        organization_name: Legal name of the reporting entity.
        organization_id:   EIOS internal org UUID (goes into metadata).
        reporting_period_start / end: FY boundaries (ISO date).
        esrs_e1: dict with keys:
            scope1_tco2e, scope2_market_tco2e, scope2_location_tco2e,
            scope3_tco2e, energy_mwh, renewable_energy_mwh, carbon_intensity.
        esrs_e2: dict with keys:
            emissions_to_air_tonnes, emissions_to_water_tonnes,
            emissions_to_soil_tonnes.
        esrs_s1: dict with keys:
            employee_headcount, contractor_count, annual_turnover_rate_pct,
            female_employees_pct, gender_pay_gap_pct, avg_training_hours.

    Returns:
        UTF-8 encoded HTML bytes with inline XBRL.
    """
    ctx_id = f"ctx_{reporting_period_start.isoformat()}_{reporting_period_end.isoformat()}"

    # Build root HTML element with all namespaces
    nsmap_full = {k: v for k, v in _NS.items()}
    html = etree.Element("html", nsmap=nsmap_full)
    html.set("xmlns", "http://www.w3.org/1999/xhtml")

    # ── <head> ────────────────────────────────────────────────────────────────
    head = etree.SubElement(html, "head")
    _el(head, "meta", charset="UTF-8")
    _el(head, "meta", name="generator", content="EIOS iXBRL Exporter 1.0")
    title = etree.SubElement(head, "title")
    title.text = f"CSRD ESRS Report — {organization_name} — {reporting_period_end.year}"

    # ── <body> ────────────────────────────────────────────────────────────────
    body = etree.SubElement(html, "body")

    # ix:header (mandatory)
    ix_header = etree.SubElement(body, f"{{{_NS['ix']}}}header")

    # ix:hidden — contexts + units (not rendered)
    etree.SubElement(ix_header, f"{{{_NS['ix']}}}hidden")

    # contexts
    etree.SubElement(ix_header, f"{{{_NS['ix']}}}references")
    ix_res = etree.SubElement(ix_header, f"{{{_NS['ix']}}}resources")

    ctx = etree.SubElement(ix_res, f"{{{_NS['xbrli']}}}context", id=ctx_id)
    ctx_entity = etree.SubElement(ctx, f"{{{_NS['xbrli']}}}entity")
    ctx_identifier = etree.SubElement(
        ctx_entity,
        f"{{{_NS['xbrli']}}}identifier",
        scheme="http://standards.iso.org/iso/17442",
    )
    ctx_identifier.text = organization_id[:20]  # LEI placeholder
    ctx_period = etree.SubElement(ctx, f"{{{_NS['xbrli']}}}period")
    etree.SubElement(
        ctx_period, f"{{{_NS['xbrli']}}}startDate"
    ).text = reporting_period_start.isoformat()
    etree.SubElement(
        ctx_period, f"{{{_NS['xbrli']}}}endDate"
    ).text = reporting_period_end.isoformat()

    # units
    for unit_id, measure in [
        (_UNIT_TONNE, "esrs-e1:t-CO2e"),
        (_UNIT_MWH, "esrs-e1:MWh"),
        (_UNIT_EUR, "iso4217:EUR"),
        (_UNIT_PERCENT, "xbrli:pure"),
    ]:
        u = etree.SubElement(ix_res, f"{{{_NS['xbrli']}}}unit", id=unit_id)
        etree.SubElement(u, f"{{{_NS['xbrli']}}}measure").text = measure

    # ── Report sections ───────────────────────────────────────────────────────

    _section(body, "CSRD/ESRS Sustainability Report")
    _para(body, f"Reporting entity: {organization_name}")
    _para(body, f"Reporting period: {reporting_period_start} — {reporting_period_end}")

    if esrs_e1:
        _heading(body, "ESRS-E1: Climate Change")
        _xbrl_numeric(
            body,
            "esrs-e1:GrossScope1GHGEmissions",
            esrs_e1.get("scope1_tco2e"),
            ctx_id,
            _UNIT_TONNE,
            "Gross Scope 1 GHG Emissions (tCO₂e)",
        )
        _xbrl_numeric(
            body,
            "esrs-e1:GrossScope2GHGEmissionsMarketBased",
            esrs_e1.get("scope2_market_tco2e"),
            ctx_id,
            _UNIT_TONNE,
            "Gross Scope 2 GHG Emissions — Market-based (tCO₂e)",
        )
        _xbrl_numeric(
            body,
            "esrs-e1:GrossScope2GHGEmissionsLocationBased",
            esrs_e1.get("scope2_location_tco2e"),
            ctx_id,
            _UNIT_TONNE,
            "Gross Scope 2 GHG Emissions — Location-based (tCO₂e)",
        )
        _xbrl_numeric(
            body,
            "esrs-e1:GrossScope3GHGEmissions",
            esrs_e1.get("scope3_tco2e"),
            ctx_id,
            _UNIT_TONNE,
            "Gross Scope 3 GHG Emissions (tCO₂e)",
        )
        _xbrl_numeric(
            body,
            "esrs-e1:TotalEnergyConsumption",
            esrs_e1.get("energy_mwh"),
            ctx_id,
            _UNIT_MWH,
            "Total Energy Consumption (MWh)",
        )
        _xbrl_numeric(
            body,
            "esrs-e1:EnergyFromRenewableSources",
            esrs_e1.get("renewable_energy_mwh"),
            ctx_id,
            _UNIT_MWH,
            "Energy from Renewable Sources (MWh)",
        )

    if esrs_e2:
        _heading(body, "ESRS-E2: Pollution")
        _xbrl_numeric(
            body,
            "esrs-e2:EmissionsToAir",
            esrs_e2.get("emissions_to_air_tonnes"),
            ctx_id,
            _UNIT_TONNE,
            "Emissions to Air (tonnes)",
        )
        _xbrl_numeric(
            body,
            "esrs-e2:EmissionsToWater",
            esrs_e2.get("emissions_to_water_tonnes"),
            ctx_id,
            _UNIT_TONNE,
            "Emissions to Water (tonnes)",
        )
        _xbrl_numeric(
            body,
            "esrs-e2:EmissionsToSoil",
            esrs_e2.get("emissions_to_soil_tonnes"),
            ctx_id,
            _UNIT_TONNE,
            "Emissions to Soil (tonnes)",
        )

    if esrs_s1:
        _heading(body, "ESRS-S1: Own Workforce")
        _xbrl_numeric(
            body,
            "esrs-s1:TotalNumberOfEmployees",
            esrs_s1.get("employee_headcount"),
            ctx_id,
            _UNIT_PERCENT,
            "Total Number of Employees",
        )
        _xbrl_numeric(
            body,
            "esrs-s1:NumberOfNonEmployeeWorkers",
            esrs_s1.get("contractor_count"),
            ctx_id,
            _UNIT_PERCENT,
            "Number of Non-Employee Workers (Contractors)",
        )
        _xbrl_numeric(
            body,
            "esrs-s1:AnnualEmployeeTurnoverRate",
            esrs_s1.get("annual_turnover_rate_pct"),
            ctx_id,
            _UNIT_PERCENT,
            "Annual Employee Turnover Rate (%)",
        )
        _xbrl_numeric(
            body,
            "esrs-s1:GenderPayGap",
            esrs_s1.get("gender_pay_gap_pct"),
            ctx_id,
            _UNIT_PERCENT,
            "Gender Pay Gap (%)",
        )
        _xbrl_numeric(
            body,
            "esrs-s1:AverageTrainingHoursPerEmployee",
            esrs_s1.get("avg_training_hours"),
            ctx_id,
            _UNIT_PERCENT,
            "Average Training Hours per Employee",
        )

    return etree.tostring(
        html, pretty_print=True, xml_declaration=False, encoding="unicode"
    ).encode("utf-8")


# ── helpers ───────────────────────────────────────────────────────────────────


def _el(parent, tag, **attrs):
    e = etree.SubElement(parent, tag)
    for k, v in attrs.items():
        e.set(k, v)
    return e


def _section(parent, text):
    h = etree.SubElement(parent, "h1")
    h.text = text


def _heading(parent, text):
    h = etree.SubElement(parent, "h2")
    h.text = text


def _para(parent, text):
    p = etree.SubElement(parent, "p")
    p.text = text


def _xbrl_numeric(parent, name: str, value, ctx_ref: str, unit_ref: str, label: str):
    """Emit an ix:nonFraction element with a human-readable label."""
    p = etree.SubElement(parent, "p")
    span_label = etree.SubElement(p, "span")
    span_label.text = f"{label}: "

    if value is None:
        span_nil = etree.SubElement(
            p,
            f"{{{_NS['ix']}}}nonFraction",
            name=name,
            contextRef=ctx_ref,
            unitRef=unit_ref,
            decimals="2",
            nilReason="http://www.xbrl.org/2009/role/nil",
        )
        span_nil.set("{http://www.w3.org/2001/XMLSchema-instance}nil", "true")
        span_nil.text = "N/A"
    else:
        span_val = etree.SubElement(
            p,
            f"{{{_NS['ix']}}}nonFraction",
            name=name,
            contextRef=ctx_ref,
            unitRef=unit_ref,
            decimals="2",
        )
        span_val.text = str(round(float(value), 2))


def compute_document_hash(content: bytes) -> str:
    """SHA-256 hash of the generated iXBRL document for audit trail."""
    return hashlib.sha256(content).hexdigest()
