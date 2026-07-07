"""ORM Models — Supply Chain Event Bus (M5)

event_outbox: Transactional outbox — events written atomically with business data,
              then published to Kafka by the background OutboxPublisher.
event_log:    Immutable audit trail of every event consumed by the consumer group.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EventOutboxModel(Base):
    """Pending domain events awaiting Kafka delivery.

    Written inside the same DB transaction as the business mutation that
    produced the event — guarantees at-least-once delivery even if the
    application crashes between the DB write and the Kafka publish.
    """

    __tablename__ = "event_outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    # Outbox state machine: PENDING → PUBLISHED | FAILED
    outbox_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_event_outbox_pending", "outbox_status", "created_at"),)


class EventLogModel(Base):
    """Immutable audit log of consumed supply-chain events.

    Every event successfully processed by the Kafka consumer group
    is appended here — provides full observability into what the
    system reacted to and when.
    """

    __tablename__ = "event_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    # Processing result
    handler_status: Mapped[str] = mapped_column(String(20), nullable=False, default="OK")
    handler_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    kafka_partition: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kafka_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_event_log_org_type", "organization_id", "event_type"),)
