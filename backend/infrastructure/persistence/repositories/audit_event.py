from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.audit_chain import compute_entry_hash, verify_entry_hash
from domain.audit_event import AuditEvent
from domain.enums import EntityStatus
from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLAuditEventRepository(BaseRepository[AuditEvent, AuditEventModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditEventModel)

    async def save(self, entity: AuditEvent) -> AuditEvent:
        """Persist an audit event, chaining its SHA-256 hash to the previous entry (ADR-006)."""
        previous_hash = await self._latest_entry_hash()
        entity.previous_hash = previous_hash
        entity.entry_hash = compute_entry_hash(
            event_id=entity.id,
            action=entity.action,
            actor_id=entity.actor_id,
            event_metadata=entity.event_metadata,
            previous_hash=previous_hash,
        )
        return await super().save(entity)

    async def _latest_entry_hash(self) -> str:
        """Return the entry_hash of the most recently written audit event, or '' for genesis."""
        stmt = (
            select(AuditEventModel.entry_hash)
            .order_by(AuditEventModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        value = result.scalar_one_or_none()
        return value or ""

    async def verify_chain(self) -> tuple[bool, int, str | None]:
        """Verify the integrity of the full audit event hash chain (ADR-006).

        Returns (is_valid, events_checked, first_broken_event_id).
        A broken chain indicates tampering or data corruption.
        """
        stmt = (
            select(AuditEventModel)
            .order_by(AuditEventModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        prev_hash = ""
        for row in rows:
            if row.entry_hash is None:
                prev_hash = ""
                continue

            expected = compute_entry_hash(
                event_id=row.id,
                action=row.action,
                actor_id=row.actor_id,
                event_metadata=dict(row.event_metadata) if row.event_metadata else {},
                previous_hash=row.previous_hash or prev_hash,
            )
            if expected != row.entry_hash:
                return False, rows.index(row), row.id

            prev_hash = row.entry_hash

        return True, len(rows), None

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
            previous_hash=entity.previous_hash,
            entry_hash=entity.entry_hash,
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
            previous_hash=model.previous_hash,
            entry_hash=model.entry_hash,
        )

    async def list_by_entity(self, entity_type: str, entity_id: str) -> list[AuditEvent]:
        events = await self._list_by_field("entity_id", entity_id)
        return [e for e in events if e.entity_type == entity_type]

    async def list_by_actor(self, actor_id: str) -> list[AuditEvent]:
        return await self._list_by_field("actor_id", actor_id)

    async def list_by_action(self, action: str) -> list[AuditEvent]:
        return await self._list_by_field("action", action)
