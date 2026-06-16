from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.process import Process
from infrastructure.persistence.models.process import ProcessModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLProcessRepository(BaseRepository[Process, ProcessModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProcessModel)

    def _to_model(self, entity: Process) -> ProcessModel:
        return ProcessModel(
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
            process_type=entity.process_type,
            steps=entity.steps,
            owner_domain=entity.owner_domain,
            automated=entity.automated,
        )

    def _to_domain(self, model: ProcessModel) -> Process:
        return Process(
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
            process_type=model.process_type,
            steps=list(model.steps) if model.steps else [],
            owner_domain=model.owner_domain,
            automated=model.automated,
        )
