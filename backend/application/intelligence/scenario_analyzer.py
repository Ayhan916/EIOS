"""Proactive Scenario Intelligence — projiziert externe Ereignisse auf das Lieferanten-Portfolio.

Wenn ein Branchenereignis erkannt wird (z.B. "VW streicht Stellen"),
analysiert dieses Modul:
  1. Welche Lieferanten im gleichen Sektor sind betroffen?
  2. Wie ist die aktuelle Finanzlage des betroffenen Unternehmens? (yfinance)
  3. Was sagen aktuelle Nachrichten? (duckduckgo-search)
  4. Was steht in internen Dokumenten? (RAG)
  5. Pro Lieferant: Expositions-Level + Handlungsempfehlung (LLM)
"""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.llm import LLMProvider, Message

logger = structlog.get_logger(__name__)

# ── Sector keyword mapping ────────────────────────────────────────────────────

_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "automotive": ["auto", "automobil", "fahrzeug", "car", "vehicle", "kfz", "motor"],
    "technology": ["tech", "software", "it ", "digital", "elektronik", "electronic", "semiconductor"],
    "energy": ["energie", "energy", "öl", "oil", "gas", "solar", "wind", "renewabl"],
    "finance": ["bank", "finanz", "financial", "versicherung", "insurance", "kredit"],
    "retail": ["handel", "retail", "consumer", "einzelhandel", "e-commerce"],
    "chemical": ["chemie", "chemical", "pharma", "kunststoff", "plastic"],
    "steel": ["stahl", "steel", "metall", "metal", "aluminium"],
    "logistics": ["logistik", "logistics", "transport", "shipping", "spedition"],
    "construction": ["bau", "construction", "immobilien", "real estate"],
    "textile": ["textil", "textile", "bekleidung", "clothing", "fashion"],
}

# Common stock ticker lookup for major companies
_TICKER_MAP: dict[str, str] = {
    "volkswagen": "VOW3.DE", "vw": "VOW3.DE",
    "bmw": "BMW.DE",
    "mercedes": "MBG.DE", "daimler": "MBG.DE",
    "stellantis": "STLAM.MI",
    "siemens": "SIE.DE",
    "basf": "BAS.DE",
    "bayer": "BAYN.DE",
    "allianz": "ALV.DE",
    "deutsche bank": "DBK.DE",
    "samsung": "005930.KS",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "toyota": "TM",
    "ford": "F",
    "general motors": "GM",
    "bosch": None,  # private
    "continental": "CON.DE",
    "schaeffler": "SHA.DE",
}


def detect_sector(text: str) -> str | None:
    """Detect the sector from signal text using keyword matching."""
    text_lower = text.lower()
    for sector, keywords in _SECTOR_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return sector
    return None


def find_ticker(company_name: str) -> str | None:
    """Return stock ticker for a known company name."""
    name_lower = company_name.lower()
    for key, ticker in _TICKER_MAP.items():
        if key in name_lower:
            return ticker
    return None


# ── Financial data (yfinance) ─────────────────────────────────────────────────

def fetch_financial_data(company_name: str) -> dict:
    """Fetch current financial data for a company via yfinance."""
    try:
        import yfinance as yf

        ticker_sym = find_ticker(company_name)
        if not ticker_sym:
            # Try direct symbol guess
            ticker_sym = company_name.upper().split()[0]

        ticker = yf.Ticker(ticker_sym)
        info = ticker.info or {}

        # Key financial metrics
        data = {
            "ticker": ticker_sym,
            "company": info.get("longName") or info.get("shortName") or company_name,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "employees": info.get("fullTimeEmployees"),
            "revenue_eur_b": round(info.get("totalRevenue", 0) / 1e9, 2) if info.get("totalRevenue") else None,
            "ebitda_eur_b": round(info.get("ebitda", 0) / 1e9, 2) if info.get("ebitda") else None,
            "profit_margin_pct": round((info.get("profitMargins", 0) or 0) * 100, 1),
            "debt_to_equity": round(info.get("debtToEquity", 0) or 0, 2),
            "current_ratio": round(info.get("currentRatio", 0) or 0, 2),
            "52w_change_pct": round((info.get("52WeekChange", 0) or 0) * 100, 1),
            "analyst_rating": info.get("recommendationKey"),
            "target_price": info.get("targetMeanPrice"),
            "description": (info.get("longBusinessSummary") or "")[:400],
        }
        return {k: v for k, v in data.items() if v not in (None, 0, "", 0.0)}
    except Exception as e:
        logger.warning("yfinance_fetch_failed", company=company_name, error=str(e))
        return {"company": company_name, "error": "Finanzdaten nicht verfügbar"}


# ── News context (duckduckgo-search) ─────────────────────────────────────────

def fetch_news_context(company_name: str, signal_text: str, max_results: int = 6) -> list[dict]:
    """Fetch recent news about the company related to the signal."""
    try:
        from duckduckgo_search import DDGS

        query = f"{company_name} financial situation layoffs revenue 2024 2025"
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")[:200],
                    "source": r.get("source", ""),
                    "date": r.get("date", ""),
                })
        return results
    except Exception as e:
        logger.warning("duckduckgo_fetch_failed", error=str(e))
        return []


# ── Supplier matching ─────────────────────────────────────────────────────────

async def find_suppliers_in_sector(
    sector: str,
    org_id: str,
    session: AsyncSession,
) -> list[dict]:
    """Find suppliers whose industry matches the given sector."""
    from infrastructure.persistence.models.supplier import SupplierModel

    keywords = _SECTOR_KEYWORDS.get(sector.lower(), [sector.lower()])

    stmt = select(
        SupplierModel.id,
        SupplierModel.name,
        SupplierModel.industry,
        SupplierModel.country,
    ).where(SupplierModel.organization_id == org_id)

    rows = (await session.execute(stmt)).all()

    matched = []
    for r in rows:
        industry_lower = (r.industry or "").lower()
        if any(kw in industry_lower for kw in keywords):
            matched.append({
                "id": r.id,
                "name": r.name,
                "industry": r.industry,
                "country": r.country,
            })

    return matched


# ── Internal document context ─────────────────────────────────────────────────

async def fetch_doc_context(
    company_name: str,
    question: str,
    org_id: str,
    session: AsyncSession,
) -> str:
    """Semantic search in internal documents for the company."""
    try:
        from application.copilot.retrieval.document_retriever import retrieve_document_context

        result = await retrieve_document_context(
            question=f"{company_name} {question}",
            org_id=org_id,
            session=session,
            top_k=4,
        )
        if not result.data:
            return ""
        snippets = [f"[{r['company_name'] or 'Doc'} {r['report_year'] or ''}]: {r['content'][:300]}"
                    for r in result.data[:4]]
        return "\n".join(snippets)
    except Exception as e:
        logger.warning("doc_context_fetch_failed", error=str(e))
        return ""


# ── Core scenario analysis ────────────────────────────────────────────────────

async def run_scenario_analysis(
    signal_text: str,
    company_name: str,
    sector: str,
    org_id: str,
    session: AsyncSession,
    llm: LLMProvider,
) -> dict:
    """Full scenario analysis pipeline."""

    # 1. Find affected suppliers
    suppliers = await find_suppliers_in_sector(sector, org_id, session)

    # 2. Fetch financial data (blocking → run in thread)
    loop = asyncio.get_event_loop()
    financial_data = await loop.run_in_executor(None, fetch_financial_data, company_name)

    # 3. Fetch news context
    news = await loop.run_in_executor(None, fetch_news_context, company_name, signal_text)

    # 4. Fetch internal document context
    doc_context = await fetch_doc_context(company_name, signal_text, org_id, session)

    # 5. Build LLM context
    fin_str = json.dumps(financial_data, ensure_ascii=False, indent=None)
    news_str = "\n".join(f"- {n['title']} ({n['source']}, {n['date']}): {n['snippet']}" for n in news[:4])
    suppliers_str = "\n".join(f"- {s['name']} | Branche: {s['industry']} | Land: {s['country']}" for s in suppliers)

    system = f"""Du bist ein Szenario-Risikoanalyst für ESG und Lieferkettenrisiken.

EREIGNIS: {signal_text}
BETROFFENES UNTERNEHMEN: {company_name}
BRANCHE: {sector}

AKTUELLE FINANZDATEN ({company_name}):
{fin_str}

AKTUELLE NACHRICHTEN:
{news_str or "Keine aktuellen Nachrichten verfügbar"}

INTERNE DOKUMENTENKONTEXT:
{doc_context or "Keine internen Dokumente verfügbar"}

LIEFERANTEN IM GLEICHEN SEKTOR:
{suppliers_str or "Keine Lieferanten in diesem Sektor gefunden"}

Analysiere für jeden Lieferanten die Exposition gegenüber diesem Ereignis.
Berücksichtige: direkte Abhängigkeiten, Brancheneffekte, Land-Risiken, finanzielle Lage des Auslösers.

Antworte NUR mit validem JSON (kein Markdown, kein Text davor/danach):
{{
  "event_summary": "Kurze Zusammenfassung des Ereignisses und seiner Ursachen (2-3 Sätze)",
  "financial_assessment": "Einschätzung der finanziellen Lage von {company_name} (2-3 Sätze)",
  "sector_impact": "Erwarteter Brancheneffekt (1-2 Sätze)",
  "suppliers": [
    {{
      "supplier_id": "id",
      "supplier_name": "name",
      "exposure_level": "HIGH|MEDIUM|LOW",
      "exposure_reason": "Warum ist dieser Lieferant betroffen?",
      "recommended_action": "Konkrete Handlungsempfehlung",
      "urgency": "IMMEDIATE|SHORT_TERM|MONITOR"
    }}
  ],
  "overall_risk_level": "HIGH|MEDIUM|LOW",
  "data_sources": ["yfinance", "duckduckgo", "internal_docs"]
}}"""

    try:
        resp = await llm.complete(
            messages=[Message(role="user", content="Führe die Szenario-Analyse durch.")],
            system=system,
            max_tokens=1500,
            temperature=0.0,
        )
        result = json.loads(resp.content.strip())
    except Exception as e:
        logger.error("scenario_llm_failed", error=str(e))
        result = {
            "event_summary": signal_text,
            "financial_assessment": json.dumps(financial_data, ensure_ascii=False),
            "sector_impact": f"Keine LLM-Analyse verfügbar: {e}",
            "suppliers": [
                {
                    "supplier_id": s["id"],
                    "supplier_name": s["name"],
                    "exposure_level": "UNKNOWN",
                    "exposure_reason": "LLM-Analyse fehlgeschlagen",
                    "recommended_action": "Manuell prüfen",
                    "urgency": "MONITOR",
                }
                for s in suppliers
            ],
            "overall_risk_level": "UNKNOWN",
            "data_sources": [],
        }

    return {
        "company_name": company_name,
        "sector": sector,
        "signal_text": signal_text,
        "suppliers_found": len(suppliers),
        "financial_data": financial_data,
        "news_headlines": [n["title"] for n in news[:4]],
        "analysis": result,
    }
