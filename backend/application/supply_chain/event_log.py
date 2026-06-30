"""Event Log Service — M5

Reads from the event_log table. Written to by the Kafka consumer dispatch loop.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.supply_chain_event import EventLogModel, EventOutboxModel

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    from datetime import UTC
    return datetime.now(UTC)


class EventLogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        log_id: str,
        organization_id: str,
        topic: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload_json: str,
        handler_status: str,
        handler_error: str | None,
        kafka_partition: int | None,
        kafka_offset: int | None,
        consumed_at: datetime,
    ) -> EventLogModel:
        entry = EventLogModel(
            id=log_id,
            organization_id=organization_id,
            topic=topic,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload_json=payload_json,
            handler_status=handler_status,
            handler_error=handler_error,
            kafka_partition=kafka_partition,
            kafka_offset=kafka_offset,
            consumed_at=consumed_at,
            processed_at=_now(),
        )
        self._session.add(entry)
        await self._session.commit()
        return entry

    async def list_for_org(
        self,
        organization_id: str,
        event_type: str | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EventLogModel], int]:
        stmt = select(EventLogModel).where(
            EventLogModel.organization_id == organization_id,
        )
        if event_type:
            stmt = stmt.where(EventLogModel.event_type == event_type)
        if aggregate_type:
            stmt = stmt.where(EventLogModel.aggregate_type == aggregate_type)
        if aggregate_id:
            stmt = stmt.where(EventLogModel.aggregate_id == aggregate_id)

        count_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        stmt = stmt.order_by(EventLogModel.consumed_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get(self, organization_id: str, log_id: str) -> EventLogModel | None:
        model = await self._session.get(EventLogModel, log_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model

    # ── Outbox queries ─────────────────────────────────────────────────────────

    async def list_outbox(
        self,
        organization_id: str,
        outbox_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EventOutboxModel], int]:
        stmt = select(EventOutboxModel).where(
            EventOutboxModel.organization_id == organization_id,
        )
        if outbox_status:
            stmt = stmt.where(EventOutboxModel.outbox_status == outbox_status)

        count_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        stmt = stmt.order_by(EventOutboxModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def retry_outbox_entry(
        self, organization_id: str, entry_id: str
    ) -> EventOutboxModel | None:
        entry = await self._session.get(EventOutboxModel, entry_id)
        if entry is None or entry.organization_id != organization_id:
            return None
        if entry.outbox_status == "FAILED":
            entry.outbox_status = "PENDING"
            entry.attempts = 0
            entry.last_error = None
            entry.failed_at = None
            await self._session.commit()
        return entry
