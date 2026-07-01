"""
CSDDD Sector Risk Register — News → Scenario Trigger (TASK-003 Phase 4)

Aggregates news articles by NACE sector keywords and scenario-type keywords.
When volume exceeds threshold, creates a ScenarioSuggestion for Founder review.

No auto-activation: suggestions are always human-gated (Founder confirms).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from domain.enums import ScenarioSuggestionStatus, ScenarioType

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Scenario keyword sets
# ---------------------------------------------------------------------------

_SCENARIO_KEYWORDS: dict[ScenarioType, set[str]] = {
    ScenarioType.GEOPOLITICAL_CONFLICT: {
        "war", "warfare", "conflict", "invasion", "military", "armed",
        "blockade", "siege", "offensive", "occupation", "airstrike",
        "troops", "missile", "bombardment", "ceasefire", "hostilities",
        "Krieg", "Konflikt", "Invasion", "Militär",
    },
    ScenarioType.SANCTIONS_ESCALATION: {
        "sanctions", "sanction", "embargo", "blacklist", "blacklisted",
        "export ban", "trade restriction", "asset freeze", "designated",
        "ofac", "treasury department", "eu sanctions", "un sanctions",
        "Sanktionen", "Exportverbot", "Handelsbeschränkung",
    },
    ScenarioType.NATURAL_DISASTER: {
        "flood", "flooding", "earthquake", "hurricane", "typhoon",
        "tornado", "wildfire", "drought", "tsunami", "cyclone",
        "volcanic", "landslide", "storm damage", "disaster",
        "Überschwemmung", "Erdbeben", "Hurrikan", "Dürre", "Naturkatastrophe",
    },
    ScenarioType.REGULATORY_CHANGE: {
        "regulation", "directive", "csddd", "lksgg", "cs3d", "supply chain act",
        "due diligence", "compliance deadline", "legislation", "mandatory",
        "enforcement", "eu directive", "new law", "ban", "prohibition",
        "Regulierung", "Richtlinie", "Sorgfaltspflicht", "Lieferkettensorgfaltspflichtengesetz",
    },
    ScenarioType.LABOUR_UNREST: {
        "strike", "strikes", "walkout", "union", "workers demand",
        "labour dispute", "labor dispute", "collective action", "protest",
        "workers rights", "wage dispute", "picket", "industrial action",
        "Streik", "Gewerkschaft", "Arbeitskampf", "Lohnstreit",
    },
    ScenarioType.SUPPLY_SHORTAGE: {
        "shortage", "scarcity", "supply chain disruption", "bottleneck",
        "chip shortage", "semiconductor", "rare earth", "critical material",
        "supply crunch", "production halt", "factory shutdown", "port closure",
        "Engpass", "Knappheit", "Lieferengpass", "Halbleitermangel",
    },
}

# ---------------------------------------------------------------------------
# Sector keyword sets: which words in an article title/summary suggest
# the article is about this NACE sector
# ---------------------------------------------------------------------------

_NACE_SECTOR_KEYWORDS: dict[str, set[str]] = {
    "01": {"agriculture", "farming", "crop", "harvest", "cocoa", "coffee", "cotton",
           "palm oil", "soy", "soybean", "wheat", "rice", "cattle", "livestock",
           "Landwirtschaft", "Anbau", "Ernte"},
    "05": {"coal", "lignite", "coal mine", "mining", "miner", "colliery"},
    "07": {"cobalt", "lithium", "copper mine", "gold mine", "metal ore", "mining",
           "artisanal mining", "asm", "mineral extraction", "iron ore"},
    "10": {"food manufacturing", "food processing", "meat processing",
           "packaged food", "food factory", "dairy processing"},
    "13": {"textile", "textiles", "fabric", "yarn", "cotton mill", "spinning",
           "weaving", "garment factory", "fast fashion", "xinjiang"},
    "14": {"apparel", "clothing", "garment", "fashion", "ready-made garments",
           "bangladesh factory", "rana plaza", "fashion industry"},
    "20": {"chemical", "chemicals", "pesticide", "fertilizer", "solvent",
           "chemical plant", "chemical factory", "hazmat"},
    "26": {"semiconductor", "electronics", "chip", "processor", "circuit board",
           "electronic components", "pcb", "display panel", "consumer electronics"},
    "29": {"automotive", "automobile", "car manufacturer", "vehicle", "ev",
           "electric vehicle", "automaker", "oem", "tier 1 supplier",
           "volkswagen", "bmw", "mercedes", "toyota", "catena-x"},
    "35": {"energy", "electricity", "power plant", "wind farm", "solar farm",
           "grid", "utility", "renewable energy", "gas pipeline"},
    "41": {"construction", "building", "infrastructure project", "contractor",
           "construction site", "real estate development"},
    "49": {"logistics", "transport", "trucking", "freight", "road transport",
           "courier", "delivery", "shipping", "supply chain transport"},
    "62": {"software", "it company", "tech company", "data center",
           "cloud computing", "cybersecurity", "saas", "digital services"},
    "78": {"staffing", "temp agency", "temporary workers", "recruitment agency",
           "labour hire", "migrant workers", "agency worker"},
    "86": {"hospital", "healthcare", "medical", "nursing", "pharmaceutical",
           "health system", "clinic"},
}

# ---------------------------------------------------------------------------
# Detection threshold
# ---------------------------------------------------------------------------
_THRESHOLD_ARTICLES = 5
_LOOKBACK_DAYS = 7


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class NewsScenarioDetector:
    """Detects scenario signals in news articles and creates pending suggestions."""

    def detect(
        self,
        articles: list[dict],
        existing_active_types: set[ScenarioType] | None = None,
    ) -> list[dict]:
        """Analyse articles and return ScenarioSuggestion dicts (not yet persisted).

        Args:
            articles: list of dicts with at least {"title": str, "summary": str | None}
            existing_active_types: scenario types already active — skip creating duplicates

        Returns:
            list of suggestion dicts ready for DB insertion
        """
        active = existing_active_types or set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)

        # Count: scenario_type → {nace_code → [matching articles]}
        hits: dict[ScenarioType, dict[str, list[dict]]] = {
            st: {} for st in ScenarioType
        }
        keyword_hits: dict[ScenarioType, list[str]] = {st: [] for st in ScenarioType}

        for article in articles:
            # Filter by recency if published_at present
            pub = article.get("published_at") or article.get("fetched_at")
            if pub:
                if isinstance(pub, str):
                    try:
                        from datetime import datetime as dt
                        pub_dt = dt.fromisoformat(pub.replace("Z", "+00:00"))
                        if pub_dt.tzinfo is None:
                            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue
                    except ValueError:
                        pass

            text = (
                (article.get("title") or "") + " " +
                (article.get("summary") or "") +
                " " +
                (article.get("translated_title") or "") + " " +
                (article.get("translated_summary") or "")
            ).lower()

            # Determine which NACE sectors this article touches
            article_nace_codes: list[str] = []
            for nace_code, keywords in _NACE_SECTOR_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    article_nace_codes.append(nace_code)
            if not article_nace_codes:
                article_nace_codes = ["*"]  # unclassified — count for all sectors

            # Determine which scenarios this article signals
            for scenario_type, keywords in _SCENARIO_KEYWORDS.items():
                matched_kws = [kw for kw in keywords if kw.lower() in text]
                if not matched_kws:
                    continue
                for kw in matched_kws:
                    if kw not in keyword_hits[scenario_type]:
                        keyword_hits[scenario_type].append(kw)
                for code in article_nace_codes:
                    bucket = hits[scenario_type].setdefault(code, [])
                    bucket.append({
                        "title": article.get("title") or "",
                        "url": article.get("url") or "",
                    })

        # Generate suggestions for hits above threshold
        suggestions: list[dict] = []
        now = datetime.now(timezone.utc)

        for scenario_type, nace_buckets in hits.items():
            if scenario_type in active:
                continue  # already active, skip

            # Aggregate: total article count and affected NACE codes
            total_articles = sum(len(v) for v in nace_buckets.values())
            if total_articles < _THRESHOLD_ARTICLES:
                continue

            # Collect affected NACE codes (exclude wildcard "*")
            affected_nace = sorted(
                code for code, arts in nace_buckets.items()
                if code != "*" and len(arts) >= 2
            )

            # Collect sample headlines (top 3 by article count)
            all_articles = [
                a for arts in nace_buckets.values() for a in arts
            ]
            sample = [a["title"] for a in all_articles[:3] if a["title"]]

            suggestions.append({
                "id": str(uuid.uuid4()),
                "status": ScenarioSuggestionStatus.PENDING.value,
                "version": 1,
                "created_at": now,
                "updated_at": now,
                "scenario_type": scenario_type.value,
                "affected_nace_codes": affected_nace,
                "trigger_article_count": total_articles,
                "trigger_keywords_matched": keyword_hits[scenario_type][:10],
                "sample_headlines": sample,
            })
            logger.info(
                "scenario_suggestion_created",
                scenario=scenario_type.value,
                articles=total_articles,
                affected_nace=affected_nace,
            )

        return suggestions


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------

async def save_suggestions(suggestions: list[dict], session: Any) -> list[str]:
    """Persist a list of scenario suggestion dicts to the DB."""
    from infrastructure.persistence.models.sector_risk_register import ScenarioSuggestionModel

    ids: list[str] = []
    for s in suggestions:
        model = ScenarioSuggestionModel(**s)
        session.add(model)
        ids.append(s["id"])
    await session.flush()
    return ids


async def activate_suggestion(
    suggestion_id: str,
    activator_id: str,
    session: Any,
    expires_in_days: int = 30,
) -> bool:
    """Activate a pending scenario suggestion."""
    from sqlalchemy import select
    from infrastructure.persistence.models.sector_risk_register import ScenarioSuggestionModel

    result = await session.execute(
        select(ScenarioSuggestionModel).where(
            ScenarioSuggestionModel.id == suggestion_id,
            ScenarioSuggestionModel.status == ScenarioSuggestionStatus.PENDING.value,
        )
    )
    model = result.scalar_one_or_none()
    if model is None:
        return False

    now = datetime.now(timezone.utc)
    model.status = ScenarioSuggestionStatus.ACTIVE.value
    model.activated_by = activator_id
    model.activated_at = now
    model.expires_at = now + timedelta(days=expires_in_days)
    model.updated_at = now
    await session.flush()

    logger.info(
        "scenario_suggestion_activated",
        suggestion_id=suggestion_id,
        scenario=model.scenario_type,
        activator=activator_id,
    )
    return True


async def dismiss_suggestion(
    suggestion_id: str,
    session: Any,
) -> bool:
    """Dismiss a pending scenario suggestion."""
    from sqlalchemy import select
    from infrastructure.persistence.models.sector_risk_register import ScenarioSuggestionModel

    result = await session.execute(
        select(ScenarioSuggestionModel).where(
            ScenarioSuggestionModel.id == suggestion_id,
            ScenarioSuggestionModel.status == ScenarioSuggestionStatus.PENDING.value,
        )
    )
    model = result.scalar_one_or_none()
    if model is None:
        return False

    now = datetime.now(timezone.utc)
    model.status = ScenarioSuggestionStatus.DISMISSED.value
    model.updated_at = now
    await session.flush()
    return True


async def list_scenario_suggestions(
    status: ScenarioSuggestionStatus | None,
    session: Any,
    limit: int = 50,
) -> list[ScenarioSuggestionModel]:
    from sqlalchemy import select
    from infrastructure.persistence.models.sector_risk_register import ScenarioSuggestionModel

    stmt = select(ScenarioSuggestionModel).order_by(
        ScenarioSuggestionModel.created_at.desc()
    ).limit(limit)
    if status is not None:
        stmt = stmt.where(ScenarioSuggestionModel.status == status.value)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_active_scenario_types(session: Any) -> set[ScenarioType]:
    """Return all currently active scenario types for duplicate prevention."""
    from sqlalchemy import select
    from infrastructure.persistence.models.sector_risk_register import ScenarioSuggestionModel

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(ScenarioSuggestionModel.scenario_type).where(
            ScenarioSuggestionModel.status == ScenarioSuggestionStatus.ACTIVE.value,
            (ScenarioSuggestionModel.expires_at == None)  # noqa: E711
            | (ScenarioSuggestionModel.expires_at > now),
        )
    )
    return {ScenarioType(row) for row in result.scalars().all()}
