from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.copilot import CopilotConversation, CopilotMessage
from domain.enums import EntityStatus
from infrastructure.persistence.models.copilot import (
    CopilotConversationModel,
    CopilotMessageModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


class SQLCopilotConversationRepository(
    BaseRepository[CopilotConversation, CopilotConversationModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CopilotConversationModel)

    def _to_model(self, entity: CopilotConversation) -> CopilotConversationModel:
        return CopilotConversationModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            user_id=entity.user_id,
            title=entity.title,
            context_type=entity.context_type,
            context_id=entity.context_id,
            message_count=entity.message_count,
            is_archived=entity.is_archived,
        )

    def _to_domain(self, model: CopilotConversationModel) -> CopilotConversation:
        return CopilotConversation(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            user_id=model.user_id,
            title=model.title,
            context_type=model.context_type,
            context_id=model.context_id,
            message_count=model.message_count,
            is_archived=model.is_archived,
        )

    async def list_for_user(
        self,
        org_id: str,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[CopilotConversation]:
        stmt = select(CopilotConversationModel).where(
            CopilotConversationModel.organization_id == org_id,
            CopilotConversationModel.user_id == user_id,
        )
        if not include_archived:
            stmt = stmt.where(CopilotConversationModel.is_archived.is_(False))
        stmt = stmt.order_by(CopilotConversationModel.updated_at.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]


class SQLCopilotMessageRepository(
    BaseRepository[CopilotMessage, CopilotMessageModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CopilotMessageModel)

    def _to_model(self, entity: CopilotMessage) -> CopilotMessageModel:
        return CopilotMessageModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            conversation_id=entity.conversation_id,
            organization_id=entity.organization_id,
            user_id=entity.user_id,
            role=entity.role if isinstance(entity.role, str) else entity.role.value,
            content=entity.content,
            intent=entity.intent,
            citations=entity.citations,
            retrieved_sources=entity.retrieved_sources,
            model_used=entity.model_used,
            generation_ms=entity.generation_ms,
            generated_at=entity.generated_at,
            retrieval_snapshot=entity.retrieval_snapshot or None,
            assembled_context=entity.assembled_context or None,
            system_prompt_snapshot=entity.system_prompt_snapshot or None,
            confidence_level=entity.confidence_level or None,
            confidence_factors=entity.confidence_factors or None,
            contradiction_count=entity.contradiction_count,
            context_budget_used=entity.context_budget_used,
            context_truncated=entity.context_truncated,
            freshness_summary=entity.freshness_summary or None,
        )

    def _to_domain(self, model: CopilotMessageModel) -> CopilotMessage:
        return CopilotMessage(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            conversation_id=model.conversation_id,
            organization_id=model.organization_id,
            user_id=model.user_id,
            role=model.role,
            content=model.content,
            intent=model.intent or "",
            citations=list(model.citations or []),
            retrieved_sources=dict(model.retrieved_sources or {}),
            model_used=model.model_used or "",
            generation_ms=model.generation_ms,
            generated_at=model.generated_at or datetime.now(UTC),
            retrieval_snapshot=dict(model.retrieval_snapshot) if model.retrieval_snapshot else {},
            assembled_context=model.assembled_context or "",
            system_prompt_snapshot=model.system_prompt_snapshot or "",
            confidence_level=model.confidence_level or "",
            confidence_factors=dict(model.confidence_factors) if model.confidence_factors else {},
            contradiction_count=model.contradiction_count or 0,
            context_budget_used=model.context_budget_used or 0,
            context_truncated=bool(model.context_truncated),
            freshness_summary=dict(model.freshness_summary) if model.freshness_summary else {},
        )

    async def list_for_conversation(
        self,
        conversation_id: str,
        org_id: str,
        limit: int = 100,
    ) -> list[CopilotMessage]:
        stmt = (
            select(CopilotMessageModel)
            .where(
                CopilotMessageModel.conversation_id == conversation_id,
                CopilotMessageModel.organization_id == org_id,
            )
            .order_by(CopilotMessageModel.created_at.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]
