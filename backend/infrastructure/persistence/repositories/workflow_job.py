from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.workflow_job import WorkflowJob
from infrastructure.persistence.models.workflow_job import WorkflowJobModel


class SQLWorkflowJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(self, entity: WorkflowJob) -> WorkflowJobModel:
        return WorkflowJobModel(
            id=entity.id,
            organization_id=entity.organization_id,
            workflow_type=entity.workflow_type,
            query=entity.query,
            created_by=entity.created_by,
            job_status=entity.job_status,
            workflow_run_id=entity.workflow_run_id,
            error=entity.error,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            job_metadata=entity.job_metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _to_domain(self, model: WorkflowJobModel) -> WorkflowJob:
        return WorkflowJob(
            id=model.id,
            organization_id=model.organization_id,
            workflow_type=model.workflow_type,
            query=model.query,
            created_by=model.created_by,
            job_status=model.job_status,
            workflow_run_id=model.workflow_run_id,
            error=model.error,
            started_at=model.started_at,
            completed_at=model.completed_at,
            job_metadata=dict(model.job_metadata) if model.job_metadata else {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(self, job_id: str) -> WorkflowJob | None:
        result = await self._session.get(WorkflowJobModel, job_id)
        if result is None:
            return None
        return self._to_domain(result)

    async def save(self, job: WorkflowJob) -> WorkflowJob:
        job.updated_at = datetime.now(UTC)
        model = self._to_model(job)
        merged = await self._session.merge(model)
        await self._session.flush()
        return self._to_domain(merged)

    async def list_by_user(self, user_id: str) -> list[WorkflowJob]:
        stmt = (
            select(WorkflowJobModel)
            .where(WorkflowJobModel.created_by == user_id)
            .order_by(WorkflowJobModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def list_by_status(self, job_status: str) -> list[WorkflowJob]:
        stmt = (
            select(WorkflowJobModel)
            .where(WorkflowJobModel.job_status == job_status)
            .order_by(WorkflowJobModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def list_org_paged(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        job_status: str | None = None,
    ) -> tuple[list[WorkflowJob], int]:
        from sqlalchemy import func

        stmt = (
            select(WorkflowJobModel)
            .where(WorkflowJobModel.organization_id == organization_id)
            .order_by(WorkflowJobModel.created_at.desc())
        )
        if job_status:
            stmt = stmt.where(WorkflowJobModel.job_status == job_status)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()
        paged_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await self._session.execute(paged_stmt)).scalars().all()
        return [self._to_domain(r) for r in rows], total
