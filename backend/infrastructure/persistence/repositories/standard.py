from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.standard import Standard
from infrastructure.persistence.models.standard import StandardModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLStandardRepository(BaseRepository[Standard, StandardModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StandardModel)

    def _to_model(self, entity: Standard) -> StandardModel:
        return StandardModel(
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
            standard_type=entity.standard_type,
            reference=entity.reference,
            version_label=entity.version_label,
        )

    def _to_domain(self, model: StandardModel) -> Standard:
        return Standard(
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
            standard_type=model.standard_type,
            reference=model.reference,
            version_label=model.version_label,
        )
