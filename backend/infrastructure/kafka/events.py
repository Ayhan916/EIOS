"""
EIOS Domain Events — M28 Supply Chain Event Bus

All domain events published to Kafka are defined here.
Schema is intentionally flat JSON — no Avro/Schema Registry for dev simplicity.
Production upgrade path: add Confluent Schema Registry in M28.2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class SupplierEventType(str, Enum):
    # Supplier Twin — core
    SUPPLIER_CREATED = "supplier.created"
    SUPPLIER_UPDATED = "supplier.updated"
    # Locations
    LOCATION_CREATED = "supplier.location.created"
    LOCATION_UPDATED = "supplier.location.updated"
    LOCATION_DELETED = "supplier.location.deleted"
    # Contacts
    CONTACT_CREATED = "supplier.contact.created"
    CONTACT_UPDATED = "supplier.contact.updated"
    # Certifications
    CERTIFICATION_CREATED = "supplier.certification.created"
    CERTIFICATION_EXPIRING_SOON = "supplier.certification.expiring_soon"  # 30/60/90d
    CERTIFICATION_EXPIRED = "supplier.certification.expired"
    CERTIFICATION_RENEWED = "supplier.certification.renewed"
    # Ownership
    OWNERSHIP_UPDATED = "supplier.ownership.updated"
    # ESG Metrics
    ESG_METRIC_RECORDED = "supplier.esg_metric.recorded"
    ESG_METRIC_UPDATED = "supplier.esg_metric.updated"
    # ESG Twin cascade triggers
    SUPPLIER_ESG_UPDATED = "supplier.esg.updated"


@dataclass
class DomainEvent:
    """Base domain event published to Kafka.

    Every event carries enough context for downstream consumers to act
    without additional database lookups (self-describing events).
    """

    event_type: str
    aggregate_type: str          # Supplier | Material | Product
    aggregate_id: str
    organization_id: str
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    correlation_id: str | None = None
    causation_id: str | None = None  # ID of the event that caused this one
    actor_id: str | None = None      # user_id who triggered the action

    def to_json(self) -> bytes:
        return json.dumps(asdict(self), default=str).encode("utf-8")

    @classmethod
    def supplier_location_created(
        cls,
        organization_id: str,
        supplier_id: str,
        location_id: str,
        location_type: str,
        actor_id: str | None = None,
    ) -> "DomainEvent":
        return cls(
            event_type=SupplierEventType.LOCATION_CREATED,
            aggregate_type="Supplier",
            aggregate_id=supplier_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={
                "location_id": location_id,
                "supplier_id": supplier_id,
                "location_type": location_type,
            },
        )

    @classmethod
    def supplier_certification_created(
        cls,
        organization_id: str,
        supplier_id: str,
        certification_id: str,
        cert_type: str,
        valid_until: str | None,
        actor_id: str | None = None,
    ) -> "DomainEvent":
        return cls(
            event_type=SupplierEventType.CERTIFICATION_CREATED,
            aggregate_type="Supplier",
            aggregate_id=supplier_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={
                "certification_id": certification_id,
                "supplier_id": supplier_id,
                "cert_type": cert_type,
                "valid_until": valid_until,
            },
        )

    @classmethod
    def supplier_esg_metric_recorded(
        cls,
        organization_id: str,
        supplier_id: str,
        metric_id: str,
        metric_type: str,
        reporting_year: int,
        value: float,
        unit: str,
        actor_id: str | None = None,
    ) -> "DomainEvent":
        return cls(
            event_type=SupplierEventType.ESG_METRIC_RECORDED,
            aggregate_type="Supplier",
            aggregate_id=supplier_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={
                "metric_id": metric_id,
                "supplier_id": supplier_id,
                "metric_type": metric_type,
                "reporting_year": reporting_year,
                "value": value,
                "unit": unit,
            },
        )

    @classmethod
    def supplier_ownership_updated(
        cls,
        organization_id: str,
        supplier_id: str,
        ownership_id: str,
        is_state_owned: bool,
        parent_company_country: str | None,
        actor_id: str | None = None,
    ) -> "DomainEvent":
        return cls(
            event_type=SupplierEventType.OWNERSHIP_UPDATED,
            aggregate_type="Supplier",
            aggregate_id=supplier_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={
                "ownership_id": ownership_id,
                "supplier_id": supplier_id,
                "is_state_owned": is_state_owned,
                "parent_company_country": parent_company_country,
            },
        )
