"""Live News Feed Service.

Fetches news from GNews (primary) and GDELT (secondary) for:
  - Supplier names (direct)
  - Countries where suppliers operate (country)
  - Supplier partners / associated companies (partner)

Translates articles to the org's configured language via Groq LLM if needed.
Assigns articles to affected suppliers and persists in news_articles table.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.news_feed import (
    NewsArticleModel,
    NewsSupplierAssignmentModel,
)
from infrastructure.persistence.models.supplier import SupplierModel
from shared.config import settings

logger = structlog.get_logger(__name__)

# Legal form suffixes to strip for cleaner search queries
_LEGAL_SUFFIXES = [
    "aktiengesellschaft",
    "gesellschaft mit beschränkter haftung",
    "gmbh & co. kg",
    "gmbh & co kg",
    "gmbh",
    "ag & co kgaa",
    "kgaa",
    "ag",
    "se",
    "inc.",
    "inc",
    "corp.",
    "corp",
    "ltd.",
    "ltd",
    "llc",
    "plc",
    "s.a.",
    "s.a",
    "s.r.l",
    "s.r.l.",
    "group ag",
    "group",
    "holding",
    "holdings",
]

_STRIP_PREFIXES = ["dr. ing. h.c. f.", "dr. ing.", "h.c.", "prof.", "dr."]

# Map verbose legal names to their widely-known brand names for better search results
_BRAND_ALIASES: dict[str, str] = {
    "bayerische motoren werke": "BMW",
    "volkswagen": "Volkswagen",
    "mercedes-benz group": "Mercedes-Benz",
    "mercedes benz group": "Mercedes-Benz",
}

_GNEWS_URL = "https://gnews.io/api/v4/search"
_GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_TIMEOUT = httpx.Timeout(connect=10.0, read=20.0, write=5.0, pool=5.0)

# Keep news for 7 days
_RETENTION_DAYS = 7
# Max articles per query
_GNEWS_MAX = 10
_GDELT_MAX = 5

# Keywords that indicate a business-relevant article.
# At least one must appear in the article title or summary.
# Broad enough to capture business/financial news, strict enough to exclude
# sports, entertainment, lifestyle, and personal news about unrelated people.
_BUSINESS_KEYWORDS: set[str] = {
    # ESG / supply chain
    "sustainability",
    "esg",
    "compliance",
    "supply chain",
    "environment",
    "labor",
    "labour",
    "sanctions",
    "recall",
    "fraud",
    "bribery",
    "human rights",
    "regulation",
    "penalty",
    "investigation",
    "carbon",
    "emissions",
    "forced labor",
    "forced labour",
    "corruption",
    "governance",
    "ethics",
    "audit",
    "violation",
    "fine",
    "lawsuit",
    "controversy",
    "factory",
    "workers",
    "wage",
    "pollution",
    "climate",
    "deforestation",
    "child labor",
    "child labour",
    "modern slavery",
    "human trafficking",
    "whistleblower",
    "certification",
    "due diligence",
    # Business / financial
    "earnings",
    "revenue",
    "profit",
    "loss",
    "shares",
    "stock",
    "quarterly",
    "annual",
    "ceo",
    "executive",
    "acquisition",
    "merger",
    "bankruptcy",
    "investment",
    "investor",
    "market",
    "delivery",
    "deliveries",
    "production",
    "manufacturing",
    "plant",
    "layoff",
    "layoffs",
    "restructuring",
    "expansion",
    "partnership",
    "contract",
    "deal",
    "settlement",
    "charges",
    "court",
    "tariff",
    "import",
    "export",
    "trade",
    "electric",
    "vehicle",
    "ev",
    # German equivalents
    "nachhaltigkeit",
    "umwelt",
    "verstoß",
    "lieferkette",
    "sanktion",
    "betrug",
    "korruption",
    "strafe",
    "klage",
    "gewinn",
    "verlust",
    "umsatz",
    "quartal",
    "produktion",
    "werk",
    "stellenabbau",
    "übernahme",
    "fusion",
}

# Country-level ESG search terms — appended to make country queries more targeted
_COUNTRY_ESG_SUFFIX = "ESG supply chain compliance"


def _search_name(name: str) -> str:
    """Return a clean, short search query from a full legal company name."""
    cleaned = name.strip()
    # Strip known prefixes
    for prefix in _STRIP_PREFIXES:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    # Strip trailing legal suffixes
    lower = cleaned.lower().rstrip(",. ")
    for suffix in _LEGAL_SUFFIXES:
        if lower.endswith(suffix):
            cleaned = cleaned[: len(cleaned) - len(suffix)].strip().rstrip(",. ")
            lower = cleaned.lower()
    # Remove punctuation-only tokens and abbreviations like "H.C."
    tokens = [t for t in cleaned.split() if len(t) > 1 and not (t.endswith(".") and len(t) <= 4)]
    result = " ".join(tokens).strip(" ,.")
    # Check for brand alias (e.g. "Bayerische Motoren Werke" → "BMW")
    result_check = result if result else name
    for verbose, brand in _BRAND_ALIASES.items():
        if verbose in result_check.lower():
            return brand
    return result_check


async def _translate_text(text: str, target_lang: str) -> str:
    """Translate a short text via Groq LLM. Returns original on failure."""
    try:
        from application.ports.llm import Message
        from infrastructure.llm.deps import get_llm_provider

        llm = get_llm_provider()
        lang_name = "German" if target_lang == "de" else "English"
        resp = await llm.complete(
            messages=[
                Message(
                    role="user",
                    content=f"Translate the following text to {lang_name}. Return ONLY the translation, no explanation:\n\n{text}",
                )
            ],
            max_tokens=512,
            temperature=0.0,
        )
        return resp.content.strip()
    except Exception as exc:
        logger.warning("news_translation_failed", error=str(exc))
        return text


def _detect_language(text: str) -> str:
    """Naive language detection based on common stop words."""
    text_lower = text.lower()
    de_words = {
        "der",
        "die",
        "das",
        "und",
        "ist",
        "ein",
        "eine",
        "im",
        "zu",
        "auf",
        "für",
        "von",
        "mit",
        "bei",
    }
    en_words = {"the", "and", "is", "in", "to", "of", "for", "with", "at", "by", "from"}
    words = set(text_lower.split())
    de_score = len(words & de_words)
    en_score = len(words & en_words)
    return "de" if de_score > en_score else "en"


def _company_name_in_text(search_name: str, text: str) -> bool:
    """Check if the company search name appears in the article title or summary.

    Requires at least one token of 4+ characters from the search name to be present.
    This catches false positives where a company name is a person's surname in an unrelated article.
    """
    import re

    tokens = [t for t in re.split(r"[\s,.\-]+", search_name) if len(t) >= 4]
    if not tokens:
        tokens = [search_name.strip()] if search_name.strip() else []
    text_lower = text.lower()
    return any(tok.lower() in text_lower for tok in tokens)


def _has_business_relevance(title: str, summary: str) -> bool:
    """Return True if the article is business-relevant.

    Filters out sports, entertainment, lifestyle, and personal news
    while keeping financial, operational, and ESG/compliance articles.
    """
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in _BUSINESS_KEYWORDS)


async def _fetch_gnews(client: httpx.AsyncClient, query: str, lang: str = "en") -> list[dict]:
    """Fetch articles from GNews API."""
    if not settings.gnews_api_key:
        return []
    try:
        resp = await client.get(
            _GNEWS_URL,
            params={
                "q": query,
                "lang": lang,
                "max": _GNEWS_MAX,
                "apikey": settings.gnews_api_key,
                "sortby": "publishedAt",
            },
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("gnews_error", status=resp.status_code, query=query)
            return []
        data = resp.json()
        return data.get("articles", [])
    except Exception as exc:
        logger.warning("gnews_fetch_failed", error=str(exc), query=query)
        return []


async def _fetch_gdelt(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Fetch articles from GDELT v2 DocSearch.

    GDELT enforces 1 request per 5 seconds. On 429, retries after 6s (up to 2 attempts).
    """
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": _GDELT_MAX,
        "sort": "DateDesc",
        "timespan": "14d",
    }

    for attempt in range(2):
        try:
            resp = await client.get(_GDELT_URL, params=params, timeout=_TIMEOUT)
            if resp.status_code == 429:
                logger.debug("gdelt_rate_limited", query=query[:40], attempt=attempt)
                await asyncio.sleep(6.0)
                continue
            text = resp.text.strip()
            if resp.status_code != 200 or not text or not text.startswith("{"):
                return []
            import json as _json

            data = _json.loads(text)
            articles = []
            for art in data.get("articles", []):
                articles.append(
                    {
                        "title": art.get("title", ""),
                        "description": art.get("seendescription", ""),
                        "url": art.get("url", ""),
                        "source": {"name": art.get("domain", "")},
                        "publishedAt": art.get("seendate", ""),
                        "image": None,
                    }
                )
            return articles
        except Exception as exc:
            logger.warning("gdelt_fetch_failed", error=str(exc), query=query[:40])
            return []

    return []


def _parse_published_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y%m%dT%H%M%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _article_id(url: str) -> str:
    """Deterministic ID from URL (first 36 chars of UUID5)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))


async def refresh_news_for_org(
    organization_id: str,
    session: AsyncSession,
    ui_language: str = "de",
) -> int:
    """Fetch, translate, assign and persist news for an organisation.

    Returns the number of new articles stored.
    """
    now = datetime.now(UTC)

    # 1. Load all active suppliers for this org
    result = await session.execute(
        select(SupplierModel).where(
            SupplierModel.organization_id == organization_id,
            SupplierModel.status.notin_(["Deleted", "Archived"]),
        )
    )
    suppliers = result.scalars().all()

    if not suppliers:
        return 0

    # 2. Build search queries
    # direct: supplier name
    # country: country name
    # partner: no partners stored yet → skip for now (future: supply chain network)
    supplier_queries: list[tuple[str, str, str]] = []  # (query, match_type, supplier_id)
    country_queries: list[tuple[str, str, list[str]]] = []  # (query, country, [supplier_ids])

    seen_countries: dict[str, list[str]] = {}
    for sup in suppliers:
        query_name = _search_name(sup.name)
        # GNews free tier: simple keyword query (no boolean operators)
        supplier_queries.append((query_name, query_name, "supplier", sup.id))
        if sup.country and len(sup.country) <= 3:
            country_name = _COUNTRY_NAMES.get(sup.country.upper(), sup.country)
            seen_countries.setdefault(country_name, []).append(sup.id)

    for country_name, sup_ids in seen_countries.items():
        # Append ESG suffix to make country queries more targeted
        country_query = f"{country_name} {_COUNTRY_ESG_SUFFIX}"
        country_queries.append((country_name, country_query, "country", sup_ids))

    # 3. Fetch existing article URLs to avoid duplicates
    cutoff = now - timedelta(days=_RETENTION_DAYS)
    existing_result = await session.execute(
        select(NewsArticleModel.url).where(
            NewsArticleModel.organization_id == organization_id,
            NewsArticleModel.fetched_at >= cutoff,
        )
    )
    existing_urls: set[str] = {row[0] for row in existing_result.all()}

    # 4. Delete articles older than retention period
    await session.execute(
        delete(NewsArticleModel).where(
            NewsArticleModel.organization_id == organization_id,
            NewsArticleModel.fetched_at < cutoff,
        )
    )

    new_count = 0

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # 4a. Supplier-specific news (GNews primary + GDELT secondary)
        # GDELT enforces 5s between requests; GNews free tier: 100 req/day
        for search_name, esg_query, match_type, supplier_id in supplier_queries:
            gnews_articles = await _fetch_gnews(client, search_name)
            await asyncio.sleep(6.0)  # GDELT: 1 request per 5 seconds minimum
            gdelt_articles = await _fetch_gdelt(client, search_name)
            await asyncio.sleep(1.0)
            raw_articles = gnews_articles + gdelt_articles

            for art in raw_articles:
                url = art.get("url", "")
                if not url or url in existing_urls:
                    continue

                title = art.get("title") or ""
                summary = art.get("description") or ""
                combined_text = title + " " + summary

                # Filter 1: company name must appear in title or summary
                if not _company_name_in_text(search_name, combined_text):
                    logger.debug("news_name_filtered", query=search_name, title=title[:60])
                    continue

                # Filter 2: article must mention at least one ESG/business-risk keyword
                if not _has_business_relevance(title, summary):
                    logger.debug("news_esg_filtered", query=search_name, title=title[:60])
                    continue

                existing_urls.add(url)
                detected_lang = _detect_language(combined_text)

                translated_title = None
                translated_summary = None
                if detected_lang != ui_language and title:
                    translated_title = await _translate_text(title, ui_language)
                if detected_lang != ui_language and summary:
                    translated_summary = await _translate_text(summary, ui_language)

                article = NewsArticleModel(
                    id=_article_id(url),
                    organization_id=organization_id,
                    title=title,
                    summary=summary or None,
                    url=url,
                    source_name=(art.get("source") or {}).get("name"),
                    image_url=art.get("image"),
                    published_at=_parse_published_at(art.get("publishedAt")),
                    fetched_at=now,
                    language=detected_lang,
                    translated_title=translated_title,
                    translated_summary=translated_summary,
                    match_type=match_type,
                    match_query=esg_query[:500],
                )
                session.add(article)

                assignment = NewsSupplierAssignmentModel(
                    id=str(uuid.uuid4()),
                    article_id=article.id,
                    supplier_id=supplier_id,
                    organization_id=organization_id,
                    match_reason="direct",
                )
                session.add(assignment)
                new_count += 1

        # 4b. Country-level news
        for country_name, country_query, _match_type_unused, sup_ids in country_queries:
            gnews_articles = await _fetch_gnews(client, f"{country_name} {_COUNTRY_ESG_SUFFIX}")
            await asyncio.sleep(6.0)
            gdelt_country = await _fetch_gdelt(client, f"{country_name} supply chain ESG")
            await asyncio.sleep(1.0)
            gnews_articles = gnews_articles + gdelt_country

            for art in gnews_articles:
                url = art.get("url", "")
                if not url or url in existing_urls:
                    continue

                title = art.get("title") or ""
                summary = art.get("description") or ""
                combined_text = title + " " + summary

                # Filter 1: country name must appear in title or summary
                if not _company_name_in_text(country_name, combined_text):
                    logger.debug(
                        "news_country_name_filtered", country=country_name, title=title[:60]
                    )
                    continue

                # Filter 2: at least one ESG keyword required for country-level articles
                if not _has_business_relevance(title, summary):
                    logger.debug(
                        "news_country_esg_filtered", country=country_name, title=title[:60]
                    )
                    continue

                existing_urls.add(url)
                detected_lang = _detect_language(title + " " + summary)

                translated_title = None
                translated_summary = None
                if detected_lang != ui_language and title:
                    translated_title = await _translate_text(title, ui_language)
                if detected_lang != ui_language and summary:
                    translated_summary = await _translate_text(summary, ui_language)

                article = NewsArticleModel(
                    id=_article_id(url),
                    organization_id=organization_id,
                    title=title,
                    summary=summary or None,
                    url=url,
                    source_name=(art.get("source") or {}).get("name"),
                    image_url=art.get("image"),
                    published_at=_parse_published_at(art.get("publishedAt")),
                    fetched_at=now,
                    language=detected_lang,
                    translated_title=translated_title,
                    translated_summary=translated_summary,
                    match_type="country",
                    match_query=country_query[:500],
                )
                session.add(article)

                for sup_id in sup_ids:
                    assignment = NewsSupplierAssignmentModel(
                        id=str(uuid.uuid4()),
                        article_id=article.id,
                        supplier_id=sup_id,
                        organization_id=organization_id,
                        match_reason="country",
                    )
                    session.add(assignment)

                new_count += 1

    await session.commit()
    logger.info("news_feed_refreshed", org=organization_id, new_articles=new_count)
    return new_count


async def get_news_feed(
    organization_id: str,
    session: AsyncSession,
    match_type: str | None = None,
    supplier_id: str | None = None,
    limit: int = 30,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return paginated news articles for an org with supplier assignments."""
    from sqlalchemy import func

    base_stmt = select(NewsArticleModel).where(
        NewsArticleModel.organization_id == organization_id,
    )

    if match_type:
        base_stmt = base_stmt.where(NewsArticleModel.match_type == match_type)

    if supplier_id:
        base_stmt = base_stmt.where(
            NewsArticleModel.id.in_(
                select(NewsSupplierAssignmentModel.article_id).where(
                    NewsSupplierAssignmentModel.supplier_id == supplier_id,
                    NewsSupplierAssignmentModel.organization_id == organization_id,
                )
            )
        )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one() or 0

    stmt = (
        base_stmt.order_by(
            NewsArticleModel.published_at.desc().nullslast(),
            NewsArticleModel.fetched_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    rows = (await session.execute(stmt)).scalars().all()

    # Load supplier assignments for these articles
    article_ids = [r.id for r in rows]
    assign_result = await session.execute(
        select(NewsSupplierAssignmentModel).where(
            NewsSupplierAssignmentModel.article_id.in_(article_ids),
            NewsSupplierAssignmentModel.organization_id == organization_id,
        )
    )
    assignments = assign_result.scalars().all()

    assign_map: dict[str, list[dict]] = {}
    for a in assignments:
        assign_map.setdefault(a.article_id, []).append(
            {
                "supplier_id": a.supplier_id,
                "match_reason": a.match_reason,
            }
        )

    # Load supplier names
    if article_ids:
        all_sup_ids = {a.supplier_id for a in assignments}
        sup_result = await session.execute(
            select(SupplierModel.id, SupplierModel.name).where(SupplierModel.id.in_(all_sup_ids))
        )
        sup_names = {row[0]: row[1] for row in sup_result.all()}
    else:
        sup_names = {}

    articles = []
    for row in rows:
        sups = assign_map.get(row.id, [])
        articles.append(
            {
                "id": row.id,
                "title": row.title,
                "translated_title": row.translated_title,
                "summary": row.summary,
                "translated_summary": row.translated_summary,
                "url": row.url,
                "source_name": row.source_name,
                "image_url": row.image_url,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "fetched_at": row.fetched_at.isoformat(),
                "language": row.language,
                "match_type": row.match_type,
                "suppliers": [
                    {
                        "id": s["supplier_id"],
                        "name": sup_names.get(s["supplier_id"], s["supplier_id"]),
                        "match_reason": s["match_reason"],
                    }
                    for s in sups
                ],
            }
        )

    return articles, total


async def get_last_refresh(organization_id: str, session: AsyncSession) -> datetime | None:
    result = await session.execute(
        select(NewsArticleModel.fetched_at)
        .where(NewsArticleModel.organization_id == organization_id)
        .order_by(NewsArticleModel.fetched_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


# ISO 3166-1 alpha-2 → readable country name for better search queries
_COUNTRY_NAMES: dict[str, str] = {
    "DE": "Germany",
    "US": "United States",
    "CN": "China",
    "JP": "Japan",
    "GB": "United Kingdom",
    "FR": "France",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "CH": "Switzerland",
    "AT": "Austria",
    "BE": "Belgium",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "HU": "Hungary",
    "RO": "Romania",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "PT": "Portugal",
    "GR": "Greece",
    "TR": "Turkey",
    "RU": "Russia",
    "UA": "Ukraine",
    "IN": "India",
    "KR": "South Korea",
    "TW": "Taiwan",
    "MX": "Mexico",
    "BR": "Brazil",
    "AR": "Argentina",
    "ZA": "South Africa",
    "NG": "Nigeria",
    "EG": "Egypt",
    "SA": "Saudi Arabia",
    "AE": "UAE",
    "AU": "Australia",
    "NZ": "New Zealand",
    "SG": "Singapore",
    "MY": "Malaysia",
    "TH": "Thailand",
    "VN": "Vietnam",
    "ID": "Indonesia",
    "PH": "Philippines",
    "CD": "Democratic Republic of Congo",
    "CG": "Republic of Congo",
    "ET": "Ethiopia",
    "KE": "Kenya",
    "TZ": "Tanzania",
    "GH": "Ghana",
    "MA": "Morocco",
    "TN": "Tunisia",
    "DZ": "Algeria",
    "LY": "Libya",
    "IQ": "Iraq",
    "IR": "Iran",
    "PK": "Pakistan",
    "BD": "Bangladesh",
    "MM": "Myanmar",
    "KH": "Cambodia",
    "LA": "Laos",
}
