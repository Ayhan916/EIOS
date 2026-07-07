"""EIOS Kafka Infrastructure — M28 Supply Chain Event Bus."""

from .events import DomainEvent, SupplierEventType
from .producer import KafkaEventProducer, get_kafka_producer

__all__ = [
    "KafkaEventProducer",
    "get_kafka_producer",
    "DomainEvent",
    "SupplierEventType",
]
