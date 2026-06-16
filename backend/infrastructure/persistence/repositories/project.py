from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus, RiskLevel
from domain.project import Project
from infrastructure.persistence.models.project import ProjectModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLProjectRepository(BaseRepository[Project, ProjectModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectModel)

    def _to_model(self, entity: Project) -> ProjectModel:
        return ProjectModel(
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
            project_type=entity.project_type,
            priority=entity.priority.value,
            start_date=entity.start_date,
            end_date=entity.end_date,
            organization_id=entity.organization_id,
        )

    def _to_domain(self, model: ProjectModel) -> Project:
        return Project(
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
            project_type=model.project_type,
            priority=RiskLevel(model.priority),
            start_date=model.start_date,
            end_date=model.end_date,
            organization_id=model.organization_id,
        )

    async def list_by_organization(self, organization_id: str) -> list[Project]:
        return await self._list_by_field("organization_id", organization_id)
