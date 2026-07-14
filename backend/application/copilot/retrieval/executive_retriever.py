"""Executive Intelligence retrieval adapter for the Copilot."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel

from .base import RetrievalResult

_CRITICAL_SEVERITY = frozenset({"Critical", "High"})
_OPEN_STATUSES = frozenset({"open", "in_progress"})


async def retrieve_executive_context(
    org_id: str,
    session: AsyncSession,
) -> RetrievalResult:
    """Return cross-domain KPI summary for executive-level questions."""

    # Supplier risk distribution
    ss_stmt = (
        select(
            SupplierScoreModel.risk_band,
            func.count().label("count"),
        )
        .where(SupplierScoreModel.organization_id == org_id)
        .group_by(SupplierScoreModel.risk_band)
    )
    ss_rows = (await session.execute(ss_stmt)).all()
    risk_dist = {r.risk_band: r.count for r in ss_rows}

    # Critical/high finding count (findings belong to assessments, join for org filter)
    finding_stmt = (
        select(func.count())
        .select_from(FindingModel)
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            FindingModel.severity.in_(list(_CRITICAL_SEVERITY)),
        )
    )
    critical_findings = (await session.execute(finding_stmt)).scalar_one_or_none() or 0

    # Open risk count (risks join through assessments)
    risk_stmt = (
        select(func.count())
        .select_from(RiskModel)
        .join(AssessmentModel, RiskModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            RiskModel.risk_level.in_(list(_CRITICAL_SEVERITY)),
        )
    )
    critical_risks = (await session.execute(risk_stmt)).scalar_one_or_none() or 0

    # Open recommendations (join through assessments)
    open_rec_stmt = (
        select(func.count())
        .select_from(RecommendationModel)
        .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            RecommendationModel.action_status.in_(list(_OPEN_STATUSES)),
        )
    )
    open_recs = (await session.execute(open_rec_stmt)).scalar_one_or_none() or 0

    # Latest assessment
    latest_assessment_stmt = (
        select(AssessmentModel)
        .where(AssessmentModel.organization_id == org_id)
        .order_by(AssessmentModel.created_at.desc())
        .limit(1)
    )
    latest_assessment = (await session.execute(latest_assessment_stmt)).scalars().first()

    # Top 5 critical findings for context
    top_findings_stmt = (
        select(FindingModel)
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            FindingModel.severity == "Critical",
        )
        .order_by(FindingModel.created_at.desc(), FindingModel.id.asc())
        .limit(5)
    )
    top_findings = (await session.execute(top_findings_stmt)).scalars().all()

    data = {
        "risk_distribution": risk_dist,
        "critical_findings": critical_findings,
        "critical_risks": critical_risks,
        "open_recommendations": open_recs,
        "latest_assessment": {
            "id": latest_assessment.id,
            "title": latest_assessment.title if hasattr(latest_assessment, "title") else "",
            "created_at": str(latest_assessment.created_at),
        }
        if latest_assessment
        else None,
        "top_critical_findings": [
            {
                "id": f.id,
                "title": f.title,
                "severity": f.severity,
                "category": f.category if hasattr(f, "category") else "",
            }
            for f in top_findings
        ],
    }

    source_ids = ([latest_assessment.id] if latest_assessment else []) + [
        f.id for f in top_findings
    ]

    retrieved_at = datetime.now(UTC).isoformat()
    freshness_metadata = [
        {
            "object_id": f.id,
            "object_type": "Finding",
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
            "retrieved_at": retrieved_at,
        }
        for f in top_findings
    ]

    return RetrievalResult(
        retriever="executive_retriever",
        provenance="Cross-domain KPI summary: risk distribution, critical findings, open actions",
        data=[data],
        source_ids=source_ids,
        citation_type="Assessment",
        freshness_metadata=freshness_metadata,
    )
