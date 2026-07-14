"""Metrics Retriever — queries company_metrics and company_signals for the Copilot.

Called when the user has set a company filter or asks a quantitative question.
Provides structured KPI time-series and qualitative signals as LLM context.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.company_intelligence import (
    CompanyMetricModel,
    CompanySignalModel,
)

from .base import RetrievalResult

_METRIC_LABEL: dict[str, str] = {
    "revenue": "Revenue",
    "ebitda": "EBITDA",
    "ebitda_margin": "EBITDA Margin",
    "net_income": "Net Income",
    "employees": "Employees",
    "capex": "CapEx",
    "free_cashflow": "Free Cash Flow",
    "debt_ratio": "Debt Ratio",
    "roce": "RoCE",
    "eps": "EPS",
    "co2_scope1": "CO₂ Scope 1",
    "co2_scope2": "CO₂ Scope 2",
    "co2_scope3": "CO₂ Scope 3",
    "water_m3": "Water Consumption",
    "energy_gwh": "Energy Consumption",
    "renewable_energy_pct": "Renewable Energy Share",
    "women_leadership_pct": "Women in Leadership",
    "supplier_audited_pct": "Supplier Audit Coverage",
    "esg_score": "ESG Score",
    "lost_time_injury_rate": "Lost-Time Injury Rate",
}

_UNIT_LABEL: dict[str, str] = {
    "EUR_M": "EUR million",
    "EUR_B": "EUR billion",
    "PCT": "%",
    "COUNT": "",
    "EUR": "EUR",
    "tCO2": "t CO₂",
    "tCO2_M": "Mt CO₂",
    "GWh": "GWh",
}


def _fmt(value: float, unit: str) -> str:
    unit_str = _UNIT_LABEL.get(unit, unit)
    if value == int(value):
        num = f"{int(value):,}"
    else:
        num = f"{value:,.1f}"
    return f"{num} {unit_str}".strip()


async def retrieve_metrics_context(
    org_id: str,
    session: AsyncSession,
    *,
    company_name: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    max_metrics: int = 60,
    max_signals: int = 15,
) -> RetrievalResult:
    """Query company_metrics and company_signals and format as structured context.

    Returns a RetrievalResult with:
    - KPI time-series grouped by metric type
    - Recent qualitative signals sorted by severity
    """
    retrieved_at = datetime.now(UTC).isoformat()

    # ── Metrics query ─────────────────────────────────────────────────────────
    m_stmt = (
        select(CompanyMetricModel)
        .where(CompanyMetricModel.organization_id == org_id)
        .order_by(
            CompanyMetricModel.metric_type,
            CompanyMetricModel.year.asc(),
        )
        .limit(max_metrics)
    )
    if company_name:
        m_stmt = m_stmt.where(
            CompanyMetricModel.company_name.ilike(f"%{company_name}%")
        )
    if year_from is not None:
        m_stmt = m_stmt.where(CompanyMetricModel.year >= year_from)
    if year_to is not None:
        m_stmt = m_stmt.where(CompanyMetricModel.year <= year_to)

    metrics = (await session.execute(m_stmt)).scalars().all()

    # ── Signals query ─────────────────────────────────────────────────────────
    _SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    s_stmt = (
        select(CompanySignalModel)
        .where(CompanySignalModel.organization_id == org_id)
        .order_by(CompanySignalModel.year.desc())
        .limit(max_signals * 4)  # fetch more, then sort/trim by severity
    )
    if company_name:
        s_stmt = s_stmt.where(
            CompanySignalModel.company_name.ilike(f"%{company_name}%")
        )
    if year_from is not None:
        s_stmt = s_stmt.where(CompanySignalModel.year >= year_from)
    if year_to is not None:
        s_stmt = s_stmt.where(CompanySignalModel.year <= year_to)

    signals_raw = (await session.execute(s_stmt)).scalars().all()
    signals = sorted(
        signals_raw,
        key=lambda s: (_SEVERITY_RANK.get(s.severity, 9), -(s.year or 0)),
    )[:max_signals]

    if not metrics and not signals:
        return RetrievalResult(
            retriever="metrics_retriever",
            provenance="Company Intelligence: no metrics/signals found for given filters",
            data=[],
            source_ids=[],
            citation_type="CompanyMetric",
            freshness_metadata=[],
        )

    # ── Format metrics as time-series lines ───────────────────────────────────
    by_type: dict[str, list[str]] = {}
    for m in metrics:
        label = _METRIC_LABEL.get(m.metric_type, m.metric_type)
        entry = f"{m.year}: {_fmt(m.value, m.unit)}"
        if m.period and m.period != "FY":
            entry = f"{m.year} {m.period}: {_fmt(m.value, m.unit)}"
        by_type.setdefault(label, []).append(entry)

    metric_lines: list[str] = []
    for label, entries in by_type.items():
        metric_lines.append(f"  {label}: {', '.join(entries)}")

    # ── Format signals ────────────────────────────────────────────────────────
    signal_lines: list[str] = []
    for s in signals:
        yr = f" ({s.year})" if s.year else ""
        direction = {"positive": "↑", "negative": "↓", "neutral": "→"}.get(s.direction or "", "")
        signal_lines.append(
            f"  [{s.severity.upper()}]{direction} {s.signal_type}{yr}: {s.description[:200]}"
        )

    # ── Assemble context block ─────────────────────────────────────────────────
    company_str = company_name or "all companies"
    year_str = ""
    if year_from or year_to:
        year_str = f" ({year_from or ''}–{year_to or ''})"

    parts: list[str] = []
    if metric_lines:
        parts.append(f"KPI Time-Series for {company_str}{year_str}:\n" + "\n".join(metric_lines))
    if signal_lines:
        parts.append(f"Qualitative Signals for {company_str}{year_str}:\n" + "\n".join(signal_lines))

    context_text = "\n\n".join(parts)
    source_ids = [str(m.id) for m in metrics[:10]] + [str(s.id) for s in signals[:5]]

    freshness_metadata = [
        {
            "object_id": str(m.id),
            "object_type": "CompanyMetric",
            "updated_at": None,
            "retrieved_at": retrieved_at,
        }
        for m in metrics[:5]
    ]

    provenance = (
        f"Company Intelligence [{company_str}{year_str}]: "
        f"{len(metrics)} KPI data points, {len(signals)} signals"
    )

    return RetrievalResult(
        retriever="metrics_retriever",
        provenance=provenance,
        data=[{"metric_count": len(metrics), "signal_count": len(signals)}],
        context_text=context_text,
        source_ids=source_ids,
        citation_type="CompanyMetric",
        freshness_metadata=freshness_metadata,
    )
