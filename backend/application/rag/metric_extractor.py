"""Metric Extractor — extrahiert strukturierte Kennzahlen und Signale aus Dokumenten.

Wird nach document_analyzer.py aufgerufen und befüllt:
  - company_metrics: quantitative Zeitreihen (Umsatz, CO2, Mitarbeiter, ...)
  - company_signals: qualitative Ereignisse (Commitments, Ziele, Warnungen, ...)
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.company_intelligence import (
    CompanyMetricModel,
    CompanySignalModel,
)

logger = structlog.get_logger(__name__)

# Per-batch limits (tuned for Groq free-tier: ~6,000 TPM, ~2,500 tokens/call for content)
# When ANTHROPIC_API_KEY is set, Haiku handles 200k tokens so these limits are conservative.
_CHARS_PER_CALL = 10_000   # ~2,500 tokens of content per LLM call
_CHUNKS_PER_CALL = 1       # one parent chunk (1,500w ≈ 10k chars) per call
_MAX_CALLS = 20            # process first 20 parent chunks per document

# ── LLM Helper ────────────────────────────────────────────────────────────────

async def _call_llm(system: str, prompt: str) -> str:
    from infrastructure.llm.deps import get_extraction_llm_provider
    from application.ports.llm import Message
    llm = get_extraction_llm_provider()
    for attempt in range(4):
        try:
            response = await llm.complete(
                messages=[Message(role="user", content=prompt)],
                system=system,
                max_tokens=4096,
                temperature=0.0,
            )
            raw = response.content.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return raw
        except Exception as exc:
            err = str(exc)
            if ("429" in err or "rate_limit_exceeded" in err) and attempt < 3:
                wait_match = re.search(r"try again in (\d+(?:\.\d+)?)s", err)
                wait = float(wait_match.group(1)) + 5.0 if wait_match else 30.0
                logger.warning("metric_extractor.rate_limit", attempt=attempt + 1, wait_s=round(wait, 1))
                await asyncio.sleep(wait)
                continue
            raise
    return "{}"


def _parse_json(raw: str) -> dict | list:
    try:
        return json.loads(raw)
    except Exception:
        return {}


# ── Finanz-Extraktor ──────────────────────────────────────────────────────────

_FINANCIAL_SYSTEM = """You are a financial data extraction specialist. Extract key financial metrics from the document text.

Return ONLY valid JSON:
{
  "metrics": [
    {
      "metric_type": "revenue",
      "value": 142385,
      "unit": "EUR_M",
      "year": 2024,
      "period": "FY",
      "confidence": "exact"
    }
  ],
  "signals": [
    {
      "signal_type": "guidance_issued",
      "dimension": "financial",
      "direction": "positive",
      "severity": "medium",
      "description": "BMW issues revenue guidance of EUR 150B for 2025",
      "year": 2024
    }
  ]
}

metric_type values: revenue, ebitda, ebitda_margin, net_income, employees, capex, free_cashflow, debt_ratio, roce, eps
unit values: EUR_M (millions), EUR_B (billions), PCT (percent), COUNT (headcount), EUR (absolute)
confidence: exact (stated explicitly), estimated (derived/calculated)
period: FY, Q1, Q2, Q3, Q4, H1, H2
signal_type: guidance_issued, profit_warning, dividend_change, restructuring, acquisition, rating_change
direction: positive, negative, neutral
severity: critical, high, medium, low

Extract ALL years present in the document (multi-year data common in annual reports).
Return [] for metrics/signals if nothing found. Never invent data."""


async def _extract_financial(chunks: list[str], company: str, year: int | None, system: str | None = None) -> dict:
    context = "\n\n---\n\n".join(chunks[:_CHUNKS_PER_CALL])[:_CHARS_PER_CALL]
    prompt = f"Company: {company}\nReport year: {year or 'unknown'}\n\nDocument text:\n{context}"
    raw = await _call_llm(system or _FINANCIAL_SYSTEM, prompt)
    return _parse_json(raw)


# ── ESG-Extraktor ─────────────────────────────────────────────────────────────

_ESG_SYSTEM = """You are an ESG data extraction specialist. Extract sustainability metrics and targets from the document.

Return ONLY valid JSON:
{
  "metrics": [
    {
      "metric_type": "co2_scope1",
      "value": 1850000,
      "unit": "tCO2",
      "year": 2024,
      "period": "FY",
      "confidence": "exact"
    }
  ],
  "signals": [
    {
      "signal_type": "esg_target_set",
      "dimension": "esg",
      "direction": "positive",
      "severity": "medium",
      "description": "BMW commits to carbon neutrality across entire value chain by 2050",
      "year": 2024
    }
  ]
}

metric_type values:
  co2_scope1, co2_scope2, co2_scope3 (tCO2 or tCO2_M)
  water_m3 (cubic meters), energy_gwh (GWh), renewable_energy_pct (%)
  women_leadership_pct (%), supplier_audited_pct (%), employees_total (COUNT)
  esg_score (0-100 scale), lost_time_injury_rate (per 1M hours)

signal_type: esg_target_set, esg_target_reached, esg_target_missed, certification_received,
             supply_chain_audit, human_rights_issue, environmental_incident, climate_commitment

Extract ALL years present. Return [] if nothing found. Never invent data."""


async def _extract_esg(chunks: list[str], company: str, year: int | None, system: str | None = None) -> dict:
    context = "\n\n---\n\n".join(chunks[:_CHUNKS_PER_CALL])[:_CHARS_PER_CALL]
    prompt = f"Company: {company}\nReport year: {year or 'unknown'}\n\nDocument text:\n{context}"
    raw = await _call_llm(system or _ESG_SYSTEM, prompt)
    return _parse_json(raw)


# ── Statement-Extraktor ───────────────────────────────────────────────────────

_STATEMENT_SYSTEM = """You are an analyst extracting strategic signals from corporate communications.

Return ONLY valid JSON:
{
  "metrics": [],
  "signals": [
    {
      "signal_type": "commitment",
      "dimension": "esg",
      "direction": "positive",
      "severity": "high",
      "description": "CEO commits to doubling EV sales by 2026 and reducing CO2 30% by 2030",
      "year": 2026
    }
  ]
}

signal_type: commitment, strategic_priority, warning, outlook_positive, outlook_negative,
             management_change, market_positioning, innovation_announcement
dimension: financial, esg, governance, supply_chain, regulatory, reputation
direction: positive, negative, neutral
severity: critical, high, medium, low

Focus on concrete commitments, forward-looking statements, and strategic decisions.
Return [] for metrics (statements rarely contain verified metrics). Never invent data."""


async def _extract_statement(chunks: list[str], company: str, year: int | None, system: str | None = None) -> dict:
    context = "\n\n---\n\n".join(chunks[:_CHUNKS_PER_CALL])[:_CHARS_PER_CALL]
    prompt = f"Company: {company}\nYear: {year or 'unknown'}\n\nDocument text:\n{context}"
    raw = await _call_llm(system or _STATEMENT_SYSTEM, prompt)
    return _parse_json(raw)


# ── Signal-Extraktor ──────────────────────────────────────────────────────────

_SIGNAL_SYSTEM = """You are an analyst extracting risk signals from external documents (ratings, NGO reports, news).

Return ONLY valid JSON:
{
  "metrics": [],
  "signals": [
    {
      "signal_type": "rating_downgrade",
      "dimension": "financial",
      "direction": "negative",
      "severity": "high",
      "description": "Moody's downgrades BMW to Baa1 citing EV transition risks",
      "year": 2024
    }
  ]
}

signal_type: rating_upgrade, rating_downgrade, legal_action, regulatory_fine, product_recall,
             insolvency_risk, acquisition_target, esg_controversy, supply_chain_disruption,
             market_share_loss, cybersecurity_incident, labor_dispute
dimension: financial, esg, governance, supply_chain, regulatory, reputation
direction: positive, negative, neutral
severity: critical, high, medium, low

Return [] for metrics. Never invent data."""


async def _extract_signal(chunks: list[str], company: str, year: int | None, system: str | None = None) -> dict:
    context = "\n\n---\n\n".join(chunks[:_CHUNKS_PER_CALL])[:_CHARS_PER_CALL]
    prompt = f"Company: {company}\nYear: {year or 'unknown'}\n\nDocument text:\n{context}"
    raw = await _call_llm(system or _SIGNAL_SYSTEM, prompt)
    return _parse_json(raw)


# ── Batch Dispatcher ─────────────────────────────────────────────────────────

async def _run_batched(
    extract_fn,
    chunks: list[str],
    company: str,
    year: int | None,
    system: str | None = None,
) -> dict:
    """Run extract_fn over all chunks in sliding batches, deduplicate results.

    Processes up to _MAX_CALLS × _CHUNKS_PER_CALL chunks per document so that
    financial tables spread across later pages of an annual report are not missed.
    Metrics are deduplicated by (metric_type, year, period); signals are kept all.
    """
    seen_metric_keys: set[tuple] = set()
    all_metrics: list[dict] = []
    all_signals: list[dict] = []

    calls = 0
    for start in range(0, len(chunks), _CHUNKS_PER_CALL):
        if calls >= _MAX_CALLS:
            break
        batch = chunks[start : start + _CHUNKS_PER_CALL]
        result = await extract_fn(batch, company, year, system)
        calls += 1

        for m in result.get("metrics") or []:
            mt = m.get("metric_type")
            yr = int(m.get("year") or 0)
            pd = m.get("period", "FY")
            key = (mt, yr, pd)
            if mt and yr > 1990 and key not in seen_metric_keys:
                seen_metric_keys.add(key)
                all_metrics.append(m)

        all_signals.extend(result.get("signals") or [])

    logger.debug(
        "metric_extractor.batched",
        calls=calls,
        total_chunks=len(chunks),
        metrics_found=len(all_metrics),
    )
    return {"metrics": all_metrics, "signals": all_signals}


# ── Haupt-Extraktor ───────────────────────────────────────────────────────────

_PROMPT_NAMES: dict[str, str] = {
    "financial": "financial_extraction_system",
    "esg": "esg_extraction_system",
    "statement": "statement_extraction_system",
    "signal": "signal_extraction_system",
    "regulatory": "signal_extraction_system",
}

_PROMPT_FALLBACKS: dict[str, str] = {
    "financial_extraction_system": _FINANCIAL_SYSTEM,
    "esg_extraction_system": _ESG_SYSTEM,
    "statement_extraction_system": _STATEMENT_SYSTEM,
    "signal_extraction_system": _SIGNAL_SYSTEM,
}

_EXTRACT_FNS = {
    "financial": _extract_financial,
    "esg": _extract_esg,
    "statement": _extract_statement,
    "signal": _extract_signal,
    "regulatory": _extract_signal,
}


async def extract_and_store_intelligence(
    organization_id: str,
    doc_file_id: str,
    doc_class: str,
    company_name: str | None,
    supplier_id: str | None,
    report_year: int | None,
    chunks: list[str],
    session: AsyncSession,
) -> dict:
    """Extract metrics + signals from document chunks and persist them."""
    if not company_name or not chunks:
        return {"metrics": 0, "signals": 0, "skipped": True}

    extract_fn = _EXTRACT_FNS.get(doc_class)
    if extract_fn is None:
        return {"metrics": 0, "signals": 0, "skipped": True}

    company = company_name

    # ADR-011: load active prompt from DB, fall back to hardcoded default
    prompt_name = _PROMPT_NAMES[doc_class]
    prompt_version_num: int | None = None
    try:
        from application.prompt_registry import PromptRegistry
        registry = PromptRegistry(session)
        pv = await registry.get_active(prompt_name)
        if pv:
            # Patch the module-level system string for this extraction run
            _PROMPT_FALLBACKS[prompt_name] = pv.template
            prompt_version_num = pv.version
            logger.debug(
                "metric_extractor.prompt_loaded",
                prompt_name=prompt_name,
                version=pv.version,
            )
    except Exception:
        pass  # Registry unavailable — hardcoded fallback still active

    logger.info(
        "metric_extractor.prompt_version",
        prompt_name=prompt_name,
        version=prompt_version_num,
        doc_class=doc_class,
        company=company_name,
    )

    # Dispatch to class-specific extractor (always batched — covers full document)
    resolved_system = _PROMPT_FALLBACKS.get(prompt_name)
    result = await _run_batched(extract_fn, chunks, company, report_year, system=resolved_system)

    raw_metrics: list[dict] = result.get("metrics") if isinstance(result, dict) else []
    raw_signals: list[dict] = result.get("signals") if isinstance(result, dict) else []
    if not isinstance(raw_metrics, list):
        raw_metrics = []
    if not isinstance(raw_signals, list):
        raw_signals = []

    now = datetime.now(UTC)
    metrics_saved = 0
    signals_saved = 0

    # ── Save metrics (upsert via unique constraint) ────────────────────────────
    for m in raw_metrics:
        try:
            metric_type = str(m.get("metric_type", ""))[:64]
            value = float(m.get("value", 0))
            unit = str(m.get("unit", ""))[:32]
            year = int(m.get("year") or report_year or 0)
            period = str(m.get("period", "FY"))[:8]
            confidence = str(m.get("confidence", "exact"))[:16]

            if not metric_type or not unit or year < 1990:
                continue

            # Check for existing record (upsert)
            existing = (await session.execute(
                select(CompanyMetricModel).where(
                    CompanyMetricModel.organization_id == organization_id,
                    CompanyMetricModel.company_name == company,
                    CompanyMetricModel.metric_type == metric_type,
                    CompanyMetricModel.year == year,
                    CompanyMetricModel.period == period,
                )
            )).scalar_one_or_none()

            if existing:
                existing.value = value
                existing.unit = unit
                existing.confidence = confidence
                existing.source_doc_id = doc_file_id
            else:
                session.add(CompanyMetricModel(
                    id=str(uuid.uuid4()),
                    organization_id=organization_id,
                    company_name=company,
                    supplier_id=supplier_id,
                    metric_type=metric_type,
                    value=value,
                    unit=unit,
                    year=year,
                    period=period,
                    source_doc_id=doc_file_id,
                    confidence=confidence,
                    created_at=now,
                ))
            metrics_saved += 1
        except Exception as exc:
            logger.warning("metric_extractor.metric_skip", error=str(exc), metric=m)

    # ── Save signals ──────────────────────────────────────────────────────────
    for s in raw_signals:
        try:
            signal_type = str(s.get("signal_type", ""))[:64]
            dimension = str(s.get("dimension", "reputation"))[:32]
            direction = str(s.get("direction", "neutral"))[:16]
            severity = str(s.get("severity", "medium"))[:16]
            description = str(s.get("description", ""))
            year = s.get("year") or report_year
            year = int(year) if year else None

            if not signal_type or not description:
                continue

            session.add(CompanySignalModel(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                company_name=company,
                supplier_id=supplier_id,
                signal_type=signal_type,
                dimension=dimension,
                direction=direction,
                severity=severity,
                description=description[:2000],
                year=year,
                source_doc_id=doc_file_id,
                created_at=now,
            ))
            signals_saved += 1
        except Exception as exc:
            logger.warning("metric_extractor.signal_skip", error=str(exc), signal=s)

    await session.flush()

    logger.info(
        "metric_extractor.done",
        doc_file_id=doc_file_id,
        doc_class=doc_class,
        company=company,
        year=report_year,
        metrics=metrics_saved,
        signals=signals_saved,
    )
    return {"metrics": metrics_saved, "signals": signals_saved}
