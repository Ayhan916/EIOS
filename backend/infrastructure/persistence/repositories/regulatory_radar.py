"""Repository — Regulatory Change Radar (CSDDD-014)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.enums import RegulatoryChangeStatus
from domain.regulatory_radar import RegulatoryChange, RegulatorySource
from infrastructure.persistence.models.regulatory_radar import (
    RegulatoryChangeModel,
    RegulatorySourceModel,
)

# ── 10 seed sources ───────────────────────────────────────────────────────────
SEED_SOURCES = [
    {
        "name": "EUR-Lex CSDDD",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L1760",
        "description": "CSDDD primary legislation (EU) 2024/1760",
        "relevance_score": 5,
        "country_code": None,
        "rss_feed_url": "https://eur-lex.europa.eu/legal-content/rss/CELEX:32024L1760",
    },
    {
        "name": "BAFA LkSG Guidance",
        "url": "https://www.bafa.de/DE/Lieferketten/lieferketten_node.html",
        "description": "German Federal Office guidance on Supply Chain Act (LkSG)",
        "relevance_score": 4,
        "country_code": "DE",
        "rss_feed_url": None,
    },
    {
        "name": "EU Commission CSDDD FAQ",
        "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_24_3121",
        "description": "European Commission guidance and FAQ on CSDDD implementation",
        "relevance_score": 5,
        "country_code": None,
        "rss_feed_url": None,
    },
    {
        "name": "EFRAG ESRS Standards",
        "url": "https://efrag.org/activities/esg-standards",
        "description": "European Financial Reporting Advisory Group — ESRS sustainability reporting standards",
        "relevance_score": 4,
        "country_code": None,
        "rss_feed_url": None,
    },
    {
        "name": "ILO Core Conventions",
        "url": "https://www.ilo.org/international-labour-standards/introduction-to-international-labour-standards",
        "description": "ILO fundamental labour rights conventions referenced in CSDDD Annex I",
        "relevance_score": 3,
        "country_code": None,
        "rss_feed_url": None,
    },
    {
        "name": "OECD Due Diligence Guidance",
        "url": "https://www.oecd.org/investment/due-diligence-guidance-for-responsible-business-conduct.htm",
        "description": "OECD RBC Due Diligence Guidance — methodology basis for CSDDD",
        "relevance_score": 4,
        "country_code": None,
        "rss_feed_url": None,
    },
    {
        "name": "ESMA ESAP Regulation",
        "url": "https://www.esma.europa.eu/esap",
        "description": "European Single Access Point — reporting portal (EU) 2023/2859",
        "relevance_score": 3,
        "country_code": None,
        "rss_feed_url": None,
    },
    {
        "name": "UN Guiding Principles (UNGPs)",
        "url": "https://www.ohchr.org/en/publications-and-resources/reports/2011/guiding-principles-business-and-human-rights",
        "description": "UN Guiding Principles on Business and Human Rights — CSDDD reference framework",
        "relevance_score": 3,
        "country_code": None,
        "rss_feed_url": None,
    },
    {
        "name": "Lieferkettensorgfaltspflichtengesetz (LkSG)",
        "url": "https://www.gesetze-im-internet.de/lksg/",
        "description": "German Supply Chain Due Diligence Act — national CSDDD predecessor law",
        "relevance_score": 4,
        "country_code": "DE",
        "rss_feed_url": None,
    },
    {
        "name": "French Loi de Vigilance",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000034290626",
        "description": "French corporate duty of vigilance law — CSDDD inspiration",
        "relevance_score": 3,
        "country_code": "FR",
        "rss_feed_url": None,
    },
]


def _now() -> datetime:
    return datetime.now(UTC)


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _source_to_domain(m: RegulatorySourceModel) -> RegulatorySource:
    return RegulatorySource(
        id=m.id,
        organization_id=m.organization_id,
        name=m.name,
        url=m.url,
        description=m.description,
        relevance_score=m.relevance_score,
        country_code=m.country_code,
        sector=m.sector,
        rss_feed_url=m.rss_feed_url,
        is_active=m.is_active,
        last_fetched_at=m.last_fetched_at,
        created_at=m.created_at,
    )


def _change_to_domain(m: RegulatoryChangeModel) -> RegulatoryChange:
    try:
        articles = json.loads(m.affected_articles_json)
    except Exception:
        articles = []
    try:
        modules = json.loads(m.impact_modules_json)
    except Exception:
        modules = []
    return RegulatoryChange(
        id=m.id,
        organization_id=m.organization_id,
        source_id=m.source_id,
        title=m.title,
        source_name=m.source_name,
        url=m.url,
        effective_date=m.effective_date,
        summary=m.summary,
        affected_articles=articles,
        status=m.status,
        action_required=m.action_required,
        action_description=m.action_description,
        impact_modules=modules,
        estimated_effort_days=m.estimated_effort_days,
        due_date=m.due_date,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        url_hash=m.url_hash,
    )


class SQLRegulatorySourceRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def seed_global(self) -> list[RegulatorySource]:
        """Seed global (org-independent) regulatory sources if not present."""
        existing_stmt = select(RegulatorySourceModel).where(
            RegulatorySourceModel.organization_id is None
        )
        existing_names = {m.name for m in self._s.execute(existing_stmt).scalars().all()}
        created = []
        for seed in SEED_SOURCES:
            if seed["name"] not in existing_names:
                m = RegulatorySourceModel(
                    id=str(uuid4()),
                    organization_id=None,
                    name=seed["name"],
                    url=seed["url"],
                    description=seed["description"],
                    relevance_score=seed["relevance_score"],
                    country_code=seed["country_code"],
                    sector=None,
                    rss_feed_url=seed["rss_feed_url"],
                    is_active=True,
                    last_fetched_at=None,
                    created_at=_now(),
                )
                self._s.add(m)
                created.append(m)
        self._s.flush()
        return [_source_to_domain(m) for m in created]

    def list_for_org(self, organization_id: str) -> list[RegulatorySource]:
        stmt = (
            select(RegulatorySourceModel)
            .where(
                (RegulatorySourceModel.organization_id is None)
                | (RegulatorySourceModel.organization_id == organization_id)
            )
            .where(RegulatorySourceModel.is_active)
            .order_by(RegulatorySourceModel.relevance_score.desc())
        )
        return [_source_to_domain(m) for m in self._s.execute(stmt).scalars().all()]


class SQLRegulatoryChangeRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_org(
        self,
        organization_id: str,
        status: str | None = None,
        action_required: str | None = None,
    ) -> list[RegulatoryChange]:
        stmt = select(RegulatoryChangeModel).where(
            RegulatoryChangeModel.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(RegulatoryChangeModel.status == status)
        if action_required:
            stmt = stmt.where(RegulatoryChangeModel.action_required == action_required)
        stmt = stmt.order_by(RegulatoryChangeModel.created_at.desc())
        return [_change_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, change_id: str, organization_id: str) -> RegulatoryChange | None:
        m = self._s.get(RegulatoryChangeModel, change_id)
        if not m or m.organization_id != organization_id:
            return None
        return _change_to_domain(m)

    def create(
        self,
        organization_id: str,
        title: str,
        source_name: str,
        summary: str,
        affected_articles: list[str],
        created_by: str,
        url: str | None = None,
        effective_date: datetime | None = None,
        action_required: str = "pending",
        action_description: str = "",
        impact_modules: list[str] | None = None,
        estimated_effort_days: int = 0,
        due_date: datetime | None = None,
        source_id: str | None = None,
    ) -> RegulatoryChange:
        m = RegulatoryChangeModel(
            id=str(uuid4()),
            organization_id=organization_id,
            source_id=source_id,
            title=title,
            source_name=source_name,
            url=url,
            effective_date=effective_date,
            summary=summary,
            affected_articles_json=json.dumps(affected_articles),
            status=RegulatoryChangeStatus.NEW.value,
            action_required=action_required,
            action_description=action_description,
            impact_modules_json=json.dumps(impact_modules or []),
            estimated_effort_days=estimated_effort_days,
            due_date=due_date,
            created_by=created_by,
            created_at=_now(),
            updated_at=_now(),
            url_hash=_url_hash(url) if url else "",
        )
        self._s.add(m)
        self._s.flush()
        return _change_to_domain(m)

    def update_status(
        self,
        change_id: str,
        organization_id: str,
        status: str,
        action_required: str | None = None,
        action_description: str | None = None,
        impact_modules: list[str] | None = None,
        estimated_effort_days: int | None = None,
        due_date: datetime | None = None,
    ) -> RegulatoryChange | None:
        m = self._s.get(RegulatoryChangeModel, change_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = status
        if action_required is not None:
            m.action_required = action_required
        if action_description is not None:
            m.action_description = action_description
        if impact_modules is not None:
            m.impact_modules_json = json.dumps(impact_modules)
        if estimated_effort_days is not None:
            m.estimated_effort_days = estimated_effort_days
        if due_date is not None:
            m.due_date = due_date
        m.updated_at = _now()
        self._s.flush()
        return _change_to_domain(m)

    def dashboard(self, organization_id: str) -> dict:
        all_changes = self.list_org(organization_id)
        new = sum(1 for c in all_changes if c.status == RegulatoryChangeStatus.NEW.value)
        action_yes = sum(1 for c in all_changes if c.action_required == "yes")
        return {
            "total": len(all_changes),
            "new": new,
            "action_required": action_yes,
            "implemented": sum(
                1 for c in all_changes if c.status == RegulatoryChangeStatus.IMPLEMENTED.value
            ),
            "not_relevant": sum(
                1 for c in all_changes if c.status == RegulatoryChangeStatus.NOT_RELEVANT.value
            ),
        }
