"""Supplier Intelligence retrieval adapter for the Copilot."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel

from .base import RetrievalResult

_LIMIT = 10
_CRITICAL_SEVERITY = frozenset({"Critical", "High"})


async def retrieve_supplier_context(
    org_id: str,
    session: AsyncSession,
    *,
    limit: int = _LIMIT,
    supplier_id: str | None = None,
) -> RetrievalResult:
    """Return top-risk suppliers + critical findings for the org."""
    # Fetch suppliers ordered by risk score descending
    ss_stmt = (
        select(SupplierScoreModel)
        .where(SupplierScoreModel.organization_id == org_id)
        .order_by(SupplierScoreModel.risk_score.desc(), SupplierScoreModel.id.asc())
        .limit(limit)
    )
    if supplier_id:
        ss_stmt = ss_stmt.where(SupplierScoreModel.supplier_id == supplier_id)
    scores = (await session.execute(ss_stmt)).scalars().all()
    supplier_ids = [s.supplier_id for s in scores]

    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == org_id,
        SupplierModel.id.in_(supplier_ids),
    )
    suppliers = (await session.execute(suppliers_stmt)).scalars().all()
    supplier_map = {s.id: s for s in suppliers}

    # Critical/high findings for these suppliers (join through AssessmentModel)
    findings_stmt = (
        select(FindingModel, AssessmentModel.supplier_id.label("assessment_supplier_id"))
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.supplier_id.in_(supplier_ids),
            FindingModel.severity.in_(list(_CRITICAL_SEVERITY)),
        )
        .limit(limit * 3)
    )
    finding_rows = (await session.execute(findings_stmt)).all()
    # finding_rows is a list of (FindingModel, supplier_id) tuples

    data = []
    for sc in scores:
        sup = supplier_map.get(sc.supplier_id)
        sup_findings = [
            {"id": f.id, "title": f.title, "severity": f.severity, "category": f.category}
            for f, asmt_sup_id in finding_rows
            if asmt_sup_id == sc.supplier_id
        ]
        data.append(
            {
                "supplier_id": sc.supplier_id,
                "supplier_name": sup.name if sup else sc.supplier_id,
                "country": sup.country if sup else "",
                "tier": sup.tier if sup else "",
                "esg_score": sc.esg_score,
                "risk_score": sc.risk_score,
                "risk_band": sc.risk_band,
                "trend": sc.trend if hasattr(sc, "trend") else "",
                "critical_findings": [f for f in sup_findings if f["severity"] == "Critical"],
                "high_findings": [f for f in sup_findings if f["severity"] == "High"],
            }
        )

    retrieved_at = datetime.now(UTC).isoformat()
    freshness_metadata = [
        {
            "object_id": sc.supplier_id,
            "object_type": "SupplierScore",
            "updated_at": sc.updated_at.isoformat() if sc.updated_at else None,
            "retrieved_at": retrieved_at,
        }
        for sc in scores
    ]

    return RetrievalResult(
        retriever="supplier_retriever",
        provenance=f"Top {len(data)} suppliers by risk score with critical/high findings",
        data=data,
        source_ids=supplier_ids,
        citation_type="Supplier",
        freshness_metadata=freshness_metadata,
    )
