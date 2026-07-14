"""Context Enricher — loads the specific object a CopilotDrawer is embedded in.

When context_type + context_id are provided, fetches the object from DB and
returns a structured dict that gets injected into the system prompt before
the general CONTEXT DATA section.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def enrich_object_context(
    context_type: str,
    context_id: str,
    org_id: str,
    session: AsyncSession,
) -> dict | None:
    """Return a structured dict for the given object, or None if not found / not applicable."""
    if context_type == "finding":
        return await _fetch_finding(context_id, org_id, session)
    if context_type == "risk":
        return await _fetch_risk(context_id, org_id, session)
    if context_type == "recommendation":
        return await _fetch_recommendation(context_id, org_id, session)
    if context_type == "cap":
        return await _fetch_cap(context_id, org_id, session)
    return None


def format_object_context(obj: dict) -> str:
    """Format enriched object as a prompt section."""
    lines = [f"SPECIFIC {obj['_type'].upper()} CONTEXT (this is what the user is currently viewing):"]
    for k, v in obj.items():
        if k.startswith("_") or v is None:
            continue
        label = k.replace("_", " ").title()
        lines.append(f"  {label}: {v}")
    return "\n".join(lines)


async def _fetch_finding(finding_id: str, org_id: str, session: AsyncSession) -> dict | None:
    from infrastructure.persistence.models.assessment import AssessmentModel
    from infrastructure.persistence.models.finding import FindingModel

    stmt = (
        select(FindingModel, AssessmentModel.organization_id, AssessmentModel.supplier_id)
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            FindingModel.id == finding_id,
            AssessmentModel.organization_id == org_id,
        )
    )
    row = (await session.execute(stmt)).first()
    if not row:
        return None
    f, _, supplier_id = row
    return {
        "_type": "finding",
        "title": f.title,
        "severity": f.severity,
        "category": f.category,
        "description": f.description[:600] if f.description else None,
        "reasoning": f.reasoning[:400] if f.reasoning else None,
        "evidence_strength": f.evidence_strength,
        "supplier_id": supplier_id,
    }


async def _fetch_risk(risk_id: str, org_id: str, session: AsyncSession) -> dict | None:
    from infrastructure.persistence.models.assessment import AssessmentModel
    from infrastructure.persistence.models.associations import risk_finding
    from infrastructure.persistence.models.finding import FindingModel
    from infrastructure.persistence.models.risk import RiskModel

    # Risks are linked to findings via risk_finding association, not directly to assessments
    # Try direct approach first, fall back to join through findings
    stmt = (
        select(RiskModel, AssessmentModel.organization_id, AssessmentModel.supplier_id)
        .join(FindingModel, RiskModel.findings)
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            RiskModel.id == risk_id,
            AssessmentModel.organization_id == org_id,
        )
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if not row:
        return None
    r, _, supplier_id = row
    return {
        "_type": "risk",
        "title": r.title,
        "risk_level": r.risk_level,
        "category": r.category,
        "description": r.description[:600] if r.description else None,
        "reasoning": r.reasoning[:400] if r.reasoning else None,
        "supplier_id": supplier_id,
    }


async def _fetch_recommendation(rec_id: str, org_id: str, session: AsyncSession) -> dict | None:
    from infrastructure.persistence.models.assessment import AssessmentModel
    from infrastructure.persistence.models.recommendation import RecommendationModel

    stmt = (
        select(RecommendationModel, AssessmentModel.organization_id, AssessmentModel.supplier_id)
        .join(
            AssessmentModel,
            RecommendationModel.assessment_id == AssessmentModel.id,
            isouter=True,
        )
        .where(
            RecommendationModel.id == rec_id,
            AssessmentModel.organization_id == org_id,
        )
    )
    row = (await session.execute(stmt)).first()
    if not row:
        return None
    rec, _, supplier_id = row
    return {
        "_type": "recommendation",
        "title": rec.title,
        "priority": rec.priority,
        "action_status": rec.action_status,
        "description": rec.description[:600] if rec.description else None,
        "due_date": str(rec.due_date.date()) if rec.due_date else None,
        "expected_benefit": rec.expected_benefit[:300] if rec.expected_benefit else None,
        "implementation_complexity": rec.implementation_complexity,
        "supplier_id": supplier_id,
    }


async def _fetch_cap(cap_id: str, org_id: str, session: AsyncSession) -> dict | None:
    from infrastructure.persistence.models.corrective_action_plan import CorrectiveActionPlanModel

    stmt = select(CorrectiveActionPlanModel).where(
        CorrectiveActionPlanModel.id == cap_id,
        CorrectiveActionPlanModel.organization_id == org_id,
    )
    cap = (await session.execute(stmt)).scalar_one_or_none()
    if not cap:
        return None
    return {
        "_type": "corrective_action_plan",
        "title": cap.title,
        "cap_status": cap.cap_status,
        "description": cap.description[:600] if cap.description else None,
    }
