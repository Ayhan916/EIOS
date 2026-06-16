from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import ConfidenceLevel, EntityStatus, RiskLevel
from domain.recommendation import Recommendation
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLRecommendationRepository(BaseRepository[Recommendation, RecommendationModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RecommendationModel)

    def _to_model(self, entity: Recommendation) -> RecommendationModel:
        return RecommendationModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            assessment_id=entity.assessment_id,
            title=entity.title,
            description=entity.description,
            priority=entity.priority.value,
            confidence=entity.confidence.value,
            reasoning=entity.reasoning,
            action_required=entity.action_required,
            due_date=entity.due_date,
            approved_by=entity.approved_by,
        )

    def _to_domain(self, model: RecommendationModel) -> Recommendation:
        return Recommendation(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            assessment_id=model.assessment_id,
            title=model.title,
            description=model.description,
            priority=RiskLevel(model.priority),
            confidence=ConfidenceLevel(model.confidence),
            reasoning=model.reasoning,
            action_required=model.action_required,
            due_date=model.due_date,
            approved_by=model.approved_by,
        )

    async def list_by_assessment(self, assessment_id: str) -> list[Recommendation]:
        return await self._list_by_field("assessment_id", assessment_id)
