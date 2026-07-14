"""
Document Classifier — erkennt Typ, Klasse, Unternehmen, Jahr und Sprache automatisch.

Strategie:
  1. Dateiname-Heuristik (schnell, kein API-Call)
  2. Groq LLM auf Basis der ersten ~800 Wörter (genauer Fallback)

Rückgabe: doc_type, doc_class, company_name, report_year, title, language,
          signal_dimension, confidence_source
"""

from __future__ import annotations

import json
import re

import structlog

from .document_parser import parse_pdf, parse_html, parse_text

logger = structlog.get_logger(__name__)

# ── Dokumenttypen ─────────────────────────────────────────────────────────────

DOC_TYPES = [
    "annual_report",
    "sustainability_report",
    "esg_overview",
    "governance_report",
    "investor_presentation",
    "press_release",
    "qa_document",
    "executive_statement",
    "key_metrics",
    "csrd_report",
    "csddd_disclosure",
    "cdp_questionnaire",
    "audit_report",
    "sector_risk",
    "financial_statement",
    "rating_report",
    "legal_document",
    "other",
]

# Mapping doc_type → doc_class
DOC_CLASS_MAP: dict[str, str] = {
    "annual_report":         "financial",
    "financial_statement":   "financial",
    "investor_presentation": "financial",
    "key_metrics":           "financial",
    "sustainability_report": "esg",
    "esg_overview":          "esg",
    "cdp_questionnaire":     "esg",
    "csrd_report":           "regulatory",
    "csddd_disclosure":      "regulatory",
    "audit_report":          "regulatory",
    "legal_document":        "regulatory",
    "rating_report":         "signal",
    "sector_risk":           "signal",
    "governance_report":     "statement",
    "press_release":         "statement",
    "qa_document":           "statement",
    "executive_statement":   "statement",
    "other":                 "signal",
}

# Mapping doc_class → primary signal_dimension
CLASS_DIMENSION_MAP: dict[str, str] = {
    "financial":  "financial",
    "esg":        "esg",
    "regulatory": "regulatory",
    "statement":  "governance",
    "signal":     "reputation",
}

# ── Heuristik-Muster ──────────────────────────────────────────────────────────

_PATTERNS: list[tuple[str, list[str]]] = [
    ("cdp_questionnaire",     ["cdp", "carbon disclosure", "climate questionnaire"]),
    ("csrd_report",           ["csrd", "corporate sustainability reporting", "2022/2464"]),
    ("csddd_disclosure",      ["csddd", "corporate sustainability due diligence", "2024/1760"]),
    ("sustainability_report", ["sustainability report", "sustainable value", "nachhaltigkeitsbericht",
                               "esg report", "non-financial", "acting sustainably"]),
    ("esg_overview",          ["esg overview", "esg summary", "esg fact", "esg profile"]),
    ("governance_report",     ["governance report", "corporate governance"]),
    ("investor_presentation", ["investor presentation", "investor day", "capital market", "kapitalmarkttag"]),
    ("press_release",         ["press release", "pressemitteilung", "media release"]),
    ("qa_document",           ["q&a", "question and answer", "analyst q"]),
    ("executive_statement",   ["statement by", "letter from", "chairman", "ceo letter",
                               "vorstandsbrief", "speech by", "ceo statement"]),
    ("key_metrics",           ["key metrics", "key figures", "kennzahlen", "factsheet"]),
    ("audit_report",          ["audit report", "auditor", "prüfbericht", "assurance"]),
    ("financial_statement",   ["financial statement", "jahresabschluss", "bilanz", "balance sheet",
                               "income statement", "cash flow statement", "finanzbericht"]),
    ("rating_report",         ["rating", "credit rating", "moody", "fitch", "s&p", "sustainalytics", "msci esg"]),
    ("legal_document",        ["urteil", "klage", "court", "judgment", "legal notice", "bußgeld"]),
    ("sector_risk",           ["sector risk", "sektorrisiko", "industry risk"]),
    ("annual_report",         ["annual report", "geschäftsbericht", "group report", "jahresbericht",
                               "integrated report", "annual review"]),
]


def _match_heuristic(text: str) -> str | None:
    lower = text.lower()
    for doc_type, keywords in _PATTERNS:
        if any(k in lower for k in keywords):
            return doc_type
    return None


def _extract_year(text: str) -> int | None:
    matches = re.findall(r"\b(20[0-2]\d)\b", text)
    if matches:
        from collections import Counter
        counts = Counter(matches)
        return int(counts.most_common(1)[0][0])
    return None


def get_doc_class(doc_type: str) -> str:
    return DOC_CLASS_MAP.get(doc_type, "signal")


def get_signal_dimension(doc_class: str) -> str:
    return CLASS_DIMENSION_MAP.get(doc_class, "reputation")


# ── Groq-Klassifizierung ──────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert document classifier for corporate intelligence.
Analyze the document and return ONLY valid JSON with these fields:

{
  "doc_type": "<one of: annual_report, sustainability_report, esg_overview, governance_report, investor_presentation, press_release, qa_document, executive_statement, key_metrics, csrd_report, csddd_disclosure, cdp_questionnaire, audit_report, sector_risk, financial_statement, rating_report, legal_document, other>",
  "company_name": "<official company name, e.g. 'BMW AG', 'Siemens AG', or null if not a company document>",
  "report_year": <integer fiscal/reporting year or null>,
  "period": "<'FY' | 'Q1' | 'Q2' | 'Q3' | 'Q4' | 'H1' | 'H2' or null>",
  "title": "<official document title or null>",
  "language": "<'de' | 'en' | 'fr' | 'es' | 'it'>",
  "confidence": <0.0-1.0>,
  "alternatives": [{"doc_type": "<type>", "confidence": <0.0-1.0>}]
}

Rules:
- company_name: extract the ISSUING company (not mentioned companies). For regulatory docs (EU directives etc.) use null.
- report_year: the year the document COVERS, not the publication year.
- alternatives: list the top 2 alternative doc_type candidates with their confidence scores (omit if none).
- Be precise. Return null for unknown fields."""


async def classify_with_groq(text_excerpt: str, filename: str) -> dict:
    try:
        from infrastructure.llm.deps import get_llm_provider
        from application.ports.llm import Message
        llm = get_llm_provider()
    except Exception:
        return {}

    prompt = f"Filename: {filename}\n\nDocument text (first 800 words):\n{text_excerpt[:4000]}"

    import asyncio
    for attempt in range(4):
        try:
            response = await llm.complete(
                messages=[Message(role="user", content=prompt)],
                system=_SYSTEM_PROMPT,
                max_tokens=300,
                temperature=0.0,
            )
            raw = response.content.strip()
            raw = re.sub(r"^```(?:json)?\n?", "", raw).rstrip("` \n")
            return json.loads(raw)
        except Exception as exc:
            err_str = str(exc)
            if ("429" in err_str or "rate_limit_exceeded" in err_str) and attempt < 3:
                wait_match = re.search(r"try again in (\d+(?:\.\d+)?)s", err_str)
                wait = float(wait_match.group(1)) + 2.0 if wait_match else 15.0
                logger.warning("doc_classifier.rate_limit_retry", attempt=attempt + 1, wait_s=round(wait, 1))
                await asyncio.sleep(wait)
                continue
            logger.warning("doc_classifier.groq_failed", error=str(exc))
            return {}
    return {}


# ── Haupt-Klassifizierungs-Funktion ──────────────────────────────────────────

async def classify_document(
    content: bytes,
    content_type: str,
    filename: str,
) -> dict:
    """
    Classify a document automatically. Returns:
      {doc_type, doc_class, company_name, report_year, period, title, language,
       signal_dimension, confidence_source}
    """
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename

    # Step 1 — Parse text
    if content_type == "pdf":
        parse_result = parse_pdf(content)
    elif content_type == "html":
        parse_result = parse_html(content, url=f"upload://{filename}")
    else:
        text = content.decode("utf-8", errors="replace")
        parse_result = parse_text(text)

    doc_text = ""
    doc_title = None
    if parse_result.ok and parse_result.document:
        doc = parse_result.document
        doc_title = doc.title
        words: list[str] = []
        for chunk in (doc.chunks or []):
            words.extend(chunk.split())
            if len(words) >= 800:
                break
        doc_text = " ".join(words[:800])

    # Step 2 — Heuristik auf Dateiname + Titel
    combined = f"{stem} {doc_title or ''}"
    doc_type_heuristic = _match_heuristic(combined)
    year_heuristic = _extract_year(combined) or _extract_year(doc_text)

    # Step 3 — Groq (immer aufrufen wenn Text vorhanden, für company_name)
    groq_result: dict = {}
    if doc_text:
        groq_result = await classify_with_groq(doc_text, filename)

    # Merge: prefer Groq for company_name + language, heuristic for doc_type if confident
    doc_type = (
        doc_type_heuristic
        or (groq_result.get("doc_type") if groq_result.get("doc_type") in DOC_TYPES else None)
        or "annual_report"
    )
    # If Groq gives a more specific type and heuristic is generic, prefer Groq
    if groq_result.get("doc_type") in DOC_TYPES and doc_type_heuristic in (None, "annual_report"):
        doc_type = groq_result["doc_type"]

    company_name = groq_result.get("company_name") or None
    report_year = (
        groq_result.get("report_year")
        or year_heuristic
        or None
    )
    title = groq_result.get("title") or doc_title
    language = groq_result.get("language") or "de"
    period = groq_result.get("period") or "FY"

    doc_class = get_doc_class(doc_type)
    signal_dimension = get_signal_dimension(doc_class)

    confidence_source = "llm" if groq_result.get("doc_type") else (
        "filename" if doc_type_heuristic else "fallback"
    )

    logger.info(
        "doc_classifier.done",
        filename=filename,
        doc_type=doc_type,
        doc_class=doc_class,
        company=company_name,
        year=report_year,
        confidence=confidence_source,
    )

    return {
        "doc_type": doc_type,
        "doc_class": doc_class,
        "company_name": company_name,
        "report_year": report_year,
        "period": period,
        "title": title,
        "language": language,
        "signal_dimension": signal_dimension,
        "confidence_source": confidence_source,
    }
