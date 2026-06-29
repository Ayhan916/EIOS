"""EIOS Kafka Infrastructure — M28 Supply Chain Event Bus."""

from .producer import KafkaEventProducer, get_kafka_producer
from .events import DomainEvent, SupplierEventType

__all__ = [
    "KafkaEventProducer",
    "get_kafka_producer",
    "DomainEvent",
    "SupplierEventType",
]
