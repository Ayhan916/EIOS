"""Disclosure Intelligence retrieval adapter for the Copilot."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.disclosure import (
    DisclosureRequirementModel,
    DisclosureResponseModel,
)

from .base import RetrievalResult

_LIMIT = 15
_WEAK_STATUSES = frozenset({"Not Started", "Draft"})


async def retrieve_disclosure_context(
    org_id: str,
    session: AsyncSession,
    *,
    limit: int = _LIMIT,
) -> RetrievalResult:
    """Return weakest disclosure responses (lowest coverage) for the org."""
    stmt = (
        select(DisclosureResponseModel)
        .where(DisclosureResponseModel.organization_id == org_id)
        .order_by(DisclosureResponseModel.coverage_score.asc(), DisclosureResponseModel.id.asc())
        .limit(limit)
    )
    responses = (await session.execute(stmt)).scalars().all()

    req_ids = [r.requirement_id for r in responses if r.requirement_id]
    reqs_stmt = select(DisclosureRequirementModel).where(DisclosureRequirementModel.id.in_(req_ids))
    reqs = (await session.execute(reqs_stmt)).scalars().all()
    req_map = {r.id: r for r in reqs}

    data = []
    for resp in responses:
        req = req_map.get(resp.requirement_id or "")
        data.append(
            {
                "response_id": resp.id,
                "disclosure_status": resp.disclosure_status,
                "coverage_score": getattr(resp, "coverage_score", None),
                "requirement_code": req.code if req else "",
                "requirement_title": req.title if req else "",
                "requirement_description": req.description
                if req and hasattr(req, "description")
                else "",
                "is_weak": resp.disclosure_status in _WEAK_STATUSES,
            }
        )

    retrieved_at = datetime.now(UTC).isoformat()
    freshness_metadata = [
        {
            "object_id": r.id,
            "object_type": "DisclosureResponse",
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "retrieved_at": retrieved_at,
        }
        for r in responses
    ]

    return RetrievalResult(
        retriever="disclosure_retriever",
        provenance=f"Top {len(data)} weakest disclosures by coverage score",
        data=data,
        source_ids=[r.id for r in responses],
        citation_type="Disclosure",
        freshness_metadata=freshness_metadata,
    )
