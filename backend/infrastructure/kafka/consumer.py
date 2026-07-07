"""EIOS Kafka Consumer — M5 Supply Chain Event Bus

Async consumer that dispatches messages to registered handler functions.
Handler registry is keyed by (topic, event_type) for O(1) dispatch.

Design decisions:
- One consumer group ID shared across all instances (competing consumers)
- auto_offset_reset="earliest" — never miss events on first start
- Graceful degradation: if Kafka is disabled (dev/test), consumer never starts
- Handler errors are caught and logged; offset is still committed so the
  consumer group advances (dead events go to the error log, not DLQ for now)
- Each handler receives the raw parsed payload dict + metadata
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from shared.config import settings

logger = structlog.get_logger(__name__)

# Handler signature: (event_dict, partition, offset) → None
HandlerFn = Callable[[dict, int, int], Awaitable[None]]


class KafkaEventConsumer:
    """Async Kafka consumer with per-(topic, event_type) handler dispatch."""

    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._running: bool = False
        # registry: {(topic, event_type): [handler, ...]}
        self._handlers: dict[tuple[str, str], list[HandlerFn]] = {}
        # Wildcard handlers: {topic: [handler, ...]}
        self._wildcard_handlers: dict[str, list[HandlerFn]] = {}

    def register(self, topic: str, event_type: str, handler: HandlerFn) -> None:
        """Register a handler for a specific (topic, event_type) pair."""
        key = (topic, event_type)
        self._handlers.setdefault(key, []).append(handler)

    def register_wildcard(self, topic: str, handler: HandlerFn) -> None:
        """Register a handler for ALL event types on a topic."""
        self._wildcard_handlers.setdefault(topic, []).append(handler)

    @property
    def subscribed_topics(self) -> list[str]:
        topics = {t for t, _ in self._handlers} | set(self._wildcard_handlers)
        return sorted(topics)

    async def start(self) -> None:
        if not settings.kafka_enabled:
            logger.info("kafka_consumer_disabled", reason="KAFKA_ENABLED=false")
            return
        if not self.subscribed_topics:
            logger.info("kafka_consumer_no_topics", reason="no handlers registered")
            return

        try:
            self._consumer = AIOKafkaConsumer(
                *self.subscribed_topics,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_consumer_group,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            )
            await self._consumer.start()
            self._running = True
            logger.info(
                "kafka_consumer_started",
                topics=self.subscribed_topics,
                group_id=settings.kafka_consumer_group,
            )
        except KafkaConnectionError as exc:
            logger.warning(
                "kafka_consumer_start_failed",
                error=str(exc),
                fallback="consumer disabled — supply chain cascades will not fire",
            )
            self._consumer = None

    async def stop(self) -> None:
        self._running = False
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
            logger.info("kafka_consumer_stopped")

    async def consume_loop(self, on_event_log=None) -> None:
        """Main consumption loop. Call after start(). Runs until stop() is called."""
        if self._consumer is None:
            return

        async for msg in self._consumer:
            if not self._running:
                break
            await self._dispatch(msg, on_event_log=on_event_log)

    async def _dispatch(self, msg, on_event_log=None) -> None:
        topic = msg.topic
        partition = msg.partition
        offset = msg.offset
        now = datetime.now(UTC)

        try:
            event = msg.value  # already deserialized by value_deserializer
        except Exception as exc:
            logger.error(
                "kafka_message_deserialize_failed", error=str(exc), topic=topic, offset=offset
            )
            return

        event_type = event.get("event_type", "")
        organization_id = event.get("organization_id", "")
        aggregate_id = event.get("aggregate_id", "")
        aggregate_type = event.get("aggregate_type", "")
        payload_json = json.dumps(event)

        handlers: list[HandlerFn] = [
            *self._handlers.get((topic, event_type), []),
            *self._wildcard_handlers.get(topic, []),
        ]

        handler_status = "OK"
        handler_error: str | None = None

        for handler in handlers:
            try:
                await handler(event, partition, offset)
            except Exception as exc:
                handler_status = "ERROR"
                handler_error = str(exc)
                logger.error(
                    "kafka_handler_failed",
                    event_type=event_type,
                    aggregate_id=aggregate_id,
                    handler=handler.__name__,
                    error=str(exc),
                )

        # Write to event_log if a log callback was provided
        if on_event_log is not None:
            await on_event_log(
                log_id=str(uuid4()),
                organization_id=organization_id,
                topic=topic,
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload_json=payload_json,
                handler_status=handler_status,
                handler_error=handler_error,
                kafka_partition=partition,
                kafka_offset=offset,
                consumed_at=now,
            )


_consumer_instance = KafkaEventConsumer()


def get_kafka_consumer() -> KafkaEventConsumer:
    return _consumer_instance
