from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import ConfidenceLevel, EntityStatus, EvidenceStrength, RiskLevel
from domain.finding import Finding
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLFindingRepository(BaseRepository[Finding, FindingModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FindingModel)

    def _to_model(self, entity: Finding) -> FindingModel:
        return FindingModel(
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
            assessment_id=entity.assessment_id,
            category=entity.category,
            severity=entity.severity.value,
            confidence=entity.confidence.value,
            reasoning=entity.reasoning,
            uncertainty=entity.uncertainty,
            evidence_strength=entity.evidence_strength.value if entity.evidence_strength else None,
            evidence_source_count=entity.evidence_source_count,
            severity_score=entity.severity_score,
            probability_score=entity.probability_score,
        )

    def _to_domain(self, model: FindingModel) -> Finding:
        return Finding(
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
            assessment_id=model.assessment_id,
            category=model.category,
            severity=RiskLevel(model.severity),
            confidence=ConfidenceLevel(model.confidence),
            reasoning=model.reasoning,
            uncertainty=model.uncertainty,
            evidence_strength=EvidenceStrength(model.evidence_strength) if model.evidence_strength else None,
            evidence_source_count=model.evidence_source_count or 0,
            severity_score=model.severity_score,
            probability_score=model.probability_score,
        )

    async def list_by_assessment(self, assessment_id: str) -> list[Finding]:
        return await self._list_by_field("assessment_id", assessment_id)
