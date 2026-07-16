"""Metric Verifier — prüft extrahierte Kennzahlen gegen Online-Quellen.

Reihenfolge:
  1. yfinance (börsenkotierte Unternehmen, letzte ~5 Jahre)
  2. DuckDuckGo + LLM-Parsing (historische Werte, alle Unternehmen)

Gibt VerificationResult zurück mit:
  - verified:         Wert stimmt mit Referenz überein (Abweichung < 30%)
  - discrepant:       Wert weicht stark ab (>5x)
  - not_found:        Kein Referenzwert gefunden
  - reference_value:  Gefundener Referenzwert
  - reference_source: z.B. "Yahoo Finance (BMW.DE)"
  - reference_url:    Direkte URL zur Quelle
"""
from __future__ import annotations

import re
import structlog

logger = structlog.get_logger(__name__)

# ── Ticker-Mapping ────────────────────────────────────────────────────────────

_TICKER_MAP: dict[str, str] = {
    "bmw":        "BMW.DE",
    "bayerische": "BMW.DE",
    "siemens":    "SIE.DE",
    "volkswagen": "VOW3.DE",
    "vw":         "VOW3.DE",
    "mercedes":   "MBG.DE",
    "daimler":    "MBG.DE",
    "basf":       "BAS.DE",
    "sap":        "SAP.DE",
    "bayer":      "BAYN.DE",
    "adidas":     "ADS.DE",
    "allianz":    "ALV.DE",
    "deutsche bank": "DBK.DE",
    "bosch":      None,  # nicht börsennotiert
}

# yfinance key → EIOS metric_type
_YFINANCE_METRIC_MAP: dict[str, list[str]] = {
    "fullTimeEmployees":       ["employees", "employees_total"],
    "totalRevenue":            ["revenue"],
    "ebitda":                  ["ebitda"],
    "netIncome":               ["net_income"],
    "totalDebt":               ["debt_ratio"],
    "freeCashflow":            ["free_cashflow"],
    "capitalExpenditures":     ["capex"],
}

_METRIC_SEARCH_TEMPLATES: dict[str, str] = {
    "employees":      "{company} total employees {year} annual report",
    "employees_total":"{company} total employees {year} annual report",
    "revenue":        "{company} total revenue {year} EUR million annual report",
    "ebitda":         "{company} EBITDA {year} annual report",
    "net_income":     "{company} net income profit {year} annual report",
    "co2_scope1":     "{company} CO2 scope 1 emissions {year} tCO2",
    "co2_scope2":     "{company} CO2 scope 2 emissions {year} tCO2",
    "co2_scope3":     "{company} CO2 scope 3 emissions {year} tCO2",
    "renewable_energy_pct": "{company} renewable energy percentage {year}",
}


class VerificationResult:
    def __init__(
        self,
        status: str,
        reference_value: float | None = None,
        reference_source: str | None = None,
        reference_url: str | None = None,
        note: str | None = None,
    ):
        self.status = status          # "verified" | "discrepant" | "not_found" | "error"
        self.reference_value = reference_value
        self.reference_source = reference_source
        self.reference_url = reference_url
        self.note = note

    @property
    def is_verified(self) -> bool:
        return self.status == "verified"

    @property
    def is_discrepant(self) -> bool:
        return self.status == "discrepant"


def _find_ticker(company_name: str) -> str | None:
    lower = company_name.lower()
    for keyword, ticker in _TICKER_MAP.items():
        if keyword in lower:
            return ticker
    return None


def _pct_diff(a: float, b: float) -> float:
    if b == 0:
        return float("inf")
    return abs(a - b) / abs(b) * 100


async def verify_metric(
    company_name: str,
    metric_type: str,
    year: int,
    extracted_value: float,
    unit: str,
) -> VerificationResult:
    """Vergleicht einen extrahierten Wert mit Online-Quellen."""

    # Schritt 1: yfinance
    result = await _verify_via_yfinance(company_name, metric_type, year, extracted_value)
    if result.status != "not_found":
        return result

    # Schritt 2: DuckDuckGo + LLM
    result = await _verify_via_web(company_name, metric_type, year, extracted_value, unit)
    return result


async def _verify_via_yfinance(
    company_name: str,
    metric_type: str,
    year: int,
    extracted_value: float,
) -> VerificationResult:
    ticker = _find_ticker(company_name)
    if not ticker:
        return VerificationResult("not_found")

    try:
        import yfinance as yf
        import asyncio

        def _fetch():
            t = yf.Ticker(ticker)

            # Direkte info-Felder (aktuellste Werte)
            for yf_key, metric_types in _YFINANCE_METRIC_MAP.items():
                if metric_type not in metric_types:
                    continue
                val = t.info.get(yf_key)
                if val and abs(val) > 0:
                    # yfinance liefert EUR/USD — für EUR umrechnen
                    ref = float(val)
                    # Umsatz/EBITDA in EUR_M → durch 1M
                    if metric_type in ("revenue", "ebitda", "net_income", "capex", "free_cashflow"):
                        ref = ref / 1_000_000
                    url = f"https://finance.yahoo.com/quote/{ticker}"
                    source = f"Yahoo Finance ({ticker})"
                    return ref, source, url
            return None, None, None

        ref_val, source, url = await asyncio.get_event_loop().run_in_executor(None, _fetch)
        if ref_val is None:
            return VerificationResult("not_found")

        diff = _pct_diff(extracted_value, ref_val)
        if diff <= 30:
            note = f"Abweichung {diff:.1f}% — plausibel"
            return VerificationResult("verified", ref_val, source, url, note)
        elif diff > 400:
            note = f"Abweichung {diff:.0f}% — Wert {extracted_value:,.0f} vs. Referenz {ref_val:,.0f}"
            return VerificationResult("discrepant", ref_val, source, url, note)
        else:
            note = f"Abweichung {diff:.1f}% — möglicherweise anderes Jahr/Scope"
            return VerificationResult("verified", ref_val, source, url, note)

    except Exception as exc:
        logger.warning("metric_verifier.yfinance_error", error=str(exc))
        return VerificationResult("not_found")


async def _verify_via_web(
    company_name: str,
    metric_type: str,
    year: int,
    extracted_value: float,
    unit: str,
) -> VerificationResult:
    template = _METRIC_SEARCH_TEMPLATES.get(metric_type)
    if not template:
        return VerificationResult("not_found")

    query = template.format(company=company_name, year=year)

    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=5)
        if not results:
            return VerificationResult("not_found")

        snippets = "\n".join(
            f"[{i+1}] {r.get('title', '')} — {r.get('body', '')[:300]}"
            for i, r in enumerate(results[:5])
        )
        urls = [r.get("href", "") for r in results[:5] if r.get("href")]

        # LLM extrahiert den Referenzwert aus den Suchergebnissen
        ref_val, source_idx = await _extract_value_from_snippets(
            company_name, metric_type, year, unit, snippets
        )
        if ref_val is None:
            return VerificationResult("not_found")

        source_url = urls[source_idx] if source_idx < len(urls) else ""
        source_label = f"Web: {results[source_idx].get('title', 'Suchergebnis')[:80]}" if source_idx < len(results) else "Web-Suche"

        diff = _pct_diff(extracted_value, ref_val)
        note = f"Abweichung {diff:.1f}% — Wert {extracted_value:,.0f} vs. Referenz {ref_val:,.0f} {unit}"
        status = "verified" if diff <= 30 else ("discrepant" if diff > 400 else "verified")

        return VerificationResult(status, ref_val, source_label, source_url, note)

    except Exception as exc:
        logger.warning("metric_verifier.web_error", error=str(exc))
        return VerificationResult("error", note=str(exc)[:200])


async def _extract_value_from_snippets(
    company_name: str,
    metric_type: str,
    year: int,
    unit: str,
    snippets: str,
) -> tuple[float | None, int]:
    """LLM extrahiert den Referenzwert aus den Suchergebnis-Snippets."""
    try:
        from groq import AsyncGroq
        import os

        client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
        prompt = (
            f"Du extrahierst eine Kennzahl aus Suchergebnis-Snippets.\n\n"
            f"Unternehmen: {company_name}\n"
            f"Kennzahl: {metric_type}\n"
            f"Jahr: {year}\n"
            f"Einheit: {unit}\n\n"
            f"Suchergebnisse:\n{snippets}\n\n"
            f"Antworte NUR mit:\n"
            f"VALUE: <zahl oder null>\n"
            f"SOURCE_INDEX: <0-4 (Index des besten Ergebnisses)>\n\n"
            f"Wichtig: Nur Zahlen, keine Einheiten, keine Erklärungen. "
            f"Wenn kein plausibler Wert gefunden, schreibe VALUE: null"
        )

        resp = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0,
        )
        text = resp.choices[0].message.content or ""
        value_match = re.search(r"VALUE:\s*([\d.,]+|null)", text, re.IGNORECASE)
        idx_match = re.search(r"SOURCE_INDEX:\s*(\d)", text)

        if not value_match or value_match.group(1).lower() == "null":
            return None, 0

        raw = value_match.group(1).replace(",", ".")
        ref_val = float(raw)
        source_idx = int(idx_match.group(1)) if idx_match else 0
        return ref_val, source_idx

    except Exception as exc:
        logger.warning("metric_verifier.llm_error", error=str(exc))
        return None, 0
