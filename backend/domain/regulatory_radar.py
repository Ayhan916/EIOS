"""Domain model — Regulatory Change Radar (CSDDD-014, Art. 7 Abs. 4).

A curated feed system tracking regulatory changes (CSDDD delegated acts,
national transposition laws, EU guidance documents) that require DD process updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RegulatorySource:
    """A monitored regulatory source (EUR-Lex, BAFA, EU Commission, etc.)."""

    id: str
    organization_id: str | None  # None = global library entry
    name: str
    url: str
    description: str
    relevance_score: int  # 1–5
    country_code: str | None  # ISO-3166-1 alpha-2, None = EU-wide
    sector: str | None
    rss_feed_url: str | None
    is_active: bool
    last_fetched_at: datetime | None
    created_at: datetime


@dataclass
class RegulatoryChange:
    """A single regulatory change event entered manually or via RSS feed."""

    id: str
    organization_id: str
    source_id: str | None
    title: str
    source_name: str
    url: str | None
    effective_date: datetime | None
    summary: str
    affected_articles: list[str]  # e.g. ["Art. 7", "Art. 10"]
    status: str  # RegulatoryChangeStatus
    action_required: str  # RegulatoryChangeActionRequired
    action_description: str
    impact_modules: list[str]  # affected EIOS modules
    estimated_effort_days: int
    due_date: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    url_hash: str  # SHA-256 of URL for deduplication


@dataclass
class RegulatoryFeedEntry:
    """Raw feed entry ingested from RSS — deduplication bucket."""

    id: str
    source_id: str
    url_hash: str
    title: str
    url: str
    published_at: datetime | None
    summary: str
    fetched_at: datetime
    converted_to_change_id: str | None  # FK to RegulatoryChange if processed
