from sqlalchemy.ext.asyncio import AsyncSession

from application.confidence_calculator import build_confidence_card_from_level
from domain.enums import ConfidenceLevel, EntityStatus, RiskLevel
from domain.risk import Risk
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLRiskRepository(BaseRepository[Risk, RiskModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RiskModel)

    def _to_model(self, entity: Risk) -> RiskModel:
        return RiskModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            title=entity.title,
            description=entity.description,
            risk_level=entity.risk_level.value,
            category=entity.category,
            assessment_id=entity.assessment_id,
            sector_id=entity.sector_id,
            probability=entity.probability,
            impact=entity.impact,
            confidence=entity.confidence.value,
            reasoning=entity.reasoning,
            uncertainty=entity.uncertainty,
            severity_score=entity.severity_score,
            probability_score=entity.probability_score,
        )

    def _to_domain(self, model: RiskModel) -> Risk:
        level = ConfidenceLevel(model.confidence)
        return Risk(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            title=model.title,
            description=model.description,
            risk_level=RiskLevel(model.risk_level),
            category=model.category,
            assessment_id=model.assessment_id,
            sector_id=model.sector_id,
            probability=model.probability,
            impact=model.impact,
            confidence=level,
            confidence_card=build_confidence_card_from_level(level),
            reasoning=model.reasoning,
            uncertainty=model.uncertainty,
            severity_score=model.severity_score,
            probability_score=model.probability_score,
        )

    async def list_by_assessment(self, assessment_id: str) -> list[Risk]:
        return await self._list_by_field("assessment_id", assessment_id)

    async def list_by_sector(self, sector_id: str) -> list[Risk]:
        return await self._list_by_field("sector_id", sector_id)
