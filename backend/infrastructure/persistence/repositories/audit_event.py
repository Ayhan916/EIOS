from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from domain.audit_event import AuditEvent
from domain.enums import EntityStatus
from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLAuditEventRepository(BaseRepository[AuditEvent, AuditEventModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditEventModel)

    def _to_model(self, entity: AuditEvent) -> AuditEventModel:
        return AuditEventModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            action=entity.action,
            actor_id=entity.actor_id,
            actor_email=entity.actor_email,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            outcome=entity.outcome,
            detail=entity.detail,
            event_metadata=entity.event_metadata,
        )

    def _to_domain(self, model: AuditEventModel) -> AuditEvent:
        return AuditEvent(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            action=model.action,
            actor_id=model.actor_id,
            actor_email=model.actor_email,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            outcome=model.outcome,
            detail=model.detail,
            event_metadata=dict(model.event_metadata) if model.event_metadata else {},
        )

    async def list_by_entity(self, entity_type: str, entity_id: str) -> list[AuditEvent]:
        events = await self._list_by_field("entity_id", entity_id)
        return [e for e in events if e.entity_type == entity_type]

    async def list_by_actor(self, actor_id: str) -> list[AuditEvent]:
        return await self._list_by_field("actor_id", actor_id)

    async def list_by_action(self, action: str) -> list[AuditEvent]:
        return await self._list_by_field("action", action)
