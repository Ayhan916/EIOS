"""
M27 Suppliers API

Supplier is the primary subject of ESG due diligence in EIOS.
All endpoints enforce tenant isolation — users only see their own org's suppliers.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime

import httpx
import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import application.audit as audit_events
from domain.enums import EntityStatus, SupplierStatus
from domain.supplier import Supplier
from domain.user import User
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLSupplierRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_audit_event_repo,
    get_current_user,
    get_db,
    get_supplier_repo,
    require_analyst,
    scope_gate,
)
from interfaces.api.routers.api_platform import dispatch_webhook_event
from interfaces.api.schemas.pagination import Page, PaginationParams
from interfaces.api.schemas.supplier import (
    SupplierCreate,
    SupplierResponse,
    SupplierRiskProfile,
    SupplierUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("suppliers:read", "suppliers:write")),
    ],
)


_MAX_SYNC_ROWS = 100  # rows above this threshold are processed async via Celery

# ── Global company search (GLEIF proxy) ──────────────────────────────────────


_GLEIF_URL = "https://api.gleif.org/api/v1/lei-records"
_GLEIF_FUZZY_URL = "https://api.gleif.org/api/v1/fuzzycompletions"

# Abbreviation → full legal form (German + international)
_LEGAL_ABBREV: dict[str, str] = {
    "AG": "Aktiengesellschaft",
    "GMBH": "GmbH",
    "SE": "SE",
    "KGAA": "KGaA",
    "KG": "KG",
    "OHG": "OHG",
    "EV": "e.V.",
    "LLC": "LLC",
    "INC": "Inc",
    "LTD": "Limited",
    "CORP": "Corp",
    "BV": "B.V.",
    "NV": "N.V.",
    "SAS": "SAS",
    "SRL": "S.r.l.",
    "SA": "S.A.",
    "PLC": "PLC",
    "AB": "Aktiebolag",  # Swedish AG
    "AS": "Aksjeselskap",  # Norwegian AS
    "OY": "Oy",  # Finnish
    "OYJ": "Oyj",  # Finnish listed
    "OÜ": "OÜ",  # Estonian
    "SIA": "SIA",  # Latvian
}


# Brand/trade name → GLEIF legal name (full query replacement when query matches exactly)
_BRAND_ALIASES: dict[str, str] = {
    "BMW": "Bayerische Motoren Werke",
    "VW": "Volkswagen",
    "MERCEDES": "Mercedes-Benz",
    "DAIMLER": "Mercedes-Benz Group",
    "DB": "Deutsche Bahn",
    "DHL": "Deutsche Post",
    "TELEKOM": "Deutsche Telekom",
    "BAYER": "Bayer",
    "MAN": "MAN SE",
    "PORSCHE": "Porsche",
    "AUDI": "AUDI",
    "OPEL": "Opel",
    "CONTINENTAL": "Continental",
    "ZF": "ZF Friedrichshafen",
    "SCHAEFFLER": "Schaeffler",
    "MAHLE": "MAHLE",
    "HELLA": "HELLA",
    "BYD": "BYD",
    "TESLA": "Tesla",
    "CATL": "Contemporary Amperex Technology",
    "TSMC": "Taiwan Semiconductor Manufacturing",
    "SAMSUNG": "Samsung",
    "LG": "LG Electronics",
    "SONY": "Sony",
    "TOYOTA": "Toyota",
    "HONDA": "Honda",
    "NISSAN": "Nissan",
    "HYUNDAI": "Hyundai",
    "KIA": "Kia",
    "VOLVO": "Volvo",
    "RENAULT": "Renault",
    "PSA": "Stellantis",
    "STELLANTIS": "Stellantis",
    "FIAT": "Stellantis",
    "P&G": "Procter & Gamble",
    "J&J": "Johnson & Johnson",
    "3M": "3M",
    "GE": "General Electric",
    "GM": "General Motors",
    "IBM": "International Business Machines",
    "ABB": "ABB",
    "SKF": "SKF",
    "HENKEL": "Henkel",
    "FRESENIUS": "Fresenius",
    "EON": "E.ON",
    "RWE": "RWE",
    "ENBW": "EnBW",
    "VATTENFALL": "Vattenfall",
    "ALLIANZ": "Allianz",
    "MUNICH RE": "Münchener Rückversicherungs",
    "MUNICHRE": "Münchener Rückversicherungs",
    "DZ BANK": "DZ BANK",
    "COMMERZBANK": "Commerzbank",
}


def _expand_abbrevs(q: str) -> str:
    """Expand legal form abbreviations word-by-word.
    'Siemens AG' → 'Siemens Aktiengesellschaft'
    """
    words = q.split()
    expanded = []
    for w in words:
        key = w.upper().rstrip(".")
        expanded.append(_LEGAL_ABBREV.get(key, w))
    return " ".join(expanded)


def _brand_expand(q: str) -> str | None:
    """Return expanded brand name for well-known trade abbreviations, or None.
    'BMW' → 'Bayerische Motoren Werke'
    'VW AG' → 'Volkswagen Aktiengesellschaft'
    """
    q_stripped = q.strip()
    upper = q_stripped.upper()
    # Exact match
    if upper in _BRAND_ALIASES:
        return _BRAND_ALIASES[upper]
    # Match with trailing legal form: "BMW AG" → base "BMW" + suffix " AG"
    parts = q_stripped.split()
    if len(parts) >= 2:
        base = parts[0].upper()
        suffix = " ".join(parts[1:])
        if base in _BRAND_ALIASES:
            return f"{_BRAND_ALIASES[base]} {suffix}"
    return None


_LEGAL_FORM_RE = re.compile(
    r"\b(GmbH|AG|SE|KGaA|KG|OHG|GbR|Inc\.?|Ltd\.?|Corp\.?|S\.A\.?|B\.V\.?|NV|PLC|LLC|LP|LLP|SAS|SRL|SpA)\b\.?\s*$",
    re.IGNORECASE,
)


# Canonical LEI registry: maps normalized search terms → (LEI, country, city, full_name)
# Verified via GLEIF API — these are the official HQ parent entities.
_CANONICAL: dict[str, tuple[str, str, str, str]] = {
    # key (upper, stripped)        LEI                        country  city            full legal name
    "VOLKSWAGEN": ("529900NNUPAGGOMPXZ31", "DE", "Wolfsburg", "VOLKSWAGEN AKTIENGESELLSCHAFT"),
    "VW": ("529900NNUPAGGOMPXZ31", "DE", "Wolfsburg", "VOLKSWAGEN AKTIENGESELLSCHAFT"),
    "BMW": ("YEH5ZCD6E441RHVHD759", "DE", "Munich", "Bayerische Motoren Werke Aktiengesellschaft"),
    "BAYERISCHE MOTOREN WERKE": (
        "YEH5ZCD6E441RHVHD759",
        "DE",
        "Munich",
        "Bayerische Motoren Werke Aktiengesellschaft",
    ),
    "MERCEDES": ("529900R27DL06UVNT076", "DE", "Stuttgart", "Mercedes-Benz Group AG"),
    "MERCEDES-BENZ": ("529900R27DL06UVNT076", "DE", "Stuttgart", "Mercedes-Benz Group AG"),
    "SIEMENS": ("W38RGI023J3WT1HWRP32", "DE", "Munich", "Siemens Aktiengesellschaft"),
    "SAP": ("529900D6BF99LW9R2E68", "DE", "Walldorf", "SAP SE"),
    "BASF": ("529900PM64WH8AF1E917", "DE", "Ludwigshafen", "BASF SE"),
    "BAYER": ("549300J4U55H3WP1XT59", "DE", "Leverkusen", "Bayer Aktiengesellschaft"),
    "DEUTSCHE BANK": (
        "529900IH9V4I3VHQVO92",
        "DE",
        "Frankfurt",
        "Deutsche Bank Aktiengesellschaft",
    ),
    "ALLIANZ": ("529900K9B0N5BT694847", "DE", "Munich", "Allianz SE"),
    "DEUTSCHE TELEKOM": ("549300V9QSIG4WX4GJ96", "DE", "Bonn", "DEUTSCHE TELEKOM AG"),
    "TELEKOM": ("549300V9QSIG4WX4GJ96", "DE", "Bonn", "DEUTSCHE TELEKOM AG"),
    "LUFTHANSA": (
        "529900PH63HYJ86ASW55",
        "DE",
        "Frankfurt",
        "Deutsche Lufthansa Aktiengesellschaft",
    ),
    "DEUTSCHE LUFTHANSA": (
        "529900PH63HYJ86ASW55",
        "DE",
        "Frankfurt",
        "Deutsche Lufthansa Aktiengesellschaft",
    ),
    "CONTINENTAL": ("529900A7YD9C0LLXC421", "DE", "Hanover", "Continental Aktiengesellschaft"),
    "AIRBUS": ("MINO79WLOO247M1IL051", "NL", "Leiden", "AIRBUS SE"),
    "HENKEL": ("549300VZCL1HTH4O4Y49", "DE", "Düsseldorf", "Henkel AG & Co. KGaA"),
    "INFINEON": ("TSI2PJM6EPETEQ4X1U25", "DE", "Neubiberg", "Infineon Technologies AG"),
    "FRESENIUS": ("XDFJ0CYCOO1FXRFTQS51", "DE", "Bad Homburg", "Fresenius SE & Co. KGaA"),
    "COMMERZBANK": ("851WYGNLUQLFZBSYGB56", "DE", "Frankfurt", "COMMERZBANK Aktiengesellschaft"),
    "PORSCHE": (
        "529900EWEX125AULXI58",
        "DE",
        "Stuttgart",
        "Dr. Ing. h.c. F. Porsche Aktiengesellschaft",
    ),
    "DAIMLER TRUCK": ("529900PW78JIYOUBSR24", "DE", "Stuttgart", "Daimler Truck Holding AG"),
    "HEIDELBERG MATERIALS": ("LZ2C6E0W5W7LQMX5ZI37", "DE", "Heidelberg", "Heidelberg Materials AG"),
    "BEIERSDORF": ("L47NHHI0Z9X22DV46U41", "DE", "Hamburg", "Beiersdorf Aktiengesellschaft"),
    "BOSCH": ("9845006FDEADE15CA138", "DE", "Stuttgart", "Robert Bosch GmbH"),
    "ROBERT BOSCH": ("9845006FDEADE15CA138", "DE", "Stuttgart", "Robert Bosch GmbH"),
}

# Words in company names that signal a subsidiary (not the main HQ entity)
_SUBSIDIARY_KEYWORDS = frozenset(
    {
        "finance",
        "financial",
        "leasing",
        "holding",
        "holdings",
        "capital",
        "insurance",
        "bank",
        "versicherung",
        "kredit",
        "invest",
        "investments",
        "asset",
        "fund",
        "realty",
        "properties",
        "real estate",
        "solutions",
        "services",
        "service",
        "consulting",
        "research",
        "ventures",
        "venture",
        "trading",
        "international",
        "global",
        "logistics",
        "distribution",
        "manufacturing",
        "production",
        "procurement",
        "purchasing",
    }
)


def _gleif_score(name: str, q: str, category: str = "") -> int:
    """
    Relevance score 0-200. Higher = better.
    Factors: name match, category (GENERAL > BRANCH), subsidiary penalty.
    """
    n = name.lower()
    base = 0

    # Name match — try original and abbrev-expanded query
    for query in {q.lower(), _expand_abbrevs(q).lower()}:
        if n == query:
            base = max(base, 100)
        elif n.startswith(query + " ") or n.startswith(query + ","):
            base = max(base, 90)
        else:
            words = [w for w in query.split() if len(w) > 1]
            if words and all(w in n for w in words):
                pos = max(n.find(w) for w in words)
                base = max(base, max(70 - pos, 10))

    if base == 0:
        return 0

    # Category bonus/penalty
    if category == "GENERAL":
        base += 30
    elif category == "BRANCH":
        base -= 25
    elif category == "FUND":
        base -= 20

    # Subsidiary name penalty: lower score if name contains subsidiary keywords
    # that the user's query did NOT mention
    q_lower = q.lower()
    name_words = set(n.split())
    for kw in _SUBSIDIARY_KEYWORDS:
        if kw in name_words and kw not in q_lower:
            base -= 15
            break  # one penalty is enough

    # Short-name bonus: parent companies tend to have shorter names
    # (e.g. "Volkswagen Aktiengesellschaft" < "Volkswagen AirService GmbH & Co. KG")
    base -= max(0, len(name) - 40) // 5

    return base


async def _gleif_search(
    client: httpx.AsyncClient,
    q: str,
    size: int = 25,
    country: str | None = None,
    category: str | None = None,
) -> list[dict]:
    params: dict[str, str | int] = {
        "filter[entity.legalName]": q,
        "page[size]": size,
        "filter[entity.status]": "ACTIVE",
    }
    if country:
        params["filter[entity.legalAddress.country]"] = country
    if category:
        params["filter[entity.category]"] = category
    resp = await client.get(
        _GLEIF_URL,
        params=params,
        headers={"Accept": "application/vnd.api+json"},
        timeout=8.0,
    )
    resp.raise_for_status()
    out = []
    for r in resp.json().get("data", []):
        attrs = r.get("attributes", {})
        entity = attrs.get("entity", {})
        addr = entity.get("legalAddress", {})
        out.append(
            {
                "lei": attrs.get("lei", ""),
                "name": entity.get("legalName", {}).get("name", ""),
                "country": addr.get("country", ""),
                "city": addr.get("city", ""),
                "jurisdiction": entity.get("legalJurisdiction", ""),
                "category": entity.get("category", ""),
            }
        )
    return out


async def _gleif_fuzzy_search(client: httpx.AsyncClient, q: str, size: int = 15) -> list[dict]:
    """
    Uses GLEIF's fuzzy-completions endpoint — finds 'Siemens Aktiengesellschaft'
    even when the user types 'Siemens AG', handles abbreviations and typos.
    Returns list of {lei, name}; country/city fetched separately for top hits.
    """
    resp = await client.get(
        _GLEIF_FUZZY_URL,
        params={"field": "entity.legalName", "q": q, "page[size]": size},
        headers={"Accept": "application/vnd.api+json"},
        timeout=6.0,
    )
    if resp.status_code != 200:
        return []
    out = []
    for item in resp.json().get("data", []):
        lei = item.get("relationships", {}).get("lei-records", {}).get("data", {}).get("id", "")
        name = item.get("attributes", {}).get("value", "")
        if lei and name:
            out.append({"lei": lei, "name": name, "country": "", "city": "", "jurisdiction": ""})
    return out


async def _gleif_enrich_lei(client: httpx.AsyncClient, lei: str) -> dict:
    """Fetch country, city, category and parent relationship for a single LEI record."""
    resp = await client.get(
        f"{_GLEIF_URL}/{lei}",
        headers={"Accept": "application/vnd.api+json"},
        timeout=5.0,
    )
    if resp.status_code != 200:
        return {}
    data = resp.json().get("data", {})
    attrs = data.get("attributes", {})
    entity = attrs.get("entity", {})
    addr = entity.get("legalAddress", {})
    category = entity.get("category", "")
    # directParent.data is non-null when the entity has a parent in GLEIF
    has_parent = bool(data.get("relationships", {}).get("directParent", {}).get("data"))
    return {
        "country": addr.get("country", ""),
        "city": addr.get("city", ""),
        "category": category,
        "has_parent": has_parent,
    }


def _tier_from_gleif(category: str, has_parent: bool) -> str:
    """Derive SupplierTier from GLEIF entity data.

    BRANCH (Niederlassung) → Tier 3
    Has a directParent in GLEIF (= Tochtergesellschaft) → Tier 2
    Standalone / ultimate parent → Tier 1
    """
    if category == "BRANCH":
        return "Tier 3"
    if has_parent:
        return "Tier 2"
    return "Tier 1"


@router.get("/company-search", response_model=list[dict])
async def company_search(
    q: str = Query(..., min_length=2, max_length=100),
    country: str = Query(default="", max_length=2),
    legal_form: str = Query(default="", max_length=30),
    category: str = Query(default="", max_length=30),
    _current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Hybrid search: fuzzy-completions (finds 'Siemens Aktiengesellschaft' for 'Siemens AG')
    merged with filter search (provides country/city). Top fuzzy hits get enriched.
    """
    q = q.strip()
    country_filter = country.strip().upper() or None
    effective_q = f"{q} {legal_form}".strip() if legal_form else q
    fuzzy_q = _expand_abbrevs(effective_q)
    brand_q = _brand_expand(effective_q)

    # ── Canonical lookup: pin the verified HQ entity to position 0 ──────────────
    canonical_key = effective_q.upper().strip()
    # Also try without legal form suffix: "Volkswagen AG" → "VOLKSWAGEN"
    canonical_base = _LEGAL_FORM_RE.sub("", canonical_key).strip()
    canonical_hit: dict | None = None
    for ck in (canonical_key, canonical_base):
        if ck in _CANONICAL:
            lei, c_country, c_city, c_name = _CANONICAL[ck]
            if not country_filter or country_filter == c_country:
                canonical_hit = {
                    "lei": lei,
                    "name": c_name,
                    "country": c_country,
                    "city": c_city,
                    "jurisdiction": c_country,
                    "category": "GENERAL",
                }
            break

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            use_brand = bool(brand_q and brand_q.lower() != fuzzy_q.lower())
            coros = [
                _gleif_fuzzy_search(client, fuzzy_q),
                _gleif_search(
                    client, effective_q, country=country_filter, category=category or None
                ),
                *([_gleif_fuzzy_search(client, _expand_abbrevs(brand_q))] if use_brand else []),
            ]
            results = await asyncio.gather(*coros)
            fuzzy_results: list[dict] = results[0]
            filter_results: list[dict] = results[1]
            brand_results: list[dict] = results[2] if use_brand else []

            lei_data: dict[str, dict] = {r["lei"]: r for r in filter_results}
            merged: list[dict] = []
            seen: set[str] = set()

            # Canonical entry goes first (if found), skip it from remaining results
            if canonical_hit:
                seen.add(canonical_hit["lei"])
                # Prefer filter_results version (has full data incl. category)
                merged.append(lei_data.get(canonical_hit["lei"], canonical_hit))

            for r in brand_results + fuzzy_results:
                if r["lei"] in seen:
                    continue
                seen.add(r["lei"])
                merged.append(lei_data.get(r["lei"], r))

            for r in filter_results:
                if r["lei"] not in seen:
                    seen.add(r["lei"])
                    merged.append(r)

            # Fallback retry without legal form suffix
            if not merged:
                stripped_q = _LEGAL_FORM_RE.sub("", effective_q).strip()
                if stripped_q != effective_q and len(stripped_q) >= 2:
                    filter_results, fuzzy_results = await asyncio.gather(
                        _gleif_search(
                            client, stripped_q, country=country_filter, category=category or None
                        ),
                        _gleif_fuzzy_search(client, _expand_abbrevs(stripped_q)),
                    )
                    lei_data = {r["lei"]: r for r in filter_results}
                    for r in fuzzy_results + filter_results:
                        if r["lei"] not in seen:
                            seen.add(r["lei"])
                            merged.append(lei_data.get(r["lei"], r))

            # Enrich top hits missing country/city — also fetches category
            to_enrich = [r for r in merged if not r["country"]][:5]
            if to_enrich:
                enriched = await asyncio.gather(
                    *[_gleif_enrich_lei(client, r["lei"]) for r in to_enrich]
                )
                for r, extra in zip(to_enrich, enriched, strict=False):
                    r.update(extra)

            if country_filter:
                # Keep canonical even if country unknown; filter the rest
                merged = [r for r in merged if not r["country"] or r["country"] == country_filter]

    except Exception:
        raise HTTPException(status_code=503, detail="Company search service unavailable")

    # Sort: canonical stays at [0] (already pinned), rest sorted by score
    if canonical_hit and merged and merged[0]["lei"] == canonical_hit["lei"]:
        rest = sorted(
            merged[1:],
            key=lambda r: _gleif_score(r["name"], effective_q, r.get("category", "")),
            reverse=True,
        )
        merged = [merged[0]] + rest
    else:
        merged.sort(
            key=lambda r: _gleif_score(r["name"], effective_q, r.get("category", "")), reverse=True
        )

    return merged[:20]


@router.get("/company-detail", response_model=dict)
async def company_detail(
    lei: str = Query(..., min_length=5, max_length=30),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Full GLEIF details for a company plus its direct children (subsidiaries/locations)."""
    headers = {"Accept": "application/vnd.api+json"}
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        lei_resp, children_resp = await asyncio.gather(
            client.get(f"{_GLEIF_URL}/{lei}", headers=headers, timeout=6.0),
            client.get(
                f"{_GLEIF_URL}/{lei}/direct-children",
                params={"page[size]": 100, "filter[entity.status]": "ACTIVE"},
                headers=headers,
                timeout=10.0,
            ),
        )

    company: dict = {}
    if lei_resp.status_code == 200:
        data = lei_resp.json().get("data", {})
        attrs = data.get("attributes", {})
        entity = attrs.get("entity", {})
        addr = entity.get("legalAddress", {})
        reg_addr = entity.get("headquartersAddress", addr)
        company = {
            "lei": attrs.get("lei", lei),
            "name": entity.get("legalName", {}).get("name", ""),
            "country": addr.get("country", ""),
            "city": addr.get("city", ""),
            "postal_code": addr.get("postalCode", ""),
            "address_lines": addr.get("addressLines", []),
            "hq_city": reg_addr.get("city", ""),
            "hq_country": reg_addr.get("country", ""),
            "status": entity.get("status", "ACTIVE"),
            "category": entity.get("category", ""),
            "jurisdiction": entity.get("legalJurisdiction", ""),
            "legal_form": entity.get("legalForm", {}).get("id", ""),
            "registration_date": attrs.get("registration", {}).get("initialRegistrationDate", ""),
        }

    children: list[dict] = []
    total_children = 0
    if children_resp.status_code == 200:
        body = children_resp.json()
        total_children = body.get("meta", {}).get("pagination", {}).get("total", 0)
        for r in body.get("data", []):
            a = r.get("attributes", {})
            e = a.get("entity", {})
            addr = e.get("legalAddress", {})
            children.append(
                {
                    "lei": a.get("lei", ""),
                    "name": e.get("legalName", {}).get("name", ""),
                    "country": addr.get("country", ""),
                    "city": addr.get("city", ""),
                    "status": e.get("status", "ACTIVE"),
                    "category": e.get("category", ""),
                }
            )
        children.sort(key=lambda x: (x["country"], x["name"]))

    return {"company": company, "children": children, "total_children": total_children}


_WD_API = "https://www.wikidata.org/w/api.php"
_WD_HEADERS = {"User-Agent": "EIOS-Compliance/1.0 (contact@eios.io)"}

# Wikidata P452 (industry) QID → (NACE code, German label)
# Only QIDs verified via Wikidata API (label confirmed correct).
_NACE_BY_QID: dict[str, tuple[str, str]] = {
    # Manufacturing C — verified
    "Q43035": ("C27", "Herstellung von elektrischen Ausrüstungen"),  # Elektrotechnik
    "Q609131": ("C28", "Maschinenbau"),  # Antriebstechnik
    "Q327092": ("C26.60", "Herstellung von medizinischen Instrumenten"),  # Medizintechnik
    "Q1786253": ("C27", "Herstellung von elektrischen Ausrüstungen"),  # Kraftwerkstechnik
    "Q101333": ("C28", "Maschinenbau"),  # Maschinenbau
    "Q17177506": ("C27.40", "Herstellung von Beleuchtungskörpern"),  # Lichttechnik
    "Q2986369": ("C26.11", "Herstellung von elektronischen Bauelementen"),  # Halbleiterindustrie
    "Q3477381": ("C29.32", "Herst. sonstiger Teile/Zubehör für Kraftwagen"),  # Autozulieferer
    "Q56604188": ("C27.51", "Herstellung von elektrischen Haushaltsgeräten"),  # Hausgeräteindustrie
    "Q190117": ("C29", "Herstellung von Kraftwagen und Kraftwagenteilen"),  # Automobilindustrie
    "Q207652": ("C20", "Herstellung von chemischen Erzeugnissen"),  # Chemische Industrie
    "Q1349660": ("B06", "Gewinnung von Erdöl und Erdgas"),  # Erdölgewinnung
    "Q1944497": ("A01.61", "Pflanzliche Erzeugnisse"),  # Pflanzenschutz
    "Q507443": ("C21", "Herst. von pharmazeutischen Erzeugnissen"),  # Pharmaindustrie
}

# Industry label keyword → NACE fallback (when QID not in mapping above).
# Order matters: more specific terms must come before general ones.
# KEY FIX: use "chemi" not "chemie" — "Chemische Industrie" contains "chemi" but not "chemie"
_NACE_BY_KEYWORD: list[tuple[str, str, str]] = [
    # Manufacturing (most specific first)
    ("medizintechnik", "C26.60", "Herstellung von medizinischen Instrumenten"),
    ("halbleiter", "C26.11", "Herstellung von elektronischen Bauelementen"),
    ("semiconductor", "C26.11", "Herstellung von elektronischen Bauelementen"),
    ("autozulieferer", "C29.32", "Herst. sonstiger Teile/Zubehör für Kraftwagen"),
    ("hausgerät", "C27.51", "Herstellung von elektrischen Haushaltsgeräten"),
    ("luft- und raum", "C30.30", "Luft- und Raumfahrzeugbau"),
    ("aerospace", "C30.30", "Luft- und Raumfahrzeugbau"),
    ("raumfahrt", "C30.30", "Luft- und Raumfahrzeugbau"),
    ("pharma", "C21", "Herst. von pharmazeutischen Erzeugnissen"),
    ("elektrotechnik", "C27", "Herstellung von elektrischen Ausrüstungen"),
    ("elektrisch", "C27", "Herstellung von elektrischen Ausrüstungen"),
    ("antriebstechnik", "C28", "Maschinenbau"),
    ("maschinenbau", "C28", "Maschinenbau"),
    ("automobil", "C29", "Herstellung von Kraftwagen und Kraftwagenteilen"),
    ("automotive", "C29", "Herstellung von Kraftwagen und Kraftwagenteilen"),
    ("fahrzeugbau", "C29", "Herstellung von Kraftwagen und Kraftwagenteilen"),
    ("elektronik", "C26", "Herst. von Datenverarbeitungsger./elektr. Optik"),
    ("electronic", "C26", "Herst. von Datenverarbeitungsger./elektr. Optik"),
    ("software", "J62", "Erbringung von IT-Dienstleistungen"),
    ("informationstechnolog", "J62", "Erbringung von IT-Dienstleistungen"),
    ("chemi", "C20", "Herstellung von chemischen Erzeugnissen"),  # matches "Chemische", "Chemie"
    ("chemical", "C20", "Herstellung von chemischen Erzeugnissen"),
    ("stahlindustrie", "C24", "Metallerzeugung und -bearbeitung"),
    ("stahl", "C24", "Metallerzeugung und -bearbeitung"),
    ("metallindustrie", "C25", "Herstellung von Metallerzeugnissen"),
    ("kunststoff", "C22", "Herstellung von Gummi- und Kunststoffwaren"),
    ("nahrungsmittel", "C10", "Ernährungsgewerbe"),
    ("lebensmittel", "C10", "Ernährungsgewerbe"),
    ("food", "C10", "Ernährungsgewerbe"),
    ("getränk", "C11", "Getränkeherstellung"),
    ("textil", "C13", "Herstellung von Textilien"),
    ("bekleidung", "C14", "Herstellung von Bekleidung"),
    ("papier", "C17", "Papiergewerbe"),
    ("erdöl", "B06", "Gewinnung von Erdöl und Erdgas"),
    ("petroleum", "B06", "Gewinnung von Erdöl und Erdgas"),
    # Energy D
    ("energieversorgu", "D35", "Energieversorgung"),
    ("energiewirtschaft", "D35", "Energieversorgung"),
    ("energie", "D35", "Energieversorgung"),
    ("energy", "D35", "Energieversorgung"),
    # Construction F
    ("bauwirtschaft", "F41", "Hochbau"),
    ("construction", "F41", "Hochbau"),
    # Trade G
    ("einzelhandel", "G47", "Einzelhandel"),
    ("großhandel", "G46", "Großhandel"),
    ("handel", "G46", "Großhandel"),
    # Transport H
    ("luftfahrt", "H51", "Luftfahrt"),
    ("schifffahrt", "H50", "Schifffahrt"),
    ("logistik", "H52", "Lagerei sowie sonstige Dienstleistungen"),
    ("transport", "H49", "Landverkehr und Transport"),
    # Finance K
    ("bankwesen", "K64", "Erbringung von Finanzdienstleistungen"),
    ("bank", "K64", "Erbringung von Finanzdienstleistungen"),
    ("finanzdienstleistung", "K64", "Erbringung von Finanzdienstleistungen"),
    ("versicherung", "K65", "Versicherungen, Rückversicherungen"),
    ("insurance", "K65", "Versicherungen, Rückversicherungen"),
    # Real Estate L
    ("immobilien", "L68", "Grundstücks- und Wohnungswesen"),
    ("real estate", "L68", "Grundstücks- und Wohnungswesen"),
    # Professional M
    ("forschung", "M72", "Forschung und Entwicklung"),
    ("research", "M72", "Forschung und Entwicklung"),
    ("unternehmensberatung", "M70", "Verwaltung und Führung von Unternehmen"),
    ("consulting", "M70", "Verwaltung und Führung von Unternehmen"),
    ("ingenieur", "M71", "Architektur- und Ingenieurbüros"),
    # Healthcare Q
    ("gesundheitswesen", "Q86", "Gesundheitswesen"),
    ("gesundheit", "Q86", "Gesundheitswesen"),
    ("health care", "Q86", "Gesundheitswesen"),
    # Agriculture A
    ("landwirtschaft", "A01", "Landwirtschaft"),
    ("pflanzenschutz", "A01.61", "Pflanzliche Erzeugnisse"),
]


def _resolve_nace(industry_qids: list[str], industry_label: str) -> tuple[str, str]:
    """Return (nace_code, nace_label) using QID lookup then keyword fallback."""
    for qid in industry_qids:
        if qid in _NACE_BY_QID:
            return _NACE_BY_QID[qid]
    label_lower = industry_label.lower()
    for keyword, code, label in _NACE_BY_KEYWORD:
        if keyword in label_lower:
            return code, label
    return "", ""


async def _find_wikidata_qid(client: httpx.AsyncClient, lei: str, name: str) -> str | None:
    """Return the Wikidata Q-ID for a company, trying LEI first then name search."""
    # 1. By LEI via SPARQL
    if lei:
        try:
            sparql = f'SELECT ?item WHERE {{ ?item wdt:P1278 "{lei}" }} LIMIT 1'
            resp = await client.get(
                "https://query.wikidata.org/sparql",
                params={"query": sparql, "format": "json"},
                headers={**_WD_HEADERS, "Accept": "application/sparql-results+json"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                bindings = resp.json().get("results", {}).get("bindings", [])
                if bindings:
                    return bindings[0]["item"]["value"].split("/")[-1]
        except Exception:
            pass

    # 2. By name via wbsearchentities (try original + title-cased)
    for search_term in dict.fromkeys([name, name.title()]):
        try:
            resp = await client.get(
                _WD_API,
                params={
                    "action": "wbsearchentities",
                    "search": search_term,
                    "language": "de",
                    "type": "item",
                    "format": "json",
                    "limit": "1",
                },
                headers=_WD_HEADERS,
                timeout=5.0,
            )
            if resp.status_code == 200:
                results = resp.json().get("search", [])
                if results:
                    return results[0]["id"]
        except Exception:
            continue
    return None


async def _fetch_entity(client: httpx.AsyncClient, qid: str) -> dict:
    # Build URL manually so pipe separators stay literal (httpx would encode them)
    url = (
        f"{_WD_API}?action=wbgetentities&ids={qid}"
        "&props=claims|descriptions|sitelinks"
        "&languages=de|en&sitefilter=dewiki|enwiki&format=json"
    )
    resp = await client.get(url, headers=_WD_HEADERS, timeout=6.0)
    resp.raise_for_status()
    return resp.json().get("entities", {}).get(qid, {})


async def _label_for_qids(client: httpx.AsyncClient, qids: list[str]) -> str:
    if not qids:
        return ""
    resp = await client.get(
        _WD_API,
        params={
            "action": "wbgetentities",
            "ids": "|".join(qids[:3]),
            "props": "labels",
            "languages": "de|en",
            "format": "json",
        },
        headers=_WD_HEADERS,
        timeout=4.0,
    )
    if resp.status_code != 200:
        return ""
    entities = resp.json().get("entities", {})
    labels = []
    for qid in qids[:3]:
        ent = entities.get(qid, {})
        lbl = ent.get("labels", {}).get("de", {}).get("value", "") or ent.get("labels", {}).get(
            "en", {}
        ).get("value", "")
        if lbl:
            labels.append(lbl)
    return ", ".join(labels)


_WIKI_HEADERS = {
    "User-Agent": "EIOS-Compliance/1.0 (contact@eios.io)",
    "Accept": "application/json",
}
_LEGAL_SUFFIXES = re.compile(
    r"\s+(AG|SE|GmbH|KGaA|Inc\.?|Ltd\.?|Corp\.?|S\.A\.?|B\.V\.?|NV|PLC|LLC)\s*$",
    re.IGNORECASE,
)


async def _wiki_extract(client: httpx.AsyncClient, title: str, lang: str = "de") -> str:
    if not title:
        return ""
    try:
        encoded = title.replace(" ", "_")
        resp = await client.get(
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}",
            headers=_WIKI_HEADERS,
            timeout=6.0,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("type") != "disambiguation":
                return data.get("extract", "")[:700]
        # If title had a legal suffix, retry without it
        stripped = _LEGAL_SUFFIXES.sub("", title).strip()
        if stripped != title:
            encoded2 = stripped.replace(" ", "_")
            resp2 = await client.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded2}",
                headers=_WIKI_HEADERS,
                timeout=6.0,
                follow_redirects=True,
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                if data2.get("type") != "disambiguation":
                    return data2.get("extract", "")[:700]
    except Exception:
        pass
    return ""


@router.get("/company-enrich")
async def company_enrich(
    lei: str = Query(default=""),
    name: str = Query(default=""),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Enrich a company record: GLEIF tier + Wikidata (website, industry) + Wikipedia summary."""
    empty = {"website": "", "industry": "", "nace_code": "", "notes": "", "supplier_tier": "Tier 1"}
    if not name and not lei:
        return empty

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        try:
            # GLEIF tier (parallel with Wikidata QID lookup)
            if lei:
                gleif_data, qid = await asyncio.gather(
                    _gleif_enrich_lei(client, lei),
                    _find_wikidata_qid(client, lei, name),
                )
            else:
                gleif_data = {}
                qid = await _find_wikidata_qid(client, "", name)

            supplier_tier = _tier_from_gleif(
                gleif_data.get("category", ""),
                gleif_data.get("has_parent", False),
            )

            if not qid:
                summary = await _wiki_extract(client, name)
                if not summary:
                    summary = await _wiki_extract(client, name.title())
                return {**empty, "notes": summary, "supplier_tier": supplier_tier}

            entity = await _fetch_entity(client, qid)
            claims = entity.get("claims", {})

            # Website (P856) — prefer https
            website = ""
            for c in claims.get("P856", []):
                val = c.get("mainsnak", {}).get("datavalue", {}).get("value", "")
                if val:
                    website = val
                    if val.startswith("https://"):
                        break

            # Industry (P452) — collect QIDs
            industry_qids = [
                c["mainsnak"]["datavalue"]["value"]["id"]
                for c in claims.get("P452", [])
                if c.get("mainsnak", {}).get("datavalue")
            ]

            # Description
            descs = entity.get("descriptions", {})
            description = descs.get("de", {}).get("value", "") or descs.get("en", {}).get(
                "value", ""
            )

            # Wikipedia sitelink title
            sl = entity.get("sitelinks", {})
            wiki_title = sl.get("dewiki", {}).get("title", "") or sl.get("enwiki", {}).get(
                "title", ""
            )
            wiki_lang = "de" if sl.get("dewiki") else "en"

            # Parallel: industry labels + Wikipedia extract
            # If no sitelink title, fall back to bare name (suffix stripped inside _wiki_extract)
            industry_task = _label_for_qids(client, industry_qids)
            wiki_task = _wiki_extract(client, wiki_title or name, wiki_lang)
            industry_label, wiki_summary = await asyncio.gather(industry_task, wiki_task)
            # Second chance: try English if German returned nothing
            if not wiki_summary and wiki_title and wiki_lang == "de":
                enwiki_title = sl.get("enwiki", {}).get("title", "")
                if enwiki_title:
                    wiki_summary = await _wiki_extract(client, enwiki_title, "en")

            # NACE: derive from P452 (industry) QIDs + label keyword mapping
            # P1581 is Wikidata's "official blog" (a URL property) — never use it for NACE
            nace_code, nace_label = _resolve_nace(industry_qids, industry_label)

            return {
                "website": website,
                "industry": industry_label[:200],
                "nace_code": nace_code,
                "nace_label": nace_label,
                "notes": wiki_summary or description,
                "supplier_tier": supplier_tier,
            }
        except Exception:
            return empty


def _assert_org_access(supplier_org_id: str, user_org_id: str | None) -> None:
    if user_org_id is None or supplier_org_id != user_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")


# ── Bulk import (G-008) ───────────────────────────────────────────────────────


@router.post(
    "/bulk-import",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_analyst)],
    summary="Bulk import suppliers from CSV",
)
async def bulk_import_suppliers(
    file: UploadFile = File(..., description="CSV file with supplier data"),
    dry_run: bool = Query(default=False, description="Validate without persisting"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Import suppliers from a CSV file.

    CSV must have a header row. Required column: `name`.
    Optional columns: legal_name, country, industry, nace_code, website, supplier_tier, notes.

    - ≤100 rows: processed synchronously, result returned immediately.
    - >100 rows: dispatched to Celery, returns {"task_id": "...", "status": "processing"}.
    - `dry_run=true`: validates and counts without writing to the database.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to an organization"
        )

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File must be a CSV"
        )

    content_bytes = await file.read()
    try:
        csv_content = content_bytes.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV must be UTF-8 encoded"
        )

    # Count rows to decide sync vs async
    import csv
    import io  # noqa: PLC0415

    row_count = sum(1 for _ in csv.reader(io.StringIO(csv_content))) - 1  # subtract header

    if row_count <= _MAX_SYNC_ROWS or dry_run:
        from infrastructure.celery.tasks.bulk_import import process_csv_sync  # noqa: PLC0415

        result = process_csv_sync(
            csv_content=csv_content,
            organization_id=current_user.organization_id,
            actor_id=current_user.id,
            dry_run=dry_run,
        )
        logger.info("bulk_import_sync", **{k: v for k, v in result.items() if k != "errors"})
        return result
    else:
        from infrastructure.celery.tasks.bulk_import import (
            bulk_import_suppliers_task,  # noqa: PLC0415
        )

        task = bulk_import_suppliers_task.delay(
            csv_content=csv_content,
            organization_id=current_user.organization_id,
            actor_id=current_user.id,
            dry_run=False,
        )
        logger.info("bulk_import_async", task_id=task.id, row_count=row_count)
        return {"task_id": task.id, "status": "processing", "total_rows": row_count}


@router.get(
    "/bulk-import/{task_id}",
    summary="Poll bulk import task status",
)
async def get_bulk_import_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Poll the result of an async bulk import task."""
    from celery.result import AsyncResult  # noqa: PLC0415

    from infrastructure.celery.app import celery_app  # noqa: PLC0415

    result = AsyncResult(task_id, app=celery_app)
    if result.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    if result.state == "STARTED":
        return {"task_id": task_id, "status": "processing"}
    if result.state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "error": str(result.result)}
    if result.state == "SUCCESS":
        return {"task_id": task_id, "status": "complete", **result.result}
    return {"task_id": task_id, "status": result.state.lower()}


# ── CRUD ──────────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_supplier(
    body: SupplierCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> SupplierResponse:
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    # Application-layer uniqueness guard (DB constraint is the safety net for races)
    existing = await supplier_repo.get_by_name_and_org(body.name, current_user.organization_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A supplier named '{body.name}' already exists in this organization.",
        )

    supplier = Supplier(
        organization_id=current_user.organization_id,
        name=body.name,
        legal_name=body.legal_name,
        country=body.country,
        industry=body.industry,
        nace_code=body.nace_code,
        website=body.website,
        supplier_tier=body.supplier_tier,
        supplier_status=SupplierStatus.ACTIVE,
        notes=body.notes,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
        chain_direction=body.chain_direction,
        downstream_type=body.downstream_type,
    )
    try:
        saved = await supplier_repo.save(supplier)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A supplier named '{body.name}' already exists in this organization.",
        )
    await audit_repo.save(
        audit_events.supplier_created(
            supplier_id=saved.id,
            supplier_name=saved.name,
            actor_id=current_user.id,
            actor_email=current_user.email,
            organization_id=current_user.organization_id,
        )
    )
    logger.info("supplier_created", supplier_id=saved.id, name=saved.name)
    background_tasks.add_task(
        dispatch_webhook_event,
        current_user.organization_id,
        "supplier.created",
        {"supplier_id": saved.id, "name": saved.name, "country": saved.country},
    )
    # Auto-enrich: generate country risk signals + enrichment score in background
    if saved.country:
        from application.external_intelligence.signal_generator import (
            auto_enrich_supplier_background,
        )

        background_tasks.add_task(
            auto_enrich_supplier_background,
            saved.id,
            saved.name,
            saved.country,
            saved.nace_code or "",
            current_user.organization_id,
        )
    return SupplierResponse.model_validate(saved)


@router.get("/", response_model=Page[SupplierResponse])
async def list_suppliers(
    pagination: PaginationParams = Depends(),
    filter_status: str | None = Query(default=None, alias="status"),
    country: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    supplier_tier: str | None = Query(default=None),
    search: str | None = Query(default=None),
    chain_direction: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
) -> Page[SupplierResponse]:
    if not current_user.organization_id:
        return Page(items=[], total=0, page=pagination.page, page_size=pagination.page_size)
    items, total = await supplier_repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=filter_status,
        country=country,
        industry=industry,
        supplier_tier=supplier_tier,
        search=search,
        chain_direction=chain_direction,
    )
    return Page(
        items=[SupplierResponse.model_validate(s) for s in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
) -> SupplierResponse:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)
    return SupplierResponse.model_validate(supplier)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    body: SupplierUpdate,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> SupplierResponse:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    changes: dict = {}
    if body.name is not None and body.name != supplier.name:
        existing = await supplier_repo.get_by_name_and_org(body.name, current_user.organization_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"A supplier named '{body.name}' already exists in this organization.",
            )
        changes["name"] = body.name
        supplier.name = body.name
    if body.legal_name is not None:
        changes["legal_name"] = body.legal_name
        supplier.legal_name = body.legal_name
    if body.country is not None:
        changes["country"] = body.country
        supplier.country = body.country
    if body.industry is not None:
        changes["industry"] = body.industry
        supplier.industry = body.industry
    if body.nace_code is not None:
        changes["nace_code"] = body.nace_code
        supplier.nace_code = body.nace_code
    if body.website is not None:
        changes["website"] = body.website
        supplier.website = body.website
    if body.supplier_tier is not None:
        changes["supplier_tier"] = body.supplier_tier.value
        supplier.supplier_tier = body.supplier_tier
    if body.supplier_status is not None:
        changes["supplier_status"] = body.supplier_status.value
        supplier.supplier_status = body.supplier_status
    if body.notes is not None:
        changes["notes"] = body.notes
        supplier.notes = body.notes
    if body.chain_direction is not None:
        changes["chain_direction"] = body.chain_direction
        supplier.chain_direction = body.chain_direction
    if body.downstream_type is not None:
        changes["downstream_type"] = body.downstream_type
        supplier.downstream_type = body.downstream_type

    supplier.updated_by = current_user.id
    supplier.updated_at = datetime.now(UTC)
    saved = await supplier_repo.save(supplier)

    await audit_repo.save(
        audit_events.supplier_updated(
            supplier_id=saved.id,
            supplier_name=saved.name,
            actor_id=current_user.id,
            actor_email=current_user.email,
            changes=changes,
        )
    )
    return SupplierResponse.model_validate(saved)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_supplier(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> None:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    supplier.supplier_status = SupplierStatus.INACTIVE
    supplier.status = EntityStatus.ARCHIVED
    supplier.updated_by = current_user.id
    supplier.updated_at = datetime.now(UTC)
    await supplier_repo.save(supplier)

    await audit_repo.save(
        audit_events.supplier_archived(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    )
    logger.info("supplier_archived", supplier_id=supplier_id)


# ── Sub-resources ─────────────────────────────────────────────────────────────


@router.get("/{supplier_id}/assessments", response_model=Page[dict])
async def list_supplier_assessments(
    supplier_id: str,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    session: AsyncSession = Depends(get_db),
) -> Page[dict]:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    stmt = (
        select(AssessmentModel)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
        .order_by(AssessmentModel.created_at.desc())
    )
    from interfaces.api.schemas.assessment import AssessmentResponse  # noqa: PLC0415

    items_raw, total = await assessment_repo._execute_paged(
        stmt, pagination.page, pagination.page_size
    )
    return Page(
        items=[AssessmentResponse.model_validate(a).model_dump() for a in items_raw],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{supplier_id}/risk-profile", response_model=SupplierRiskProfile)
async def get_supplier_risk_profile(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    supplier_repo: SQLSupplierRepository = Depends(get_supplier_repo),
    session: AsyncSession = Depends(get_db),
) -> SupplierRiskProfile:
    supplier = await supplier_repo.get_by_id(supplier_id)
    if supplier is None or supplier.status == EntityStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    _assert_org_access(supplier.organization_id, current_user.organization_id)

    now = datetime.now(UTC)

    # ── Assessment counts ─────────────────────────────────────────────────────
    assessment_agg = await session.execute(
        select(
            func.count(AssessmentModel.id).label("total"),
            func.max(AssessmentModel.created_at).label("last_date"),
        ).where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
    )
    agg = assessment_agg.one()
    total_assessments = agg.total or 0
    last_assessment_date = agg.last_date.isoformat() if agg.last_date else None

    approved_row = await session.execute(
        select(func.count(AssessmentModel.id)).where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.review_status == "Approved",
        )
    )
    approved_assessments = approved_row.scalar() or 0

    in_review_row = await session.execute(
        select(func.count(AssessmentModel.id)).where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.review_status == "InReview",
        )
    )
    assessments_in_review = in_review_row.scalar() or 0

    # ── Findings by severity ──────────────────────────────────────────────────
    finding_rows = await session.execute(
        select(
            FindingModel.severity,
            func.count(FindingModel.id).label("cnt"),
        )
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(FindingModel.severity)
    )
    findings_by_severity: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    total_findings = 0
    for row in finding_rows:
        findings_by_severity[row.severity] = row.cnt
        total_findings += row.cnt

    # ── Risks by severity ─────────────────────────────────────────────────────
    risk_rows = await session.execute(
        select(
            RiskModel.risk_level,
            func.count(RiskModel.id).label("cnt"),
        )
        .join(AssessmentModel, RiskModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(RiskModel.risk_level)
    )
    risks_by_severity: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    total_risks = 0
    for row in risk_rows:
        risks_by_severity[row.risk_level] = row.cnt
        total_risks += row.cnt

    # ── Recommendations / actions ─────────────────────────────────────────────
    _CLOSED = ("resolved", "verified")
    rec_rows = await session.execute(
        select(
            RecommendationModel.action_status,
            func.count(RecommendationModel.id).label("cnt"),
        )
        .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
        )
        .group_by(RecommendationModel.action_status)
    )
    action_counts: dict[str, int] = {}
    for row in rec_rows:
        action_counts[row.action_status] = row.cnt

    open_recommendations = sum(v for k, v in action_counts.items() if k not in _CLOSED)
    open_actions = action_counts.get("open", 0) + action_counts.get("in_progress", 0)

    overdue_row = await session.execute(
        select(func.count(RecommendationModel.id))
        .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.supplier_id == supplier_id,
            AssessmentModel.status != "Deleted",
            RecommendationModel.due_date < now,
            RecommendationModel.action_status.notin_(list(_CLOSED)),
        )
    )
    overdue_actions = overdue_row.scalar() or 0

    return SupplierRiskProfile(
        supplier_id=supplier_id,
        supplier_name=supplier.name,
        total_assessments=total_assessments,
        approved_assessments=approved_assessments,
        assessments_in_review=assessments_in_review,
        last_assessment_date=last_assessment_date,
        total_findings=total_findings,
        findings_by_severity=findings_by_severity,
        total_risks=total_risks,
        risks_by_severity=risks_by_severity,
        open_recommendations=open_recommendations,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
    )


# ── Supplier Benchmark ────────────────────────────────────────────────────────

class SupplierBenchmarkResponse(BaseModel):
    supplier_id: str
    supplier_name: str
    risk_score: float
    risk_band: str
    sector_percentile: float | None
    peer_comparison: str
    peers_evaluated: int
    industry: str


@router.get("/{supplier_id}/benchmark", response_model=SupplierBenchmarkResponse)
async def get_supplier_benchmark(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupplierBenchmarkResponse:
    """Compare supplier ESG risk score against same-industry peers in the org."""
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organisation")

    # Load this supplier
    sup_row = await session.execute(
        select(SupplierModel).where(
            SupplierModel.id == supplier_id,
            SupplierModel.organization_id == current_user.organization_id,
        )
    )
    supplier = sup_row.scalar_one_or_none()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    # Latest score for this supplier
    score_row = await session.execute(
        select(SupplierScoreModel)
        .where(SupplierScoreModel.supplier_id == supplier_id)
        .order_by(SupplierScoreModel.created_at.desc())
        .limit(1)
    )
    score = score_row.scalar_one_or_none()

    risk_score = score.risk_score if score else 0.0
    risk_band = score.risk_band if score else "Low"
    stored_percentile = score.sector_percentile if score else None

    # Peer scores in the same industry within this org (latest per supplier)
    from sqlalchemy import text
    peer_stmt = text(
        """
        SELECT ss.risk_score
        FROM supplier_scores ss
        JOIN suppliers s ON s.id = ss.supplier_id
        WHERE s.organization_id = :org_id
          AND s.industry = :industry
          AND s.id != :supplier_id
          AND ss.created_at = (
              SELECT MAX(ss2.created_at)
              FROM supplier_scores ss2
              WHERE ss2.supplier_id = ss.supplier_id
          )
        """
    )
    peer_rows = await session.execute(
        peer_stmt,
        {"org_id": current_user.organization_id, "industry": supplier.industry, "supplier_id": supplier_id},
    )
    peer_scores = [r[0] for r in peer_rows.fetchall()]
    peers_evaluated = len(peer_scores)

    # Compute percentile: % of peers with a higher risk score (lower = better)
    if stored_percentile is not None:
        sector_percentile = stored_percentile
    elif peers_evaluated > 0:
        better_than = sum(1 for p in peer_scores if p >= risk_score)
        sector_percentile = round((better_than / peers_evaluated) * 100, 1)
    else:
        sector_percentile = None

    if peers_evaluated == 0:
        peer_comparison = "No peers in the same industry yet."
    elif sector_percentile is not None and sector_percentile >= 75:
        peer_comparison = f"Better than {sector_percentile:.0f}% of {peers_evaluated} peers in {supplier.industry}."
    elif sector_percentile is not None and sector_percentile >= 50:
        peer_comparison = f"Above average among {peers_evaluated} peers in {supplier.industry}."
    else:
        peer_comparison = f"Below average among {peers_evaluated} peers in {supplier.industry}."

    return SupplierBenchmarkResponse(
        supplier_id=supplier_id,
        supplier_name=supplier.name,
        risk_score=round(risk_score, 1),
        risk_band=risk_band,
        sector_percentile=sector_percentile,
        peer_comparison=peer_comparison,
        peers_evaluated=peers_evaluated,
        industry=supplier.industry or "",
    )
