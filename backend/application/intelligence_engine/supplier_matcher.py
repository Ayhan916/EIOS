"""Supplier Matcher — deterministic fuzzy name matching.

Matches external entity names (from sanctions lists, NGO reports, etc.)
against the supplier database for a given organisation.

Algorithm:
  1. Tokenise both names (lowercase, strip legal suffixes)
  2. Compute token overlap — shared tokens / max(token_count)
  3. Match if overlap ≥ threshold AND optional country filter passes
  4. Return (supplier_id, confidence) or None

No ML, no LLM — fully deterministic and auditable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Legal suffixes to strip before comparison
_LEGAL_SUFFIXES = {
    # Legal entity forms
    "gmbh",
    "ag",
    "bv",
    "ltd",
    "llc",
    "inc",
    "corp",
    "sa",
    "sas",
    "spa",
    "nv",
    "plc",
    "co",
    "pty",
    "pte",
    "ab",
    "as",
    "oy",
    "kk",
    "srl",
    "sl",
    "bvba",
    "mbh",
    "se",
    "ug",
    "kg",
    "ohg",
    "gbr",
    "eg",
    "ev",
    "vvag",
    # Generic organizational words
    "holding",
    "holdings",
    "group",
    "international",
    "industries",
    "industrial",
    "technologies",
    "technology",
    "solutions",
    "services",
    "europe",
    "global",
    "supply",
    "chain",
    "automotive",
    "manufacturing",
    # Common industry domain words — too generic to uniquely identify a company
    # Without these, "PISHGAM ENERGY INDUSTRIES" falsely matches "Siemens Energy AG"
    # (shared token: "energy"; Jaccard 0.5 ≥ threshold 0.45)
    "energy",
    "systems",
    "engineering",
    "motors",
    "electric",
    "electronics",
    "components",
    "parts",
    "chemicals",
    "chemical",
    "materials",
    "resources",
    "power",
    "gas",
    "oil",
    "trading",
    "enterprise",
    "enterprises",
}

_MATCH_THRESHOLD = 0.45  # token overlap needed for a match


@dataclass
class MatchResult:
    supplier_id: str
    supplier_name: str
    entity_name: str
    confidence: float  # 0.0–1.0
    match_reason: str


def _tokenise(name: str) -> set[str]:
    """Lowercase, strip punctuation, remove legal suffixes, return word set."""
    tokens = set(re.sub(r"[^a-z0-9\s]", " ", name.lower()).split())
    return {t for t in tokens if len(t) >= 3 and t not in _LEGAL_SUFFIXES}


def match_entity_name(
    entity_name: str,
    entity_country: str,
    suppliers: list[dict[str, Any]],
    threshold: float = _MATCH_THRESHOLD,
) -> MatchResult | None:
    """Try to match a single external entity against a list of suppliers.

    Args:
        entity_name:    Name from the external source (e.g. "Robert Bosch GmbH")
        entity_country: ISO-2 country code from the external source (may be "")
        suppliers:      List of dicts with keys: id, name, country
        threshold:      Minimum token overlap to accept a match

    Returns:
        MatchResult with highest confidence, or None if no match found.
    """
    if not entity_name or not entity_name.strip():
        return None

    entity_tokens = _tokenise(entity_name)
    if not entity_tokens:
        return None

    best: MatchResult | None = None

    for supplier in suppliers:
        supplier_tokens = _tokenise(supplier["name"])
        if not supplier_tokens:
            continue

        shared = entity_tokens & supplier_tokens
        if not shared:
            continue

        overlap = len(shared) / max(len(entity_tokens), len(supplier_tokens))

        # Country match gives a small boost
        country_boost = 0.0
        if entity_country and supplier.get("country"):
            if entity_country.upper() == supplier["country"].upper():
                country_boost = 0.10

        confidence = min(1.0, overlap + country_boost)

        if confidence >= threshold and (best is None or confidence > best.confidence):
            reason = f"token_overlap={overlap:.2f} shared={sorted(shared)}"
            if country_boost:
                reason += f" country_match={entity_country}"
            best = MatchResult(
                supplier_id=supplier["id"],
                supplier_name=supplier["name"],
                entity_name=entity_name,
                confidence=confidence,
                match_reason=reason,
            )

    return best


async def load_org_suppliers(org_id: str, session: AsyncSession) -> list[dict[str, Any]]:
    """Load all active suppliers for an organisation."""
    from infrastructure.persistence.models.supplier import SupplierModel

    stmt = select(
        SupplierModel.id,
        SupplierModel.name,
        SupplierModel.country,
        SupplierModel.industry,
    ).where(
        SupplierModel.organization_id == org_id,
        SupplierModel.status == "Active",
    )
    rows = (await session.execute(stmt)).all()
    return [
        {"id": str(r.id), "name": r.name, "country": r.country or "", "industry": r.industry or ""}
        for r in rows
    ]
