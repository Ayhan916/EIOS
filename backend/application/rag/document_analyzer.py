"""Document Analyzer Agent — LLM-basierte Extraktion strukturierter Daten aus Dokumenten.

Extrahiert aus Geschäftsberichten, Nachhaltigkeitsberichten etc.:
  - Risiken (mit Kategorie, Schwere, betroffene Bereiche)
  - ESG-Ziele und Fortschritte
  - Verpflichtungen (CSDDD/CSRD-relevant)
  - KPIs (CO2, Wasser, Energie, Lieferantenzahlen, etc.)
  - Executive Summary

Sicherheitshinweis: Kein deterministisches Scoring — reine Extraktion.
Scoring bleibt im deterministischen M43-Modell.
"""

from __future__ import annotations

import json
import os
import re

import structlog

logger = structlog.get_logger(__name__)

_MAX_CONTEXT_CHARS = 12_000  # ~3000 tokens für Analyse-Prompt


def _get_client():
    """Lazy-init Anthropic client."""
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


def analyze_document(
    chunks: list[str],
    doc_type: str,
    company_name: str | None,
    report_year: int | None,
    language: str = "de",
) -> dict:
    """
    Analyze document chunks and extract structured data via Claude.

    Returns dict with keys:
      summary, risks, targets, commitments, kpis, esg_score_hint
    """
    # Select representative chunks (first 5 + last 2 = context window)
    sample_chunks = chunks[:5] + (chunks[-2:] if len(chunks) > 7 else [])
    context = "\n\n---\n\n".join(sample_chunks)[:_MAX_CONTEXT_CHARS]

    doc_type_label = {
        "annual_report": "Geschäftsbericht",
        "sustainability_report": "Nachhaltigkeitsbericht / ESG-Report",
        "audit_report": "Audit-Bericht",
        "csrd_report": "CSRD-Bericht",
        "csddd_disclosure": "CSDDD Due-Diligence-Erklärung",
        "sector_risk": "Sektoraler Risikoreport",
    }.get(doc_type, doc_type)

    company_str = f"Unternehmen: {company_name}" if company_name else ""
    year_str = f"Berichtsjahr: {report_year}" if report_year else ""

    prompt = f"""Du bist ein CSDDD/CSRD-Compliance-Analyst. Analysiere den folgenden Dokumentenauszug und extrahiere strukturierte Daten.

Dokumenttyp: {doc_type_label}
{company_str}
{year_str}

DOKUMENTAUSZUG:
{context}

Antworte NUR mit validem JSON (kein Markdown, kein Text davor/danach):
{{
  "summary": "Executive Summary in 3-4 Sätzen",
  "risks": [
    {{
      "category": "Umwelt|Sozial|Governance|Lieferkette|Regulatorisch",
      "title": "Kurztitel",
      "description": "Beschreibung",
      "severity": "hoch|mittel|niedrig",
      "affected_regions": ["Land/Region"]
    }}
  ],
  "targets": [
    {{
      "area": "CO2|Wasser|Energie|Biodiversität|Sozial|Governance",
      "target": "Zielformulierung",
      "baseline_year": 2020,
      "target_year": 2030,
      "current_progress": "Fortschritt falls angegeben"
    }}
  ],
  "commitments": [
    {{
      "article": "CSDDD Art. X | CSRD | freiwillig",
      "commitment": "Verpflichtung",
      "status": "geplant|in_umsetzung|abgeschlossen"
    }}
  ],
  "kpis": {{
    "co2_emissions_tco2": null,
    "energy_consumption_gwh": null,
    "water_consumption_m3": null,
    "employee_count": null,
    "supplier_count": null,
    "women_in_leadership_pct": null,
    "renewable_energy_pct": null
  }},
  "esg_score_hint": null
}}

Fülle nur aus was im Dokument vorhanden ist. Null für fehlende Werte."""

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        logger.info(
            "doc_analyzer.done",
            doc_type=doc_type,
            company=company_name,
            risks=len(result.get("risks", [])),
            targets=len(result.get("targets", [])),
        )
        return result
    except json.JSONDecodeError as exc:
        logger.warning("doc_analyzer.json_error", error=str(exc))
        return _empty_result()
    except Exception as exc:
        logger.error("doc_analyzer.error", error=str(exc))
        return _empty_result()


def _empty_result() -> dict:
    return {
        "summary": None,
        "risks": [],
        "targets": [],
        "commitments": [],
        "kpis": {},
        "esg_score_hint": None,
    }
