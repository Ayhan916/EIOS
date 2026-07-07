"""
EIOS Domain Events — M28 Supply Chain Event Bus

All domain events published to Kafka are defined here.
Schema is intentionally flat JSON — no Avro/Schema Registry for dev simplicity.
Production upgrade path: add Confluent Schema Registry in M28.2.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
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
    # External ESG Ratings (KAN-90)
    ESG_RATING_RECEIVED = "supplier.esg_rating.received"
    ESG_RATING_DELETED = "supplier.esg_rating.deleted"


class ProductEventType(str, Enum):
    # Product core (KAN-98)
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    PRODUCT_ARCHIVED = "product.archived"
    # BOM (KAN-99)
    BOM_ITEM_ADDED = "product.bom.item_added"
    BOM_ITEM_REMOVED = "product.bom.item_removed"


class MaterialEventType(str, Enum):
    # Material core (KAN-91)
    MATERIAL_CREATED = "material.created"
    MATERIAL_UPDATED = "material.updated"
    MATERIAL_ARCHIVED = "material.archived"
    # Composition / BOM (KAN-92)
    COMPOSITION_ADDED = "material.composition.added"
    COMPOSITION_REMOVED = "material.composition.removed"
    # Sourcing (KAN-93)
    SOURCING_ADDED = "material.sourcing.added"
    SOURCING_REMOVED = "material.sourcing.removed"
    # Compliance (KAN-94)
    COMPLIANCE_FLAG_SET = "material.compliance.flag_set"
    COMPLIANCE_STATUS_CHANGED = "material.compliance.status_changed"
    # Sustainability (KAN-95)
    SUSTAINABILITY_METRIC_RECORDED = "material.sustainability.metric_recorded"


@dataclass
class DomainEvent:
    """Base domain event published to Kafka.

    Every event carries enough context for downstream consumers to act
    without additional database lookups (self-describing events).
    """

    event_type: str
    aggregate_type: str  # Supplier | Material | Product
    aggregate_id: str
    organization_id: str
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    correlation_id: str | None = None
    causation_id: str | None = None  # ID of the event that caused this one
    actor_id: str | None = None  # user_id who triggered the action

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
    ) -> DomainEvent:
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
    ) -> DomainEvent:
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
    ) -> DomainEvent:
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
    ) -> DomainEvent:
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

    @classmethod
    def supplier_esg_rating_received(
        cls,
        organization_id: str,
        supplier_id: str,
        rating_id: str,
        provider: str,
        rating_date: str,
        score_pct: float | None,
        grade: str | None,
        actor_id: str | None = None,
    ) -> DomainEvent:
        return cls(
            event_type=SupplierEventType.ESG_RATING_RECEIVED,
            aggregate_type="Supplier",
            aggregate_id=supplier_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={
                "rating_id": rating_id,
                "supplier_id": supplier_id,
                "provider": provider,
                "rating_date": rating_date,
                "score_pct": score_pct,
                "grade": grade,
            },
        )

    @classmethod
    def product_created(
        cls,
        organization_id: str,
        product_id: str,
        product_type: str,
        name: str,
        actor_id: str | None = None,
    ) -> DomainEvent:
        return cls(
            event_type=ProductEventType.PRODUCT_CREATED,
            aggregate_type="Product",
            aggregate_id=product_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={"product_id": product_id, "product_type": product_type, "name": name},
        )

    @classmethod
    def product_bom_item_added(
        cls,
        organization_id: str,
        product_id: str,
        material_id: str,
        weight_pct: float | None,
        actor_id: str | None = None,
    ) -> DomainEvent:
        return cls(
            event_type=ProductEventType.BOM_ITEM_ADDED,
            aggregate_type="Product",
            aggregate_id=product_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={
                "product_id": product_id,
                "material_id": material_id,
                "weight_pct": weight_pct,
            },
        )

    @classmethod
    def material_created(
        cls,
        organization_id: str,
        material_id: str,
        material_type: str,
        name: str,
        actor_id: str | None = None,
    ) -> DomainEvent:
        return cls(
            event_type=MaterialEventType.MATERIAL_CREATED,
            aggregate_type="Material",
            aggregate_id=material_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={"material_id": material_id, "material_type": material_type, "name": name},
        )

    @classmethod
    def material_compliance_flag_set(
        cls,
        organization_id: str,
        material_id: str,
        regulation: str,
        compliance_status: str,
        actor_id: str | None = None,
    ) -> DomainEvent:
        return cls(
            event_type=MaterialEventType.COMPLIANCE_FLAG_SET,
            aggregate_type="Material",
            aggregate_id=material_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={
                "material_id": material_id,
                "regulation": regulation,
                "compliance_status": compliance_status,
            },
        )

    @classmethod
    def material_sourcing_added(
        cls,
        organization_id: str,
        material_id: str,
        supplier_id: str,
        country_of_origin: str | None,
        actor_id: str | None = None,
    ) -> DomainEvent:
        return cls(
            event_type=MaterialEventType.SOURCING_ADDED,
            aggregate_type="Material",
            aggregate_id=material_id,
            organization_id=organization_id,
            actor_id=actor_id,
            payload={
                "material_id": material_id,
                "supplier_id": supplier_id,
                "country_of_origin": country_of_origin,
            },
        )
