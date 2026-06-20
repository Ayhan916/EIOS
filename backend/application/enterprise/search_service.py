"""Enterprise-wide global search — permission-aware, across entity types."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.organization import OrganizationModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.supplier import SupplierModel


async def global_search(
    enterprise_id: str,
    query: str,
    entity_types: list[str],
    limit: int,
    session: AsyncSession,
) -> dict:
    """
    Full-text search across suppliers, risks, findings, actions, reports.

    Permission-aware: only returns entities belonging to organizations
    within the enterprise. Uses ILIKE for case-insensitive substring match.
    For production at scale, replace with a dedicated search index (Elasticsearch, pg_trgm).
    """
    # Resolve org_ids for this enterprise
    org_ids = list(
        (
            await session.execute(
                select(OrganizationModel.id).where(
                    OrganizationModel.enterprise_id == enterprise_id
                )
            )
        ).scalars().all()
    )

    if not org_ids:
        return {"query": query, "total_hits": 0, "hits": []}

    hits = []
    pattern = f"%{query}%"

    if "suppliers" in entity_types:
        rows = (
            await session.execute(
                select(SupplierModel)
                .where(
                    SupplierModel.organization_id.in_(org_ids),
                    or_(
                        SupplierModel.name.ilike(pattern),
                        SupplierModel.country.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
        ).scalars().all()
        for r in rows:
            hits.append({
                "entity_type": "suppliers",
                "entity_id": r.id,
                "organization_id": r.organization_id,
                "title": r.name,
                "snippet": f"Country: {r.country or 'N/A'}",
                "score": 1.0,
            })

    if "risks" in entity_types:
        rows = (
            await session.execute(
                select(RiskModel)
                .where(
                    RiskModel.organization_id.in_(org_ids),
                    or_(
                        RiskModel.title.ilike(pattern),
                        RiskModel.description.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
        ).scalars().all()
        for r in rows:
            hits.append({
                "entity_type": "risks",
                "entity_id": r.id,
                "organization_id": r.organization_id,
                "title": r.title,
                "snippet": (r.description or "")[:120],
                "score": 1.0,
            })

    if "findings" in entity_types:
        rows = (
            await session.execute(
                select(FindingModel)
                .where(
                    FindingModel.organization_id.in_(org_ids),
                    or_(
                        FindingModel.title.ilike(pattern),
                        FindingModel.description.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
        ).scalars().all()
        for r in rows:
            hits.append({
                "entity_type": "findings",
                "entity_id": r.id,
                "organization_id": r.organization_id,
                "title": r.title,
                "snippet": (r.description or "")[:120],
                "score": 1.0,
            })

    # Truncate to global limit and return
    hits = hits[:limit]
    return {
        "query": query,
        "total_hits": len(hits),
        "hits": hits,
    }
