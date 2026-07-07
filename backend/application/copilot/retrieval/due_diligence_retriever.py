"""Due Diligence retrieval adapter for the Copilot."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.due_diligence import DueDiligenceReportModel
from infrastructure.persistence.models.recommendation import RecommendationModel

from .base import RetrievalResult

_LIMIT = 5
_OVERDUE_STATUSES = frozenset({"open", "in_progress"})


async def retrieve_due_diligence_context(
    org_id: str,
    session: AsyncSession,
    *,
    limit: int = _LIMIT,
) -> RetrievalResult:
    """Return latest DD reports + overdue remediation actions."""
    reports_stmt = (
        select(DueDiligenceReportModel)
        .where(DueDiligenceReportModel.organization_id == org_id)
        .order_by(DueDiligenceReportModel.generated_at.desc(), DueDiligenceReportModel.id.asc())
        .limit(limit)
    )
    reports = (await session.execute(reports_stmt)).scalars().all()

    # Overdue open/in_progress recommendations
    today = date.today()
    overdue_stmt = (
        select(RecommendationModel)
        .where(
            RecommendationModel.organization_id == org_id,
            RecommendationModel.action_status.in_(list(_OVERDUE_STATUSES)),
            RecommendationModel.due_date < today,
        )
        .order_by(RecommendationModel.due_date.asc(), RecommendationModel.id.asc())
        .limit(10)
    )
    overdue = (await session.execute(overdue_stmt)).scalars().all()

    report_data = []
    for rpt in reports:
        rpt.report_data.get("meta", {}) if rpt.report_data else {}
        report_data.append(
            {
                "report_id": rpt.id,
                "report_type": rpt.report_type,
                "framework": rpt.framework,
                "generated_at": rpt.generated_at.isoformat() if rpt.generated_at else "",
                "summary": {
                    k: v
                    for k, v in (rpt.report_data or {}).items()
                    if k
                    in (
                        "supplier_inventory",
                        "risk_classification",
                        "remediation",
                        "human_rights",
                        "environmental",
                    )
                },
            }
        )

    overdue_data = [
        {
            "id": r.id,
            "title": r.title,
            "priority": r.priority,
            "due_date": str(r.due_date) if r.due_date else "",
            "days_overdue": (today - r.due_date).days if r.due_date else 0,
            "supplier_id": r.supplier_id if hasattr(r, "supplier_id") else "",
        }
        for r in overdue
    ]

    data = {"reports": report_data, "overdue_actions": overdue_data}

    retrieved_at = datetime.now(UTC).isoformat()
    freshness_metadata = [
        {
            "object_id": r.id,
            "object_type": "DueDiligenceReport",
            "updated_at": r.generated_at.isoformat() if r.generated_at else None,
            "retrieved_at": retrieved_at,
        }
        for r in reports
    ]

    return RetrievalResult(
        retriever="due_diligence_retriever",
        provenance=f"Latest {len(reports)} DD reports + {len(overdue)} overdue remediation actions",
        data=[data],
        source_ids=[r.id for r in reports] + [r.id for r in overdue],
        citation_type="Report",
        freshness_metadata=freshness_metadata,
    )
