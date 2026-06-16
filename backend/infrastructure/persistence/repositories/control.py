from sqlalchemy.ext.asyncio import AsyncSession

from domain.control import Control
from domain.enums import ControlType, EntityStatus
from infrastructure.persistence.models.control import ControlModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLControlRepository(BaseRepository[Control, ControlModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ControlModel)

    def _to_model(self, entity: Control) -> ControlModel:
        return ControlModel(
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
            control_type=entity.control_type.value,
            effectiveness=entity.effectiveness,
            automated=entity.automated,
        )

    def _to_domain(self, model: ControlModel) -> Control:
        return Control(
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
            control_type=ControlType(model.control_type),
            effectiveness=model.effectiveness,
            automated=model.automated,
        )
