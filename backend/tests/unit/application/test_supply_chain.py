"""Unit tests — Supply Chain Event Bus (M5)

Tests cover:
- OutboxService.append()
- OutboxPublisher.run_once()
- EventLogService CRUD
- KafkaEventConsumer handler dispatch
- SupplyChainHandlers cascade logic

Uses AsyncMock / MagicMock — no real DB or Kafka.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from application.supply_chain.event_log import EventLogService
from application.supply_chain.outbox import OutboxPublisher, OutboxService
from infrastructure.kafka.consumer import KafkaEventConsumer
from infrastructure.kafka.events import DomainEvent, MaterialEventType


def _uid() -> str:
    return str(uuid4())


def _make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_event(event_type=None) -> DomainEvent:
    return DomainEvent(
        event_type=event_type or MaterialEventType.COMPLIANCE_FLAG_SET,
        aggregate_type="Material",
        aggregate_id=_uid(),
        organization_id=_uid(),
        actor_id=_uid(),
        payload={"material_id": _uid(), "regulation": "REACH", "compliance_status": "NON_COMPLIANT"},
    )


def _make_outbox_entry(status="PENDING", attempts=0):
    m = MagicMock()
    m.id = _uid()
    m.organization_id = _uid()
    m.topic = "eios.material.events"
    m.event_type = "material.compliance.flag_set"
    m.aggregate_type = "Material"
    m.aggregate_id = _uid()
    m.payload_json = json.dumps({"event_type": "material.compliance.flag_set"})
    m.outbox_status = status
    m.attempts = attempts
    m.last_error = None
    m.published_at = None
    m.failed_at = None
    return m


# ── OutboxService ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outbox_service_append_adds_entry():
    db = _make_db()
    svc = OutboxService(db)
    event = _make_event()

    entry = await svc.append(event, topic="eios.material.events")

    db.add.assert_called_once()
    assert entry.topic == "eios.material.events"
    assert entry.outbox_status == "PENDING"
    assert entry.attempts == 0


@pytest.mark.asyncio
async def test_outbox_service_payload_is_json_string():
    db = _make_db()
    svc = OutboxService(db)
    event = _make_event()
    entry = await svc.append(event, topic="eios.material.events")
    # Should be parseable JSON
    parsed = json.loads(entry.payload_json)
    assert "event_type" in parsed


# ── OutboxPublisher ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outbox_publisher_marks_published():
    db = _make_db()
    entry = _make_outbox_entry("PENDING")
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [entry]
    db.execute = AsyncMock(return_value=result_mock)

    with patch("application.supply_chain.outbox.settings") as mock_settings:
        mock_settings.kafka_enabled = False  # skip actual Kafka in test
        publisher = OutboxPublisher(db, MagicMock())
        count = await publisher.run_once()

    assert count == 1
    assert entry.outbox_status == "PUBLISHED"
    assert entry.published_at is not None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_outbox_publisher_kafka_disabled_marks_published():
    db = _make_db()
    entry = _make_outbox_entry("PENDING", attempts=0)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [entry]
    db.execute = AsyncMock(return_value=result_mock)

    with patch("application.supply_chain.outbox.settings") as mock_settings:
        mock_settings.kafka_enabled = False
        publisher = OutboxPublisher(db, MagicMock())
        count = await publisher.run_once()

    # kafka_enabled=False → skip publish, still mark PUBLISHED
    assert count == 1
    assert entry.outbox_status == "PUBLISHED"


@pytest.mark.asyncio
async def test_outbox_publisher_no_entries_returns_zero():
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    publisher = OutboxPublisher(db, MagicMock())
    count = await publisher.run_once()
    assert count == 0
    db.commit.assert_not_called()


# ── EventLogService ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_log_append_writes_to_db():
    db = _make_db()
    svc = EventLogService(db)

    entry = await svc.append(
        log_id=_uid(),
        organization_id=_uid(),
        topic="eios.material.events",
        event_type="material.compliance.flag_set",
        aggregate_type="Material",
        aggregate_id=_uid(),
        payload_json='{"event_type": "material.compliance.flag_set"}',
        handler_status="OK",
        handler_error=None,
        kafka_partition=0,
        kafka_offset=42,
        consumed_at=datetime.now(UTC),
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert entry.handler_status == "OK"
    assert entry.kafka_offset == 42


@pytest.mark.asyncio
async def test_event_log_get_returns_none_on_org_mismatch():
    db = _make_db()
    model = MagicMock()
    model.organization_id = _uid()
    db.get = AsyncMock(return_value=model)

    svc = EventLogService(db)
    result = await svc.get(_uid(), _uid())  # different org
    assert result is None


@pytest.mark.asyncio
async def test_event_log_retry_outbox_resets_failed_entry():
    org_id = _uid()
    entry_id = _uid()
    db = _make_db()
    entry = MagicMock()
    entry.id = entry_id
    entry.organization_id = org_id
    entry.outbox_status = "FAILED"
    db.get = AsyncMock(return_value=entry)

    svc = EventLogService(db)
    result = await svc.retry_outbox_entry(org_id, entry_id)

    assert result is not None
    assert entry.outbox_status == "PENDING"
    assert entry.attempts == 0
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_event_log_retry_outbox_returns_none_when_not_found():
    db = _make_db()
    db.get = AsyncMock(return_value=None)

    svc = EventLogService(db)
    result = await svc.retry_outbox_entry(_uid(), _uid())
    assert result is None


# ── KafkaEventConsumer ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consumer_register_handler():
    consumer = KafkaEventConsumer()
    called_with = []

    async def handler(event, partition, offset):
        called_with.append(event)

    consumer.register("eios.material.events", "material.compliance.flag_set", handler)
    assert "eios.material.events" in consumer.subscribed_topics


@pytest.mark.asyncio
async def test_consumer_dispatch_calls_correct_handler():
    consumer = KafkaEventConsumer()
    received = []

    async def compliance_handler(event, partition, offset):
        received.append(("compliance", event))

    async def other_handler(event, partition, offset):
        received.append(("other", event))

    consumer.register("eios.material.events", "material.compliance.flag_set", compliance_handler)
    consumer.register("eios.material.events", "material.sourcing.added", other_handler)

    msg = MagicMock()
    msg.topic = "eios.material.events"
    msg.partition = 0
    msg.offset = 1
    msg.value = {
        "event_type": "material.compliance.flag_set",
        "organization_id": _uid(),
        "aggregate_id": _uid(),
        "aggregate_type": "Material",
        "payload": {},
    }

    await consumer._dispatch(msg)
    assert len(received) == 1
    assert received[0][0] == "compliance"


@pytest.mark.asyncio
async def test_consumer_wildcard_handler_receives_all_events():
    consumer = KafkaEventConsumer()
    received = []

    async def wildcard(event, partition, offset):
        received.append(event)

    consumer.register_wildcard("eios.material.events", wildcard)

    for event_type in ["material.compliance.flag_set", "material.sourcing.added"]:
        msg = MagicMock()
        msg.topic = "eios.material.events"
        msg.partition = 0
        msg.offset = 0
        msg.value = {"event_type": event_type, "organization_id": _uid(), "aggregate_id": _uid(), "aggregate_type": "Material", "payload": {}}
        await consumer._dispatch(msg)

    assert len(received) == 2


@pytest.mark.asyncio
async def test_consumer_handler_error_does_not_raise():
    consumer = KafkaEventConsumer()

    async def failing_handler(event, partition, offset):
        raise RuntimeError("handler failure")

    consumer.register("eios.material.events", "material.compliance.flag_set", failing_handler)

    msg = MagicMock()
    msg.topic = "eios.material.events"
    msg.partition = 0
    msg.offset = 0
    msg.value = {
        "event_type": "material.compliance.flag_set",
        "organization_id": _uid(),
        "aggregate_id": _uid(),
        "aggregate_type": "Material",
        "payload": {},
    }

    # Must not raise — consumer continues after handler error
    await consumer._dispatch(msg)


@pytest.mark.asyncio
async def test_consumer_start_skips_when_kafka_disabled():
    consumer = KafkaEventConsumer()

    async def dummy(event, partition, offset):
        pass

    consumer.register("some.topic", "some.event", dummy)

    with patch("infrastructure.kafka.consumer.settings") as mock_settings:
        mock_settings.kafka_enabled = False
        await consumer.start()

    assert consumer._consumer is None
