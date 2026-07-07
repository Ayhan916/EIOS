"""Crawler Agent — findet Dokument-URLs auf IR-Seiten und Portalen.

Strategien:
  1. Direct URL — source_url ist bereits ein direkter PDF/HTML-Link
  2. IR-Page Scan — source_url ist eine Investor-Relations-Seite,
     der Agent sucht nach PDF-Links mit report-relevanten Keywords
  3. CDP / GRI / ESMA — bekannte Portale mit strukturierten URLs

Gibt eine Liste von gefundenen Dokument-URLs zurück.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import structlog

logger = structlog.get_logger(__name__)

# Keywords die auf relevante Dokumente hindeuten
_REPORT_KEYWORDS = [
    "annual", "geschäftsbericht", "jahresbericht", "report", "sustainability",
    "nachhaltigkeitsbericht", "esg", "csrd", "csddd", "non-financial",
    "nfb", "dnk", "integrated", "climate", "klima", "scope3",
]

_PDF_LINK_RE = re.compile(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', re.IGNORECASE)
_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


@dataclass
class CrawlResult:
    ok: bool
    urls: list[str]
    error: str | None = None


async def crawl(source_url: str, doc_type: str) -> CrawlResult:
    """
    Given a source URL, return a list of document URLs to download.

    For direct PDF/file links: returns [source_url] immediately.
    For IR/portal pages: scans for relevant PDF links.
    """
    parsed = urlparse(source_url)
    lower_url = source_url.lower()

    # Direct file link
    if lower_url.endswith(".pdf") or "pdf" in parsed.query.lower():
        return CrawlResult(ok=True, urls=[source_url])

    # Scan the page for PDF links
    try:
        import httpx
    except ImportError:
        # Fallback: treat as direct URL
        return CrawlResult(ok=True, urls=[source_url])

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": "EIOSBot/1.0 (+https://eios.app/bot)"},
        ) as client:
            resp = await client.get(source_url)
            resp.raise_for_status()
            html = resp.text
            base_url = str(resp.url)

        # Find all PDF links
        pdf_hrefs = _PDF_LINK_RE.findall(html)
        all_hrefs = _LINK_RE.findall(html)

        # Filter hrefs that contain report keywords
        keyword_hrefs = [
            h for h in all_hrefs
            if any(kw in h.lower() for kw in _REPORT_KEYWORDS)
            and (h.lower().endswith(".pdf") or "report" in h.lower())
        ]

        candidates = list(dict.fromkeys(pdf_hrefs + keyword_hrefs))  # deduplicated

        # Resolve relative URLs
        resolved = []
        for href in candidates:
            if href.startswith("http"):
                resolved.append(href)
            elif href.startswith("/"):
                resolved.append(urljoin(base_url, href))

        if not resolved:
            # No PDFs found — return the page itself for HTML parsing
            resolved = [base_url]

        logger.info("crawler_agent.done", url=source_url, found=len(resolved))
        return CrawlResult(ok=True, urls=resolved[:10])  # max 10 links per source

    except Exception as exc:
        logger.error("crawler_agent.error", url=source_url, error=str(exc))
        # Fallback: try the URL directly
        return CrawlResult(ok=True, urls=[source_url], error=str(exc))
