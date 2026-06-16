from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agent_run import AgentRun
from domain.enums import EntityStatus
from infrastructure.persistence.models.agent_run import AgentRunModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLAgentRunRepository(BaseRepository[AgentRun, AgentRunModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentRunModel)

    def _to_model(self, entity: AgentRun) -> AgentRunModel:
        return AgentRunModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            agent_type=entity.agent_type,
            query=entity.query,
            workflow_run_id=entity.workflow_run_id,
            step_index=entity.step_index,
            result_content=entity.result_content,
            confidence=entity.confidence,
            reasoning=entity.reasoning,
            llm_provider=entity.llm_provider,
            llm_model=entity.llm_model,
            input_tokens=entity.input_tokens,
            output_tokens=entity.output_tokens,
            error=entity.error,
            run_metadata=entity.run_metadata,
        )

    def _to_domain(self, model: AgentRunModel) -> AgentRun:
        return AgentRun(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            agent_type=model.agent_type,
            query=model.query,
            workflow_run_id=model.workflow_run_id,
            step_index=model.step_index,
            result_content=model.result_content,
            confidence=model.confidence,
            reasoning=model.reasoning,
            llm_provider=model.llm_provider,
            llm_model=model.llm_model,
            input_tokens=model.input_tokens,
            output_tokens=model.output_tokens,
            error=model.error,
            run_metadata=dict(model.run_metadata) if model.run_metadata else {},
        )

    async def list_by_agent_type(self, agent_type: str) -> list[AgentRun]:
        return await self._list_by_field("agent_type", agent_type)

    async def list_by_workflow_run(self, workflow_run_id: str) -> list[AgentRun]:
        return await self._list_by_field("workflow_run_id", workflow_run_id)
