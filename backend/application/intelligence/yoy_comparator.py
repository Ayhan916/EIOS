"""Year-over-Year Comparator — vergleicht extrahierte Metriken mit dem Vorjahr.

Wird automatisch nach jeder Intelligence-Extraktion aufgerufen.
Ergebnis: CompanySignal-Einträge mit signal_type="yoy_comparison".
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.company_intelligence import (
    CompanyMetricModel,
    CompanySignalModel,
)

logger = structlog.get_logger(__name__)

_FINANCIAL = {
    "revenue", "ebitda", "ebitda_margin", "net_income", "employees",
    "employees_total", "capex", "free_cashflow", "debt_ratio", "roce", "eps",
}
_ESG = {
    "co2_scope1", "co2_scope2", "co2_scope3", "water_m3", "energy_gwh",
    "renewable_energy_pct", "women_leadership_pct", "supplier_audited_pct",
    "esg_score", "lost_time_injury_rate",
}
_HIGHER_BETTER = {
    "revenue", "ebitda", "ebitda_margin", "net_income", "free_cashflow",
    "renewable_energy_pct", "women_leadership_pct", "supplier_audited_pct",
    "esg_score", "roce", "eps",
}
_LOWER_BETTER = {
    "co2_scope1", "co2_scope2", "co2_scope3",
    "water_m3", "debt_ratio", "lost_time_injury_rate",
}

_METRIC_LABELS = {
    "revenue": "Umsatz", "ebitda": "EBITDA", "ebitda_margin": "EBITDA-Marge",
    "net_income": "Jahresüberschuss", "employees": "Mitarbeiter",
    "employees_total": "Mitarbeiter gesamt", "capex": "CapEx",
    "free_cashflow": "Free Cashflow", "debt_ratio": "Verschuldungsgrad",
    "roce": "ROCE", "eps": "EPS", "co2_scope1": "CO₂ Scope 1",
    "co2_scope2": "CO₂ Scope 2", "co2_scope3": "CO₂ Scope 3",
    "water_m3": "Wasserverbrauch", "energy_gwh": "Energieverbrauch",
    "renewable_energy_pct": "Erneuerbare Energie",
    "women_leadership_pct": "Frauen in Führung",
    "supplier_audited_pct": "Lieferanten auditiert",
    "esg_score": "ESG-Score", "lost_time_injury_rate": "Unfallrate",
}
_UNIT_LABELS = {
    "EUR_M": "Mio. €", "EUR_B": "Mrd. €", "EUR": "€",
    "PCT": "%", "%": "%", "COUNT": "", "tCO2": "tCO₂",
    "tCO2_M": "Mio. tCO₂", "GWh": "GWh", "MWh": "MWh", "m3": "m³",
}


@dataclass
class YoYChange:
    metric_type: str
    prev_year: int
    curr_year: int
    prev_value: float
    curr_value: float
    unit: str
    pct_change: float
    direction: str   # "positive" | "negative" | "neutral"
    dimension: str   # "financial" | "esg"
    severity: str    # "high" | "medium" | "low"


def _dimension(metric_type: str) -> str:
    if metric_type in _ESG:
        return "esg"
    if metric_type in _FINANCIAL:
        return "financial"
    return "financial"


def _direction(metric_type: str, pct_change: float) -> str:
    if pct_change > 0 and metric_type in _HIGHER_BETTER:
        return "positive"
    if pct_change < 0 and metric_type in _LOWER_BETTER:
        return "positive"
    if pct_change < 0 and metric_type in _HIGHER_BETTER:
        return "negative"
    if pct_change > 0 and metric_type in _LOWER_BETTER:
        return "negative"
    return "neutral"


def _severity(pct_change: float) -> str:
    abs_pct = abs(pct_change)
    if abs_pct >= 20:
        return "high"
    if abs_pct >= 5:
        return "medium"
    return "low"


def _fmt(value: float, unit: str) -> str:
    label = _UNIT_LABELS.get(unit, unit)
    if value >= 1_000_000:
        s = f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        s = f"{value / 1_000:.1f}K"
    elif value % 1 == 0:
        s = f"{value:,.0f}".replace(",", ".")
    else:
        s = f"{value:.2f}"
    return f"{s} {label}".strip()


async def generate_yoy_comparison(
    organization_id: str,
    company_name: str,
    supplier_id: str | None,
    report_year: int,
    source_doc_id: str | None,
    session: AsyncSession,
) -> dict[str, int]:
    """Vergleicht Metriken des neuen Dokuments mit dem Vorjahr.

    Löscht vorherige yoy_comparison-Signale für dieselbe Firma+Jahr
    und schreibt aktualisierte Signale.
    """
    prev_year = report_year - 1

    # Lade Metriken für aktuelles Jahr (nur FY, gleiche Firma)
    curr_rows = (await session.execute(
        select(CompanyMetricModel).where(
            CompanyMetricModel.organization_id == organization_id,
            CompanyMetricModel.company_name == company_name,
            CompanyMetricModel.year == report_year,
            CompanyMetricModel.period == "FY",
            CompanyMetricModel.confidence != "estimated",
        )
    )).scalars().all()

    if not curr_rows:
        return {"yoy_signals": 0}

    # Lade Metriken für Vorjahr (gleiche Firma, alle company_name-Varianten via ilike)
    prev_rows = (await session.execute(
        select(CompanyMetricModel).where(
            CompanyMetricModel.organization_id == organization_id,
            CompanyMetricModel.company_name.ilike(f"%{company_name.split()[0]}%"),
            CompanyMetricModel.year == prev_year,
            CompanyMetricModel.period == "FY",
            CompanyMetricModel.confidence != "estimated",
        )
    )).scalars().all()

    if not prev_rows:
        logger.info("yoy_comparator.no_prev_year", company=company_name, year=prev_year)
        return {"yoy_signals": 0}

    # Index: metric_type → best value (höchste Confidence, neueste)
    def _best(rows: list) -> dict[str, CompanyMetricModel]:
        conf_order = {"exact": 0, "high": 1, "medium": 2, "low": 3, "estimated": 4}
        idx: dict[str, CompanyMetricModel] = {}
        for r in rows:
            existing = idx.get(r.metric_type)
            if existing is None or conf_order.get(r.confidence, 9) < conf_order.get(existing.confidence, 9):
                idx[r.metric_type] = r
        return idx

    curr_idx = _best(curr_rows)
    prev_idx = _best(prev_rows)

    changes: list[YoYChange] = []
    for metric_type, curr in curr_idx.items():
        prev = prev_idx.get(metric_type)
        if prev is None:
            continue
        if curr.unit != prev.unit:
            continue  # Einheitenkonflikt — nicht vergleichbar

        v_prev = float(prev.value)
        v_curr = float(curr.value)
        if abs(v_prev) < 1e-9:
            continue

        pct = (v_curr - v_prev) / abs(v_prev) * 100.0
        if abs(pct) < 1.0:
            continue  # Unter 1% → kein Signal

        changes.append(YoYChange(
            metric_type=metric_type,
            prev_year=prev_year,
            curr_year=report_year,
            prev_value=v_prev,
            curr_value=v_curr,
            unit=curr.unit,
            pct_change=round(pct, 1),
            direction=_direction(metric_type, pct),
            dimension=_dimension(metric_type),
            severity=_severity(pct),
        ))

    if not changes:
        return {"yoy_signals": 0}

    # Alte yoy_comparison-Signale für diese Firma+Jahr löschen (Re-Run)
    await session.execute(
        delete(CompanySignalModel).where(
            CompanySignalModel.organization_id == organization_id,
            CompanySignalModel.company_name == company_name,
            CompanySignalModel.year == report_year,
            CompanySignalModel.signal_type == "yoy_comparison",
        )
    )

    # Neue Signale schreiben
    for c in changes:
        label = _METRIC_LABELS.get(c.metric_type, c.metric_type)
        sign = "+" if c.pct_change > 0 else ""
        description = (
            f"{label}: {_fmt(c.prev_value, c.unit)} ({c.prev_year}) "
            f"→ {_fmt(c.curr_value, c.unit)} ({c.curr_year}), "
            f"{sign}{c.pct_change:.1f}%"
        )
        session.add(CompanySignalModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            company_name=company_name,
            supplier_id=supplier_id,
            signal_type="yoy_comparison",
            dimension=c.dimension,
            direction=c.direction,
            severity=c.severity,
            description=description,
            year=c.curr_year,
            source_doc_id=source_doc_id,
        ))

    logger.info(
        "yoy_comparator.done",
        company=company_name,
        year=report_year,
        prev_year=prev_year,
        signals=len(changes),
    )
    return {"yoy_signals": len(changes)}
