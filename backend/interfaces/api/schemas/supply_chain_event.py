"""API Schemas — Supply Chain Event Bus (M5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventLogResponse(BaseModel):
    id: str
    organization_id: str
    topic: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload_json: str
    handler_status: str
    handler_error: str | None
    kafka_partition: int | None
    kafka_offset: int | None
    consumed_at: datetime
    processed_at: datetime | None

    @classmethod
    def from_model(cls, m: Any) -> "EventLogResponse":
        return cls(
            id=m.id,
            organization_id=m.organization_id,
            topic=m.topic,
            event_type=m.event_type,
            aggregate_type=m.aggregate_type,
            aggregate_id=m.aggregate_id,
            payload_json=m.payload_json,
            handler_status=m.handler_status,
            handler_error=m.handler_error,
            kafka_partition=m.kafka_partition,
            kafka_offset=m.kafka_offset,
            consumed_at=m.consumed_at,
            processed_at=m.processed_at,
        )


class EventLogListResponse(BaseModel):
    items: list[EventLogResponse]
    total: int
    limit: int
    offset: int


class EventOutboxResponse(BaseModel):
    id: str
    organization_id: str
    topic: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    outbox_status: str
    attempts: int
    last_error: str | None
    created_at: datetime
    published_at: datetime | None
    failed_at: datetime | None

    @classmethod
    def from_model(cls, m: Any) -> "EventOutboxResponse":
        return cls(
            id=m.id,
            organization_id=m.organization_id,
            topic=m.topic,
            event_type=m.event_type,
            aggregate_type=m.aggregate_type,
            aggregate_id=m.aggregate_id,
            outbox_status=m.outbox_status,
            attempts=m.attempts,
            last_error=m.last_error,
            created_at=m.created_at,
            published_at=m.published_at,
            failed_at=m.failed_at,
        )


class EventOutboxListResponse(BaseModel):
    items: list[EventOutboxResponse]
    total: int
    limit: int
    offset: int
