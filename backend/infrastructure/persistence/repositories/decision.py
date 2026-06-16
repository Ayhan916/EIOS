from sqlalchemy.ext.asyncio import AsyncSession

from domain.decision import Decision
from domain.enums import EntityStatus
from infrastructure.persistence.models.decision import DecisionModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLDecisionRepository(BaseRepository[Decision, DecisionModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DecisionModel)

    def _to_model(self, entity: Decision) -> DecisionModel:
        return DecisionModel(
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
            rationale=entity.rationale,
            decided_by=entity.decided_by,
            decided_at=entity.decided_at,
            decision_type=entity.decision_type,
            context=entity.context,
        )

    def _to_domain(self, model: DecisionModel) -> Decision:
        return Decision(
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
            rationale=model.rationale,
            decided_by=model.decided_by,
            decided_at=model.decided_at,
            decision_type=model.decision_type,
            context=model.context,
        )
