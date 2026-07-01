"""Collector Orchestrator — M50 External Intelligence Engine.

Fetches real external intelligence from public APIs, matches entities
to suppliers in the organisation, creates ExternalRiskSignals, and
runs the intelligence pipeline to update Supplier Digital Twins.

Sources:
  - EU Financial Sanctions List (EEAS/FSF XML, daily)
  - OFAC SDN List (US Treasury XML, daily)
  - World Bank Governance Indicators (country-level risk, monthly)
  - UN Security Council Sanctions (consolidated XML, daily)
  - GDELT News (free REST API, 90-day rolling, per supplier)

All matching is deterministic — no LLM, no ML. See supplier_matcher.py.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .supplier_matcher import load_org_suppliers, match_entity_name

logger = structlog.get_logger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)


@dataclass
class CollectionSummary:
    org_id: str
    started_at: datetime
    completed_at: datetime | None = None
    sources_attempted: int = 0
    sources_ok: int = 0
    entities_checked: int = 0
    suppliers_matched: int = 0
    signals_created: int = 0
    twins_updated: int = 0
    events_created: int = 0
    errors: list[str] = field(default_factory=list)

    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


# ── EU Sanctions ──────────────────────────────────────────────────────────────

_EU_SANCTIONS_URL = (
    "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content"
    "?token=dG9rZW4tMjAxNw=="
)

async def _fetch_eu_sanctions(client: httpx.AsyncClient) -> list[dict]:
    """Download and parse EU consolidated sanctions list."""
    import xml.etree.ElementTree as ET

    try:
        resp = await client.get(_EU_SANCTIONS_URL)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as exc:
        logger.warning("eu_sanctions_fetch_failed", error=str(exc))
        return []

    entries = []
    for subject in root.iter("sanctionEntity"):
        name_node = subject.find(".//nameAlias")
        if name_node is None:
            continue
        name = name_node.get("wholeName", "").strip()
        if not name:
            continue

        country = ""
        addr = subject.find(".//address")
        if addr is not None:
            country = addr.get("countryIso2Code", "")

        regulation = ""
        reg_node = subject.find(".//regulation")
        if reg_node is not None:
            regulation = reg_node.get("numberTitle", "")

        subject_type = subject.get("subjectType", "individual").lower()
        entries.append({
            "name": name,
            "country": country,
            "regulation": regulation,
            "subject_type": subject_type,
        })

    # Only match against enterprises/organisations (skip individuals)
    return [e for e in entries if e["subject_type"] not in ("individual", "person")]


# ── OFAC SDN ─────────────────────────────────────────────────────────────────

_OFAC_SDN_URL = "https://ofac.treasury.gov/downloads/sdn.xml"
_SDN_NS = "http://tempuri.org/sdnList.xsd"

def _ns(tag: str) -> str:
    return f"{{{_SDN_NS}}}{tag}"

async def _fetch_ofac_sdn(client: httpx.AsyncClient) -> list[dict]:
    """Download and parse OFAC SDN list — entity entries only."""
    try:
        from lxml import etree
        resp = await client.get(_OFAC_SDN_URL)
        resp.raise_for_status()
        root = etree.fromstring(resp.content)
    except Exception as exc:
        logger.warning("ofac_sdn_fetch_failed", error=str(exc))
        return []

    entries = []
    for sdn in root.findall(_ns("sdnEntry")):
        type_el = sdn.find(_ns("sdnType"))
        sdn_type = (type_el.text or "").lower()
        if sdn_type not in ("entity", "vessel", "aircraft", "organization"):
            continue  # skip individuals

        last_el = sdn.find(_ns("lastName"))
        first_el = sdn.find(_ns("firstName"))
        if last_el is None:
            continue
        last = last_el.text or ""
        first = (first_el.text or "") if first_el is not None else ""
        name = f"{first} {last}".strip() if first else last

        country = ""
        addr = sdn.find(f".//{_ns('address')}/{_ns('country')}")
        if addr is not None:
            country = addr.text or ""

        programs = [p.text or "" for p in sdn.findall(f".//{_ns('program')}")]

        entries.append({
            "name": name,
            "country": country,
            "programs": programs,
        })

    return entries


# ── World Bank Country Risk ───────────────────────────────────────────────────

_WB_CORRUPTION_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_CC.SC"
    "?format=json&mrv=1&per_page=300&source=3"
)

async def _fetch_world_bank_country_risk(client: httpx.AsyncClient) -> dict[str, float]:
    """Return {country_iso2: corruption_risk_0_100} for all countries.

    Uses World Bank GOV_WGI_CC.SC — Control of Corruption score 0-100 (higher = better governance).
    We invert to risk: risk = 100 - score (higher = more risk).
    """
    try:
        resp = await client.get(_WB_CORRUPTION_URL)
        resp.raise_for_status()
        payload = resp.json()
        records = payload[1] if len(payload) > 1 else []
    except Exception as exc:
        logger.warning("world_bank_fetch_failed", error=str(exc))
        return {}

    risks: dict[str, float] = {}
    for rec in records:
        code = (rec.get("country", {}).get("id") or "").upper()
        value = rec.get("value")
        if code and value is not None:
            # GOV_WGI_CC.SC: 0–100 where higher = better governance, so risk = 100 - score
            risk = round(max(0.0, min(100.0, 100.0 - float(value))), 1)
            risks[code] = risk
    return risks


# ── UN Security Council Sanctions ────────────────────────────────────────────

_UN_SANCTIONS_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"


async def _fetch_un_sanctions(client: httpx.AsyncClient) -> list[dict]:
    """Download and parse UN Security Council consolidated sanctions list — entities only."""
    import xml.etree.ElementTree as ET

    try:
        resp = await client.get(_UN_SANCTIONS_URL)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as exc:
        logger.warning("un_sanctions_fetch_failed", error=str(exc))
        return []

    entries = []
    for entity in root.iter("ENTITY"):
        name = (entity.findtext("FIRST_NAME") or entity.findtext("ENTITY_NAME") or "").strip()
        if not name:
            continue
        country_raw = entity.findtext("NATIONALITY/VALUE") or ""
        entries.append({
            "name": name,
            "country": country_raw[:2].upper() if country_raw else "",
            "listed_on": entity.findtext("LISTED_ON") or "",
            "committee": entity.findtext("UN_LIST_TYPE") or "",
        })
    logger.info("un_sanctions_parsed", entity_count=len(entries))
    return entries


# ── GDELT News Intelligence ───────────────────────────────────────────────────

_GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_GDELT_RISK_TERMS = (
    "sanction OR corruption OR \"forced labor\" OR \"human rights\" "
    "OR \"environmental violation\" OR fraud OR bribery OR bankruptcy "
    "OR \"labor violation\" OR \"human trafficking\" OR \"child labor\""
)

# (keyword-set, signal_type, severity) — first match wins
_GDELT_RISK_CLASSIFIERS: list[tuple[list[str], str, str]] = [
    (
        ["forced labor", "child labor", "human trafficking", "labor violation",
         "labour violation", "worker abuse", "modern slavery"],
        "HUMAN_RIGHTS_VIOLATION", "HIGH",
    ),
    (
        ["sanction", "blacklist", "blacklisted", "designated", "ofac", "embargo",
         "un security council"],
        "SANCTIONS", "HIGH",
    ),
    (
        ["corruption", "bribery", "fraud", "kickback", "money laundering",
         "embezzlement", "anti-corruption"],
        "CORRUPTION", "HIGH",
    ),
    (
        ["environmental violation", "pollution", "toxic waste", "hazardous",
         "environmental fine", "emissions fraud"],
        "ENVIRONMENTAL_VIOLATION", "MEDIUM",
    ),
    (
        ["bankruptcy", "insolvency", "debt default", "credit downgrade",
         "financial trouble", "ratings cut", "bond default"],
        "FINANCIAL_DISTRESS", "MEDIUM",
    ),
    (
        ["recall", "production halt", "factory closure", "supply chain disruption",
         "factory fire", "plant shutdown"],
        "SUPPLY_CHAIN_DISRUPTION", "MEDIUM",
    ),
]


def _classify_gdelt_article(title: str, url: str) -> tuple[str, str] | None:
    """Return (signal_type, severity) if article matches a risk pattern, else None."""
    text = (title + " " + url).lower()
    for keywords, signal_type, severity in _GDELT_RISK_CLASSIFIERS:
        if any(kw in text for kw in keywords):
            return signal_type, severity
    return None


def _supplier_name_in_title(supplier_name: str, title: str) -> bool:
    """Verify that the supplier name (or a meaningful token) appears in the title.

    Strips common legal suffixes before checking so "BMW AG" matches "BMW".
    At least one token of 4+ characters must appear in the title.
    """
    import re
    _LEGAL_SUFFIXES = re.compile(
        r"\b(ag|gmbh|inc|llc|ltd|corp|s\.a\.|se|oy|ab|nv|bv|co\.|co)\b",
        re.IGNORECASE,
    )
    clean = _LEGAL_SUFFIXES.sub("", supplier_name)
    tokens = [t for t in re.split(r"\s+", clean.strip()) if len(t) >= 4]
    if not tokens:
        tokens = [supplier_name.split()[0]] if supplier_name else []
    title_lower = title.lower()
    return any(tok.lower() in title_lower for tok in tokens)


async def _query_gdelt_for_supplier(
    supplier_name: str,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Query GDELT for risk-relevant English-language news about one supplier.

    Uses a semaphore to cap concurrency (GDELT rate-limits aggressively).
    Returns empty list on rate-limit or network errors — never raises.
    """
    params = {
        "query": f'"{supplier_name}" ({_GDELT_RISK_TERMS})',
        "mode": "ArtList",
        "maxrecords": "5",
        "format": "json",
        "timespan": "90d",
        "sourcelang": "english",
    }
    async with semaphore:
        try:
            resp = await client.get(_GDELT_URL, params=params)
            if resp.status_code == 429:
                logger.debug("gdelt_rate_limited", supplier=supplier_name)
                return []
            resp.raise_for_status()
            text = resp.text.strip()
            if not text:
                return []
            import json as _json
            data = _json.loads(text)
        except Exception as exc:
            logger.debug("gdelt_query_failed", supplier=supplier_name, error=str(exc))
            return []
        # 1.5s between requests — GDELT rate-limits hard below this
        await asyncio.sleep(1.5)

    results = []
    for art in data.get("articles") or []:
        title = art.get("title") or ""
        url = art.get("url") or ""
        # Discard articles where the supplier name doesn't appear in the title — avoids false positives
        if not _supplier_name_in_title(supplier_name, title):
            logger.debug("gdelt_false_positive_skipped", supplier=supplier_name, title=title[:80])
            continue
        classification = _classify_gdelt_article(title, url)
        if classification:
            signal_type, severity = classification
            results.append({
                "signal_type": signal_type,
                "severity": severity,
                "title": title,
                "url": url,
                "date": art.get("seendate") or "",
            })
    return results


# ── Signal creation ───────────────────────────────────────────────────────────

async def _create_signal(
    *,
    supplier_id: str,
    org_id: str,
    signal_type: str,
    severity: str,
    description: str,
    source_name: str,
    country_code: str,
    session: AsyncSession,
) -> bool:
    """Insert an ExternalRiskSignal if not already present (dedup by description hash)."""
    import hashlib
    from sqlalchemy import select
    from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel

    dedup_hash = hashlib.md5(
        f"{supplier_id}:{signal_type}:{description[:120]}".encode()
    ).hexdigest()

    # Check for duplicate using description prefix
    stmt = select(ExternalRiskSignalModel.id).where(
        ExternalRiskSignalModel.supplier_id == supplier_id,
        ExternalRiskSignalModel.signal_type == signal_type,
        ExternalRiskSignalModel.source_name == source_name,
        ExternalRiskSignalModel.is_active == True,
    ).limit(1)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return False  # already have a signal of this type from this source

    now = datetime.now(UTC)
    model = ExternalRiskSignalModel(
        id=str(uuid.uuid4()),
        signal_type=signal_type,
        severity=severity,
        description=description,
        source_name=source_name,
        source_version=now.date().isoformat(),
        observed_at=now,
        dataset_id=None,
        country_code=country_code,
        supplier_id=supplier_id,
        organization_id=org_id,
        is_active=True,
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    try:
        await session.flush()
        return True
    except Exception as exc:
        logger.warning("signal_insert_failed", error=str(exc))
        await session.rollback()
        return False


# ── Main orchestrator ─────────────────────────────────────────────────────────

async def run_collection_for_org(
    org_id: str,
    session: AsyncSession,
    sources: list[str] | None = None,
) -> CollectionSummary:
    """Fetch external intelligence, match to suppliers, update twins.

    Args:
        org_id:  Organisation UUID
        session: Async DB session
        sources: Subset of ["eu_sanctions","ofac","world_bank"] — None = all
    """
    summary = CollectionSummary(org_id=org_id, started_at=datetime.now(UTC))
    all_sources = sources or ["eu_sanctions", "ofac", "world_bank", "un_sanctions", "gdelt"]

    # Load org suppliers once
    suppliers = await load_org_suppliers(org_id, session)
    if not suppliers:
        summary.errors.append("No active suppliers found for organisation")
        summary.completed_at = datetime.now(UTC)
        return summary

    logger.info("collector_orchestrator.start", org_id=org_id, supplier_count=len(suppliers), sources=all_sources)

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:

        # ── EU Sanctions ──────────────────────────────────────────────────────
        if "eu_sanctions" in all_sources:
            summary.sources_attempted += 1
            try:
                entities = await _fetch_eu_sanctions(client)
                summary.sources_ok += 1
                logger.info("eu_sanctions_fetched", entity_count=len(entities))

                for entity in entities:
                    summary.entities_checked += 1
                    match = match_entity_name(
                        entity["name"], entity.get("country", ""), suppliers
                    )
                    if match:
                        created = await _create_signal(
                            supplier_id=match.supplier_id,
                            org_id=org_id,
                            signal_type="SANCTIONS",
                            severity="CRITICAL",
                            description=(
                                f"EU Financial Sanctions: {entity['name']} listed under "
                                f"{entity.get('regulation', 'CFSP regulation')}. "
                                f"Confidence: {match.confidence:.0%}. Match: {match.match_reason}"
                            ),
                            source_name="eu_sanctions",
                            country_code=entity.get("country", ""),
                            session=session,
                        )
                        if created:
                            summary.signals_created += 1
                            summary.suppliers_matched += 1
                            logger.info(
                                "eu_sanctions_match",
                                entity=entity["name"],
                                supplier=match.supplier_name,
                                confidence=match.confidence,
                            )

            except Exception as exc:
                summary.errors.append(f"EU Sanctions: {exc}")
                logger.error("eu_sanctions_failed", error=str(exc))

        # ── OFAC SDN ─────────────────────────────────────────────────────────
        if "ofac" in all_sources:
            summary.sources_attempted += 1
            try:
                entities = await _fetch_ofac_sdn(client)
                summary.sources_ok += 1
                logger.info("ofac_fetched", entity_count=len(entities))

                for entity in entities:
                    summary.entities_checked += 1
                    match = match_entity_name(
                        entity["name"], entity.get("country", ""), suppliers
                    )
                    if match:
                        programs = ", ".join(entity.get("programs", [])[:3])
                        created = await _create_signal(
                            supplier_id=match.supplier_id,
                            org_id=org_id,
                            signal_type="SANCTIONS",
                            severity="CRITICAL",
                            description=(
                                f"OFAC SDN designation: {entity['name']}. "
                                f"Programs: {programs or 'unspecified'}. "
                                f"Confidence: {match.confidence:.0%}. Match: {match.match_reason}"
                            ),
                            source_name="ofac",
                            country_code=entity.get("country", ""),
                            session=session,
                        )
                        if created:
                            summary.signals_created += 1
                            summary.suppliers_matched += 1
                            logger.info(
                                "ofac_match",
                                entity=entity["name"],
                                supplier=match.supplier_name,
                                confidence=match.confidence,
                            )

            except Exception as exc:
                summary.errors.append(f"OFAC: {exc}")
                logger.error("ofac_failed", error=str(exc))

        # ── World Bank Country Risk ───────────────────────────────────────────
        if "world_bank" in all_sources:
            summary.sources_attempted += 1
            try:
                country_risks = await _fetch_world_bank_country_risk(client)
                summary.sources_ok += 1
                logger.info("world_bank_fetched", country_count=len(country_risks))

                # Create COUNTRY_RISK signals for suppliers in high-risk countries
                for supplier in suppliers:
                    country = (supplier.get("country") or "").upper()
                    if not country:
                        continue
                    risk_score = country_risks.get(country)
                    if risk_score is None:
                        continue

                    summary.entities_checked += 1

                    if risk_score >= 65:
                        severity = "HIGH"
                    elif risk_score >= 45:
                        severity = "MEDIUM"
                    else:
                        continue  # low-risk country — no signal

                    created = await _create_signal(
                        supplier_id=supplier["id"],
                        org_id=org_id,
                        signal_type="COUNTRY_RISK",
                        severity=severity,
                        description=(
                            f"World Bank Governance Indicator (Corruption Control): "
                            f"{supplier['name']} is headquartered in {country} "
                            f"with a corruption risk score of {risk_score}/100 "
                            f"(inverted from WB governance score). "
                            f"Score ≥65 indicates HIGH, ≥45 MEDIUM procurement and compliance risk."
                        ),
                        source_name="world_bank",
                        country_code=country,
                        session=session,
                    )
                    if created:
                        summary.signals_created += 1
                        summary.suppliers_matched += 1

            except Exception as exc:
                summary.errors.append(f"World Bank: {exc}")
                logger.error("world_bank_failed", error=str(exc))

        # ── UN Security Council Sanctions ─────────────────────────────────────
        if "un_sanctions" in all_sources:
            summary.sources_attempted += 1
            try:
                entities = await _fetch_un_sanctions(client)
                summary.sources_ok += 1
                logger.info("un_sanctions_fetched", entity_count=len(entities))

                for entity in entities:
                    summary.entities_checked += 1
                    match = match_entity_name(
                        entity["name"], entity.get("country", ""), suppliers
                    )
                    if match:
                        committee = entity.get("committee") or "UNSC"
                        listed_on = entity.get("listed_on") or "unknown date"
                        created = await _create_signal(
                            supplier_id=match.supplier_id,
                            org_id=org_id,
                            signal_type="SANCTIONS",
                            severity="CRITICAL",
                            description=(
                                f"UN Security Council sanction: {entity['name']} listed by "
                                f"{committee} committee (listed: {listed_on}). "
                                f"Confidence: {match.confidence:.0%}. Match: {match.match_reason}"
                            ),
                            source_name="un_sanctions",
                            country_code=entity.get("country", ""),
                            session=session,
                        )
                        if created:
                            summary.signals_created += 1
                            summary.suppliers_matched += 1
                            logger.info(
                                "un_sanctions_match",
                                entity=entity["name"],
                                supplier=match.supplier_name,
                                confidence=match.confidence,
                            )

            except Exception as exc:
                summary.errors.append(f"UN Sanctions: {exc}")
                logger.error("un_sanctions_failed", error=str(exc))

        # ── GDELT News Intelligence ────────────────────────────────────────────
        # Sequential requests with generous inter-call delay to avoid rate-limits.
        # GDELT is a best-effort source: 429 responses are handled gracefully.
        if "gdelt" in all_sources:
            summary.sources_attempted += 1
            gdelt_ok = False
            _gdelt_sem = asyncio.Semaphore(1)  # sequential — GDELT rate-limits aggressively
            try:
                for supplier in suppliers:
                    results = await _query_gdelt_for_supplier(
                        supplier["name"], client, _gdelt_sem
                    )
                    if results is not None:
                        gdelt_ok = True  # at least one request didn't hard-fail
                    for article in (results or []):
                        created = await _create_signal(
                            supplier_id=supplier["id"],
                            org_id=org_id,
                            signal_type=article["signal_type"],
                            severity=article["severity"],
                            description=(
                                f"News signal: \"{article['title']}\". "
                                f"Published: {article['date'][:8] if article['date'] else 'unknown'}. "
                                f"Source URL: {article['url']}"
                            ),
                            source_name="gdelt_news",
                            country_code=supplier.get("country", ""),
                            session=session,
                        )
                        if created:
                            summary.signals_created += 1
                            summary.suppliers_matched += 1
                            logger.info(
                                "gdelt_match",
                                supplier=supplier["name"],
                                signal_type=article["signal_type"],
                                title=article["title"][:60],
                            )
                if gdelt_ok:
                    summary.sources_ok += 1

            except Exception as exc:
                summary.errors.append(f"GDELT: {exc}")
                logger.error("gdelt_failed", error=str(exc))

    # ── Flush signals so pipeline can read them in the same session ───────────
    # We flush (not commit) because the session is owned by FastAPI's get_db()
    # context manager. Committing here closes the transaction and breaks further
    # DB operations. The caller (router) issues the final commit.
    if summary.signals_created > 0:
        try:
            await session.flush()
        except Exception as exc:
            summary.errors.append(f"Flush failed: {exc}")
            await session.rollback()
            summary.completed_at = datetime.now(UTC)
            return summary

    # ── Run intelligence pipeline on all new signals ──────────────────────────
    if summary.signals_created > 0:
        from .pipeline_service import process_signals_for_supplier

        processed_suppliers: set[str] = set()
        for supplier in suppliers:
            if supplier["id"] not in processed_suppliers:
                try:
                    events = await process_signals_for_supplier(
                        supplier["id"], org_id, session
                    )
                    if events:
                        summary.events_created += len(events)
                        summary.twins_updated += 1
                        processed_suppliers.add(supplier["id"])
                except Exception as exc:
                    logger.warning("pipeline_failed_for_supplier", supplier_id=supplier["id"], error=str(exc))

    summary.completed_at = datetime.now(UTC)
    logger.info(
        "collector_orchestrator.complete",
        org_id=org_id,
        signals_created=summary.signals_created,
        twins_updated=summary.twins_updated,
        events_created=summary.events_created,
        duration_s=summary.duration_seconds(),
    )
    return summary
