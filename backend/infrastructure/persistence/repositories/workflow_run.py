from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.workflow_run import WorkflowRun
from infrastructure.persistence.models.workflow_run import WorkflowRunModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLWorkflowRunRepository(BaseRepository[WorkflowRun, WorkflowRunModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkflowRunModel)

    def _to_model(self, entity: WorkflowRun) -> WorkflowRunModel:
        return WorkflowRunModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            workflow_type=entity.workflow_type,
            query=entity.query,
            steps_completed=entity.steps_completed,
            total_steps=entity.total_steps,
            verdict=entity.verdict,
            verdict_reasoning=entity.verdict_reasoning,
            overall_risk_level=entity.overall_risk_level,
            total_input_tokens=entity.total_input_tokens,
            total_output_tokens=entity.total_output_tokens,
            error=entity.error,
            assessment_id=entity.assessment_id,
            finding_count=entity.finding_count,
            risk_count=entity.risk_count,
            recommendation_count=entity.recommendation_count,
            run_metadata=entity.run_metadata,
        )

    def _to_domain(self, model: WorkflowRunModel) -> WorkflowRun:
        return WorkflowRun(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            workflow_type=model.workflow_type,
            query=model.query,
            steps_completed=model.steps_completed,
            total_steps=model.total_steps,
            verdict=model.verdict,
            verdict_reasoning=model.verdict_reasoning,
            overall_risk_level=model.overall_risk_level,
            total_input_tokens=model.total_input_tokens,
            total_output_tokens=model.total_output_tokens,
            error=model.error,
            assessment_id=model.assessment_id,
            finding_count=model.finding_count,
            risk_count=model.risk_count,
            recommendation_count=model.recommendation_count,
            run_metadata=dict(model.run_metadata) if model.run_metadata else {},
        )

    async def list_by_workflow_type(self, workflow_type: str) -> list[WorkflowRun]:
        return await self._list_by_field("workflow_type", workflow_type)

    async def list_by_verdict(self, verdict: str) -> list[WorkflowRun]:
        return await self._list_by_field("verdict", verdict)

    async def list_by_organization(self, organization_id: str) -> list[WorkflowRun]:
        return await self._list_by_field("organization_id", organization_id)

    async def list_org_paged(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        workflow_type: Optional[str] = None,
        verdict: Optional[str] = None,
    ) -> tuple[list[WorkflowRun], int]:
        stmt = (
            select(WorkflowRunModel)
            .where(WorkflowRunModel.organization_id == organization_id)
            .order_by(WorkflowRunModel.created_at.desc())
        )
        if workflow_type:
            stmt = stmt.where(WorkflowRunModel.workflow_type == workflow_type)
        if verdict:
            stmt = stmt.where(WorkflowRunModel.verdict == verdict)
        return await self._execute_paged(stmt, page, page_size)

    async def list_by_assessment_id(self, assessment_id: str) -> list[WorkflowRun]:
        return await self._list_by_field("assessment_id", assessment_id)
