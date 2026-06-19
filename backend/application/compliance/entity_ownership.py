"""Entity ownership resolution for compliance mapping validation.

Before creating a RequirementMapping, the caller must verify that the target
entity (Finding, Risk, Recommendation) belongs to the same organisation as the
authenticated user.  This module resolves ownership via the entity's parent
Assessment, which carries the canonical organization_id.

Entities with no assessment_id are treated as unresolvable.  The caller should
reject them (403) rather than leak information about whether the entity exists.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.risk import RiskModel

_SUPPORTED = frozenset({"finding", "risk", "recommendation"})


async def resolve_entity_org_id(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> str | None:
    """Return the organization_id that owns entity_id, or None.

    None means: entity does not exist, has no assessment, or entity_type is
    unsupported.  Callers should treat None as a denial.
    """
    if entity_type not in _SUPPORTED:
        return None

    if entity_type == "finding":
        stmt = (
            select(AssessmentModel.organization_id)
            .join(FindingModel, FindingModel.assessment_id == AssessmentModel.id)
            .where(FindingModel.id == entity_id)
        )
    elif entity_type == "risk":
        stmt = (
            select(AssessmentModel.organization_id)
            .join(RiskModel, RiskModel.assessment_id == AssessmentModel.id)
            .where(
                RiskModel.id == entity_id,
                RiskModel.assessment_id.isnot(None),
            )
        )
    else:  # recommendation
        stmt = (
            select(AssessmentModel.organization_id)
            .join(
                RecommendationModel,
                RecommendationModel.assessment_id == AssessmentModel.id,
            )
            .where(
                RecommendationModel.id == entity_id,
                RecommendationModel.assessment_id.isnot(None),
            )
        )

    return (await session.execute(stmt)).scalar_one_or_none()
