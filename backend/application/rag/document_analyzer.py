"""Document Analyzer — 5 spezialisierte LLM-Extraktoren je nach Dokumentklasse.

Klassen:
  financial   → Geschäftsberichte, Quartalsberichte, Investor Presentations
  esg         → Nachhaltigkeitsberichte, CSRD, CDP
  regulatory  → EU-Richtlinien, Gesetze, Audit-Berichte
  statement   → CEO-Statements, Press Releases, Q&A
  signal      → Ratingberichte, Gerichtsurteile, NGO-Berichte, sonstige Signale

Alle Extraktoren geben dasselbe Schema zurück (standardisiert):
  summary, doc_class, signal_dimension, signal_direction,
  risks[], targets[], commitments[], kpis{}, metrics[], references[]
"""

from __future__ import annotations

import json
import re

import structlog

from .document_classifier import get_doc_class, get_signal_dimension

logger = structlog.get_logger(__name__)

_MAX_CONTEXT_CHARS = 14_000


# ── Kontext aufbauen ──────────────────────────────────────────────────────────

def _build_context(chunks: list[str], total_pages: int) -> tuple[str, list[dict]]:
    """Select representative chunks and build numbered context for citations."""
    indices: list[int] = list(range(min(5, len(chunks))))
    if len(chunks) > 7:
        indices += [len(chunks) - 2, len(chunks) - 1]
    seen: set[int] = set()
    unique = [i for i in indices if not (i in seen or seen.add(i))]  # type: ignore

    pages_per_chunk = total_pages / max(len(chunks), 1)
    parts: list[str] = []
    meta: list[dict] = []
    for ref_num, idx in enumerate(unique, start=1):
        page_est = int(idx * pages_per_chunk) + 1
        parts.append(f"[Quelle {ref_num}] Chunk {idx + 1}, ca. Seite {page_est}:\n{chunks[idx]}")
        meta.append({"ref_num": ref_num, "chunk_index": idx, "page_estimate": page_est})

    return "\n\n---\n\n".join(parts)[:_MAX_CONTEXT_CHARS], meta


def _llm_call(system: str, prompt: str) -> dict:
    raise NotImplementedError  # replaced by async version below


async def _call_llm(system: str, prompt: str) -> str:
    import asyncio
    from infrastructure.llm.deps import get_llm_provider
    from application.ports.llm import Message
    llm = get_llm_provider()

    for attempt in range(4):
        try:
            response = await llm.complete(
                messages=[Message(role="user", content=prompt)],
                system=system,
                max_tokens=3500,
                temperature=0.0,
            )
            raw = response.content.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return raw
        except Exception as exc:
            err_str = str(exc)
            if ("429" in err_str or "rate_limit_exceeded" in err_str) and attempt < 3:
                wait_match = re.search(r"try again in (\d+(?:\.\d+)?)s", err_str)
                wait = float(wait_match.group(1)) + 2.0 if wait_match else 15.0
                logger.warning("doc_analyzer.rate_limit_retry", attempt=attempt + 1, wait_s=round(wait, 1))
                await asyncio.sleep(wait)
                continue
            raise


def _empty() -> dict:
    return {
        "summary": None,
        "doc_class": "signal",
        "signal_dimension": "reputation",
        "signal_direction": "neutral",
        "risks": [],
        "targets": [],
        "commitments": [],
        "kpis": {},
        "metrics": [],
        "references": [],
    }


def _append_bibliography(result: dict) -> dict:
    """Auto-append bibliography to summary if LLM omitted it."""
    summary: str = result.get("summary") or ""
    refs: list[dict] = result.get("references") or []
    if refs and "Literaturverzeichnis" not in summary:
        bib = ["\n\n**Literaturverzeichnis**"]
        for ref in refs:
            bib.append(f'[{ref["id"]}] Seite ~{ref.get("page_estimate", "?")}: "{ref.get("excerpt", "")}"')
        result["summary"] = summary + "\n".join(bib)
    return result


# ── 1. Financial Extractor ────────────────────────────────────────────────────

_FINANCIAL_SYSTEM = (
    "Du bist ein erfahrener Finanzanalyst und M&A-Berater. "
    "Du extrahierst strukturierte Finanzdaten aus Geschäftsberichten und Investorenpräsentationen. "
    "Alle Zahlen exakt wie im Dokument angegeben, mit Einheit. Keine Schätzungen erfinden."
)

async def _analyze_financial(
    chunks: list[str], company_name: str | None, report_year: int | None,
    language: str, total_pages: int,
) -> dict:
    context, _ = _build_context(chunks, total_pages)
    company_str = f"Unternehmen: {company_name}" if company_name else ""
    year_str = f"Berichtsjahr: {report_year}" if report_year else ""

    prompt = f"""Analysiere diesen Finanzbericht und extrahiere strukturierte Daten.

{company_str}
{year_str}

DOKUMENTAUSZUG:
{context}

Antworte NUR mit validem JSON:
{{
  "summary": "Executive Summary im wissenschaftlichen Stil, 4-6 Sätze mit Quellenzitaten [1][2]. Kernaussagen zu Umsatz, Profitabilität, Strategie, Risiken. Am Ende Literaturverzeichnis.",
  "signal_direction": "positive|negative|neutral",
  "risks": [
    {{"title": "Kurztitel", "description": "Beschreibung", "category": "Markt|Regulatorisch|Operationell|Finanziell|ESG", "severity": "hoch|mittel|niedrig"}}
  ],
  "targets": [],
  "commitments": [],
  "kpis": {{
    "revenue_eur": null,
    "ebitda_eur": null,
    "ebitda_margin_pct": null,
    "net_income_eur": null,
    "employees": null,
    "capex_eur": null,
    "free_cashflow_eur": null,
    "debt_ratio_pct": null,
    "equity_ratio_pct": null
  }},
  "metrics": [
    {{"metric_type": "revenue", "value": null, "unit": "EUR"}}
  ],
  "references": [
    {{"id": 1, "chunk_index": 0, "page_estimate": 1, "excerpt": "Exaktes Zitat"}}
  ]
}}

Nur ausfüllen was im Dokument steht. null für Unbekanntes."""

    try:
        raw = await _call_llm(_FINANCIAL_SYSTEM, prompt)
        result = json.loads(raw)
        result["doc_class"] = "financial"
        result["signal_dimension"] = "financial"
        return _append_bibliography(result)
    except Exception as exc:
        logger.error("doc_analyzer.financial_error", error=str(exc))
        r = _empty()
        r["doc_class"] = "financial"
        r["signal_dimension"] = "financial"
        return r


# ── 2. ESG Extractor ──────────────────────────────────────────────────────────

_ESG_SYSTEM = (
    "Du bist ein CSDDD/CSRD-Compliance-Analyst und ESG-Experte. "
    "Du extrahierst strukturierte Nachhaltigkeitsdaten mit wissenschaftlichem Zitierstil [1][2]. "
    "Nur Daten extrahieren die explizit im Dokument stehen. Keine Annahmen treffen."
)

async def _analyze_esg(
    chunks: list[str], company_name: str | None, report_year: int | None,
    language: str, total_pages: int,
) -> dict:
    context, _ = _build_context(chunks, total_pages)
    company_str = f"Unternehmen: {company_name}" if company_name else ""
    year_str = f"Berichtsjahr: {report_year}" if report_year else ""

    prompt = f"""Analysiere diesen Nachhaltigkeitsbericht und extrahiere strukturierte ESG-Daten.

{company_str}
{year_str}

DOKUMENTAUSZUG:
{context}

Antworte NUR mit validem JSON:
{{
  "summary": "Wissenschaftliche Zusammenfassung, 4-6 Sätze mit Quellenangaben [1][2]. Kernaussagen zu ESG-Performance, Zielen, CSDDD-Relevanz. Am Ende Literaturverzeichnis.",
  "signal_direction": "positive|negative|neutral",
  "risks": [
    {{"title": "Risikotitel", "description": "Beschreibung", "category": "Umwelt|Sozial|Governance|Lieferkette|Regulatorisch", "severity": "hoch|mittel|niedrig"}}
  ],
  "targets": [
    {{"area": "CO2|Wasser|Energie|Biodiversität|Sozial|Governance", "target": "Zielformulierung", "target_year": null, "baseline_year": null, "current_progress": null}}
  ],
  "commitments": [
    {{"article": "CSDDD Art. X|CSRD|freiwillig", "commitment": "Verpflichtung", "status": "geplant|in_umsetzung|abgeschlossen"}}
  ],
  "kpis": {{
    "co2_scope1_tco2": null,
    "co2_scope2_tco2": null,
    "co2_scope3_tco2": null,
    "energy_gwh": null,
    "renewable_energy_pct": null,
    "water_m3": null,
    "waste_tonnes": null,
    "women_leadership_pct": null,
    "employees": null,
    "supplier_audited_pct": null,
    "esg_score": null
  }},
  "metrics": [
    {{"metric_type": "co2_scope1", "value": null, "unit": "tCO2"}}
  ],
  "references": [
    {{"id": 1, "chunk_index": 0, "page_estimate": 1, "excerpt": "Exaktes Zitat"}}
  ]
}}

Nur ausfüllen was im Dokument steht. null für Unbekanntes."""

    try:
        raw = await _call_llm(_ESG_SYSTEM, prompt)
        result = json.loads(raw)
        result["doc_class"] = "esg"
        result["signal_dimension"] = "esg"
        return _append_bibliography(result)
    except Exception as exc:
        logger.error("doc_analyzer.esg_error", error=str(exc))
        r = _empty()
        r["doc_class"] = "esg"
        r["signal_dimension"] = "esg"
        return r


# ── 3. Regulatory Extractor ───────────────────────────────────────────────────

_REGULATORY_SYSTEM = (
    "Du bist ein Rechtsexperte für EU-Regulatorik und Corporate Compliance. "
    "Du extrahierst strukturierte Anforderungen aus Gesetzen und Richtlinien. "
    "Präzise Artikelreferenzen, Fristen und betroffene Unternehmen angeben."
)

async def _analyze_regulatory(
    chunks: list[str], company_name: str | None, report_year: int | None,
    language: str, total_pages: int,
) -> dict:
    context, _ = _build_context(chunks, total_pages)

    prompt = f"""Analysiere dieses regulatorische Dokument und extrahiere strukturierte Anforderungen.

DOKUMENTAUSZUG:
{context}

Antworte NUR mit validem JSON:
{{
  "summary": "Wissenschaftliche Zusammenfassung, 4-6 Sätze mit Artikelreferenzen [1][2]. Kernpflichten, Fristen, betroffene Unternehmen. Am Ende Literaturverzeichnis.",
  "signal_direction": "neutral",
  "risks": [
    {{"title": "Compliance-Risiko", "description": "Beschreibung", "category": "Regulatorisch", "severity": "hoch|mittel|niedrig"}}
  ],
  "targets": [],
  "commitments": [
    {{"article": "Art. X Abs. Y", "commitment": "Konkrete Pflicht", "status": "geplant"}}
  ],
  "kpis": {{
    "implementation_deadline": null,
    "affected_company_size_employees": null,
    "affected_turnover_eur": null,
    "penalty_max_pct_turnover": null
  }},
  "metrics": [],
  "references": [
    {{"id": 1, "chunk_index": 0, "page_estimate": 1, "excerpt": "Exaktes Zitat"}}
  ]
}}"""

    try:
        raw = await _call_llm(_REGULATORY_SYSTEM, prompt)
        result = json.loads(raw)
        result["doc_class"] = "regulatory"
        result["signal_dimension"] = "regulatory"
        result["signal_direction"] = "neutral"
        return _append_bibliography(result)
    except Exception as exc:
        logger.error("doc_analyzer.regulatory_error", error=str(exc))
        r = _empty()
        r["doc_class"] = "regulatory"
        r["signal_dimension"] = "regulatory"
        return r


# ── 4. Statement Extractor ────────────────────────────────────────────────────

_STATEMENT_SYSTEM = (
    "Du bist ein Corporate Intelligence Analyst. "
    "Du analysierst CEO-Statements, Pressemitteilungen und Führungskommunikation. "
    "Extrahiere konkrete Versprechen, benannte Ziele mit Jahreszahlen und strategische Ankündigungen. "
    "Bewerte Tonalität und Glaubwürdigkeit der Aussagen."
)

async def _analyze_statement(
    chunks: list[str], company_name: str | None, report_year: int | None,
    language: str, total_pages: int,
) -> dict:
    context, _ = _build_context(chunks, total_pages)
    company_str = f"Unternehmen: {company_name}" if company_name else ""
    year_str = f"Jahr: {report_year}" if report_year else ""

    prompt = f"""Analysiere dieses Statement/diese Kommunikation und extrahiere strategische Signale.

{company_str}
{year_str}

DOKUMENTAUSZUG:
{context}

Antworte NUR mit validem JSON:
{{
  "summary": "Zusammenfassung, 4-6 Sätze. Kernbotschaften, konkrete Versprechen, Tonalität. Quellenangaben [1][2]. Am Ende Literaturverzeichnis.",
  "signal_direction": "positive|negative|neutral",
  "risks": [
    {{"title": "Genanntes Risiko", "description": "Wie vom Management beschrieben", "category": "Markt|ESG|Governance|Operationell", "severity": "hoch|mittel|niedrig"}}
  ],
  "targets": [
    {{"area": "Bereich", "target": "Konkretes Versprechen mit Jahreszahl falls angegeben", "target_year": null, "baseline_year": null, "current_progress": null}}
  ],
  "commitments": [
    {{"article": "Freiwillig|Strategisch", "commitment": "Konkretes Versprechen das später überprüft werden kann", "status": "angekündigt"}}
  ],
  "kpis": {{
    "sentiment_score": null,
    "concrete_targets_count": null
  }},
  "metrics": [],
  "references": [
    {{"id": 1, "chunk_index": 0, "page_estimate": 1, "excerpt": "Exaktes Zitat des Versprechens"}}
  ]
}}"""

    try:
        raw = await _call_llm(_STATEMENT_SYSTEM, prompt)
        result = json.loads(raw)
        result["doc_class"] = "statement"
        result["signal_dimension"] = "governance"
        return _append_bibliography(result)
    except Exception as exc:
        logger.error("doc_analyzer.statement_error", error=str(exc))
        r = _empty()
        r["doc_class"] = "statement"
        r["signal_dimension"] = "governance"
        return r


# ── 5. Signal Extractor ───────────────────────────────────────────────────────

_SIGNAL_SYSTEM = (
    "Du bist ein Corporate Intelligence und Risk Analyst. "
    "Du analysierst externe Signale: Ratingberichte, NGO-Berichte, Gerichtsurteile, "
    "Insolvenzberichte, Produktrückrufe, Übernahmen, Führungswechsel. "
    "Bewerte Schwere, Dimension und Richtung des Signals."
)

async def _analyze_signal(
    chunks: list[str], company_name: str | None, report_year: int | None,
    language: str, total_pages: int,
) -> dict:
    context, _ = _build_context(chunks, total_pages)
    company_str = f"Betroffenes Unternehmen: {company_name}" if company_name else ""

    prompt = f"""Analysiere dieses externe Signal-Dokument.

{company_str}

DOKUMENTAUSZUG:
{context}

Antworte NUR mit validem JSON:
{{
  "summary": "Zusammenfassung des Signals, 3-5 Sätze. Was ist passiert? Wer ist betroffen? Welche Konsequenzen? Quellenangaben [1][2]. Am Ende Literaturverzeichnis.",
  "signal_direction": "positive|negative|neutral",
  "signal_dimension": "financial|esg|governance|supply_chain|regulatory|reputation",
  "risks": [
    {{"title": "Risiko aus Signal", "description": "Konkrete Auswirkung", "category": "Finanziell|ESG|Governance|Lieferkette|Regulatorisch|Reputation", "severity": "kritisch|hoch|mittel|niedrig"}}
  ],
  "targets": [],
  "commitments": [],
  "kpis": {{
    "signal_type": null,
    "affected_companies": null,
    "estimated_impact_eur": null
  }},
  "metrics": [],
  "references": [
    {{"id": 1, "chunk_index": 0, "page_estimate": 1, "excerpt": "Exaktes Zitat"}}
  ]
}}"""

    try:
        raw = await _call_llm(_SIGNAL_SYSTEM, prompt)
        result = json.loads(raw)
        result["doc_class"] = "signal"
        if "signal_dimension" not in result:
            result["signal_dimension"] = "reputation"
        return _append_bibliography(result)
    except Exception as exc:
        logger.error("doc_analyzer.signal_error", error=str(exc))
        return _empty()


# ── Router ────────────────────────────────────────────────────────────────────

async def analyze_document(
    chunks: list[str],
    doc_type: str,
    company_name: str | None,
    report_year: int | None,
    language: str = "de",
    total_pages: int = 1,
    sections: list[str] | None = None,
) -> dict:
    """Route to the correct extractor based on doc_class."""
    doc_class = get_doc_class(doc_type)

    logger.info(
        "doc_analyzer.start",
        doc_type=doc_type,
        doc_class=doc_class,
        company=company_name,
        year=report_year,
        chunks=len(chunks),
    )

    if doc_class == "financial":
        result = await _analyze_financial(chunks, company_name, report_year, language, total_pages)
    elif doc_class == "esg":
        result = await _analyze_esg(chunks, company_name, report_year, language, total_pages)
    elif doc_class == "regulatory":
        result = await _analyze_regulatory(chunks, company_name, report_year, language, total_pages)
    elif doc_class == "statement":
        result = await _analyze_statement(chunks, company_name, report_year, language, total_pages)
    else:
        result = await _analyze_signal(chunks, company_name, report_year, language, total_pages)

    logger.info(
        "doc_analyzer.done",
        doc_class=doc_class,
        risks=len(result.get("risks") or []),
        targets=len(result.get("targets") or []),
        direction=result.get("signal_direction"),
    )
    return result
