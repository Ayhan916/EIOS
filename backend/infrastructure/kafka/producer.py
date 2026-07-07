"""
EIOS Kafka Producer — M28 Supply Chain Event Bus

Singleton async producer, initialized at FastAPI startup and closed on shutdown.
Uses aiokafka for async-native event publishing compatible with FastAPI's event loop.

Design decisions:
- acks="all"     → guaranteed delivery (all in-sync replicas acknowledge)
- compression    → lz4 for throughput; events can be large JSON payloads
- Graceful degradation: if Kafka is unavailable and kafka_enabled=False (dev/test),
  events are logged but not published — application logic is never blocked.
"""

from __future__ import annotations

import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from shared.config import settings

from .events import DomainEvent

logger = structlog.get_logger(__name__)

_producer: AIOKafkaProducer | None = None


async def init_kafka_producer() -> None:
    """Initialize the Kafka producer. Called at FastAPI startup."""
    global _producer

    if not settings.kafka_enabled:
        logger.info("kafka_disabled", reason="KAFKA_ENABLED=false — events will be logged only")
        return

    try:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            acks="all",
            compression_type="gzip",
            enable_idempotence=True,
            max_batch_size=65536,
            linger_ms=5,
        )
        await _producer.start()
        logger.info("kafka_producer_started", servers=settings.kafka_bootstrap_servers)
    except KafkaConnectionError as exc:
        logger.warning(
            "kafka_producer_start_failed",
            error=str(exc),
            fallback="events will be logged only",
        )
        _producer = None


async def close_kafka_producer() -> None:
    """Flush and close the producer. Called at FastAPI shutdown."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        logger.info("kafka_producer_stopped")


class KafkaEventProducer:
    """Async event publisher. Injected into routers via FastAPI dependency."""

    async def publish(self, topic: str, event: DomainEvent) -> None:
        """Publish a domain event to a Kafka topic.

        Never raises — Kafka failures are logged and swallowed so that the
        API response is never blocked by the event bus.
        """
        payload = event.to_json()
        key = event.aggregate_id.encode("utf-8")

        if _producer is None:
            logger.info(
                "kafka_event_logged_only",
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                topic=topic,
            )
            return

        try:
            await _producer.send_and_wait(topic, value=payload, key=key)
            logger.debug(
                "kafka_event_published",
                event_type=event.event_type,
                topic=topic,
                aggregate_id=event.aggregate_id,
            )
        except Exception as exc:
            logger.error(
                "kafka_publish_failed",
                event_type=event.event_type,
                topic=topic,
                aggregate_id=event.aggregate_id,
                error=str(exc),
            )

    async def publish_supplier_event(self, event: DomainEvent) -> None:
        await self.publish(settings.kafka_supplier_topic, event)

    async def publish_material_event(self, event: DomainEvent) -> None:
        await self.publish(settings.kafka_material_topic, event)

    async def publish_product_event(self, event: DomainEvent) -> None:
        await self.publish(settings.kafka_product_topic, event)


_kafka_producer_instance = KafkaEventProducer()


def get_kafka_producer() -> KafkaEventProducer:
    """FastAPI dependency — returns the shared Kafka producer instance."""
    return _kafka_producer_instance
