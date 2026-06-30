"""Supply Chain Event Outbox — M5

Two responsibilities:
1. OutboxService.append()  — write a domain event to event_outbox atomically
   with the business mutation (called from within an existing session).

2. OutboxPublisher.run_once() — poll PENDING entries, publish to Kafka,
   mark as PUBLISHED or increment failure counter.

The background loop in main.py calls run_once() every N seconds.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.kafka.events import DomainEvent
from infrastructure.kafka.producer import KafkaEventProducer
from infrastructure.persistence.models.supply_chain_event import EventOutboxModel
from shared.config import settings

logger = structlog.get_logger(__name__)

_MAX_ATTEMPTS = 5


def _now() -> datetime:
    return datetime.now(UTC)


class OutboxService:
    """Writes a domain event to the transactional outbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: DomainEvent, topic: str) -> EventOutboxModel:
        entry = EventOutboxModel(
            id=str(uuid4()),
            organization_id=event.organization_id,
            topic=topic,
            event_type=event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            payload_json=event.to_json().decode("utf-8") if isinstance(event.to_json(), bytes) else event.to_json(),
            outbox_status="PENDING",
            attempts=0,
            created_at=_now(),
        )
        self._session.add(entry)
        # No flush — caller owns the transaction boundary
        return entry


class OutboxPublisher:
    """Background worker: reads PENDING outbox entries and publishes them to Kafka."""

    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def run_once(self, batch_size: int = 50) -> int:
        """Process up to batch_size pending entries. Returns count published."""
        stmt = (
            select(EventOutboxModel)
            .where(
                EventOutboxModel.outbox_status == "PENDING",
                EventOutboxModel.attempts < _MAX_ATTEMPTS,
            )
            .order_by(EventOutboxModel.created_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        entries = list(result.scalars().all())

        published = 0
        for entry in entries:
            try:
                payload = entry.payload_json
                key = entry.aggregate_id.encode("utf-8")

                if settings.kafka_enabled:
                    from aiokafka import AIOKafkaProducer as _P  # noqa: F401 — guard import
                    from infrastructure.kafka.producer import _producer as _p
                    if _p is not None:
                        await _p.send_and_wait(
                            entry.topic,
                            value=payload.encode("utf-8"),
                            key=key,
                        )
                    else:
                        logger.info(
                            "outbox_kafka_unavailable_logged",
                            event_type=entry.event_type,
                            aggregate_id=entry.aggregate_id,
                        )

                entry.outbox_status = "PUBLISHED"
                entry.published_at = _now()
                published += 1
            except Exception as exc:
                entry.attempts += 1
                entry.last_error = str(exc)
                if entry.attempts >= _MAX_ATTEMPTS:
                    entry.outbox_status = "FAILED"
                    entry.failed_at = _now()
                logger.error(
                    "outbox_publish_failed",
                    entry_id=entry.id,
                    event_type=entry.event_type,
                    attempts=entry.attempts,
                    error=str(exc),
                )

        if entries:
            await self._session.commit()

        return published
