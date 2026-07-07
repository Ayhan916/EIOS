"""Compliance Intelligence retrieval adapter for the Copilot."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.regulatory import (
    ComplianceGapModel,
    RegulationModel,
    RegulationRequirementModel,
)

from .base import RetrievalResult

_LIMIT = 15
_HIGH_SEVERITY = frozenset({"Critical", "High"})


async def retrieve_compliance_context(
    org_id: str,
    session: AsyncSession,
    *,
    limit: int = _LIMIT,
) -> RetrievalResult:
    """Return most severe compliance gaps with regulation context."""
    gaps_stmt = (
        select(ComplianceGapModel)
        .where(ComplianceGapModel.organization_id == org_id)
        .order_by(ComplianceGapModel.severity.desc(), ComplianceGapModel.id.asc())
        .limit(limit)
    )
    gaps = (await session.execute(gaps_stmt)).scalars().all()

    req_ids = list({g.requirement_id for g in gaps if g.requirement_id})
    reqs_stmt = select(RegulationRequirementModel).where(RegulationRequirementModel.id.in_(req_ids))
    reqs = (await session.execute(reqs_stmt)).scalars().all()
    req_map = {r.id: r for r in reqs}

    reg_ids = list({r.regulation_id for r in reqs})
    regs_stmt = select(RegulationModel).where(RegulationModel.id.in_(reg_ids))
    regs = (await session.execute(regs_stmt)).scalars().all()
    reg_map = {r.id: r for r in regs}

    data = []
    for g in gaps:
        req = req_map.get(g.requirement_id or "")
        reg = reg_map.get(req.regulation_id if req else "") if req else None
        data.append(
            {
                "gap_id": g.id,
                "gap_type": g.gap_type,
                "severity": g.severity,
                "description": g.description if hasattr(g, "description") else "",
                "requirement_code": req.code if req else "",
                "requirement_title": req.title if req else "",
                "regulation_name": reg.name if reg else "",
                "regulation_code": reg.reg_code if reg and hasattr(reg, "reg_code") else "",
                "remediation_steps": g.remediation_steps if hasattr(g, "remediation_steps") else "",
            }
        )

    retrieved_at = datetime.now(UTC).isoformat()
    freshness_metadata = [
        {
            "object_id": g.id,
            "object_type": "ComplianceGap",
            "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            "retrieved_at": retrieved_at,
        }
        for g in gaps
    ]

    return RetrievalResult(
        retriever="compliance_retriever",
        provenance=f"Top {len(data)} compliance gaps by severity with regulation context",
        data=data,
        source_ids=[g.id for g in gaps],
        citation_type="ComplianceGap",
        freshness_metadata=freshness_metadata,
    )
