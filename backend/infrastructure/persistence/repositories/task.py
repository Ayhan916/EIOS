from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus, RiskLevel
from domain.task import Task
from infrastructure.persistence.models.task import TaskModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLTaskRepository(BaseRepository[Task, TaskModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TaskModel)

    def _to_model(self, entity: Task) -> TaskModel:
        return TaskModel(
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
            task_type=entity.task_type,
            project_id=entity.project_id,
            assignee_id=entity.assignee_id,
            priority=entity.priority.value,
            due_date=entity.due_date,
            completed=entity.completed,
        )

    def _to_domain(self, model: TaskModel) -> Task:
        return Task(
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
            task_type=model.task_type,
            project_id=model.project_id,
            assignee_id=model.assignee_id,
            priority=RiskLevel(model.priority),
            due_date=model.due_date,
            completed=model.completed,
        )

    async def list_by_project(self, project_id: str) -> list[Task]:
        return await self._list_by_field("project_id", project_id)
