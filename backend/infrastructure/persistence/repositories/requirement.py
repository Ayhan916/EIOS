from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.requirement import Requirement
from infrastructure.persistence.models.requirement import RequirementModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLRequirementRepository(BaseRepository[Requirement, RequirementModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RequirementModel)

    def _to_model(self, entity: Requirement) -> RequirementModel:
        return RequirementModel(
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
            source=entity.source,
            article=entity.article,
            mandatory=entity.mandatory,
            requirement_type=entity.requirement_type,
        )

    def _to_domain(self, model: RequirementModel) -> Requirement:
        return Requirement(
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
            source=model.source,
            article=model.article,
            mandatory=model.mandatory,
            requirement_type=model.requirement_type,
        )

    async def list_by_source(self, source: str) -> list[Requirement]:
        return await self._list_by_field("source", source)
