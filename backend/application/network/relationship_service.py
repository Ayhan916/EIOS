"""M38 Supplier Relationship CRUD Service.

Handles create / get / list / remove for SupplierRelationshipModel.
All state changes emit audit events.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from application.network.metrics import network_counters

logger = structlog.get_logger(__name__)


async def _log_audit_event(
    session,
    action: str,
    entity_id: str,
    detail: str = "",
    actor_id: str = "network_engine",
) -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel

    now = datetime.now(UTC)
    try:
        event = AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action=action,
            actor_id=actor_id,
            entity_type="supplier_relationship",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("network_rel_audit_failed", action=action, error=str(exc))


_VALID_TYPES = {
    "PARENT_COMPANY", "SUBSIDIARY", "SISTER_COMPANY", "SHARED_COUNTRY",
    "SHARED_SECTOR", "SHARED_SUPPLY_CHAIN", "SHARED_INCIDENT",
    "SHARED_LOGISTICS", "SHARED_REGULATORY_EXPOSURE", "CUSTOM",
}


async def create_relationship(
    *,
    organization_id: str,
    supplier_id: str,
    related_supplier_id: str,
    relationship_type: str,
    confidence: float = 1.0,
    source: str = "MANUAL",
    rationale: str = "",
    created_by: str | None = None,
    session,
) -> object:
    from infrastructure.persistence.models.network import SupplierRelationshipModel
    from sqlalchemy import select

    rel_type = relationship_type.upper()
    if rel_type not in _VALID_TYPES:
        raise ValueError(f"Invalid relationship_type: {rel_type}")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError("confidence must be between 0.0 and 1.0")
    if supplier_id == related_supplier_id:
        raise ValueError("supplier_id and related_supplier_id must differ")

    # P1 M38.1: verify both suppliers belong to this organization
    from infrastructure.persistence.models.supplier import SupplierModel

    for sid in (supplier_id, related_supplier_id):
        sup_stmt = select(SupplierModel.id).where(
            SupplierModel.id == sid,
            SupplierModel.organization_id == organization_id,
        )
        if (await session.execute(sup_stmt)).scalar_one_or_none() is None:
            raise ValueError(f"Supplier not found in organization: {sid}")

    # P1 M38.1: prevent duplicate ACTIVE relationships of the same type
    dup_stmt = select(SupplierRelationshipModel.id).where(
        SupplierRelationshipModel.organization_id == organization_id,
        SupplierRelationshipModel.supplier_id == supplier_id,
        SupplierRelationshipModel.related_supplier_id == related_supplier_id,
        SupplierRelationshipModel.relationship_type == rel_type,
        SupplierRelationshipModel.relationship_status == "ACTIVE",
    )
    if (await session.execute(dup_stmt)).scalar_one_or_none() is not None:
        raise ValueError(
            f"Active {rel_type} relationship already exists between these suppliers"
        )

    now = datetime.now(UTC)
    rel = SupplierRelationshipModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        created_by=created_by,
        organization_id=organization_id,
        supplier_id=supplier_id,
        related_supplier_id=related_supplier_id,
        relationship_type=rel_type,
        confidence=round(confidence, 4),
        source=source,
        rationale=rationale,
        relationship_status="ACTIVE",
        calculation_inputs={
            "source": source,
            "confidence": confidence,
            "created_by": created_by,
        },
    )
    session.add(rel)
    await session.flush()

    network_counters.record_relationship_created()
    await _log_audit_event(
        session,
        "network.relationship.created",
        rel.id,
        detail=(
            f"type={rel_type} supplier={supplier_id} "
            f"related={related_supplier_id} source={source}"
        ),
        actor_id=created_by or "network_engine",
    )
    return rel


async def get_relationship(
    relationship_id: str,
    organization_id: str,
    session,
) -> object | None:
    from infrastructure.persistence.models.network import SupplierRelationshipModel
    from sqlalchemy import select

    stmt = select(SupplierRelationshipModel).where(
        SupplierRelationshipModel.id == relationship_id,
        SupplierRelationshipModel.organization_id == organization_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_relationships(
    organization_id: str,
    supplier_id: str | None = None,
    relationship_type: str | None = None,
    relationship_status: str | None = None,
    limit: int = 100,
    session=None,
) -> list:
    from application.network.graph_service import get_relationships
    return await get_relationships(
        organization_id=organization_id,
        supplier_id=supplier_id,
        relationship_type=relationship_type,
        limit=limit,
        session=session,
    )


async def remove_relationship(
    relationship_id: str,
    organization_id: str,
    removed_by: str,
    session,
) -> object:
    from infrastructure.persistence.models.network import SupplierRelationshipModel
    from sqlalchemy import select

    stmt = select(SupplierRelationshipModel).where(
        SupplierRelationshipModel.id == relationship_id,
        SupplierRelationshipModel.organization_id == organization_id,
    )
    rel = (await session.execute(stmt)).scalar_one_or_none()
    if rel is None:
        raise ValueError(f"Relationship not found: {relationship_id}")
    if rel.relationship_status == "REMOVED":
        raise ValueError("Relationship already removed")

    now = datetime.now(UTC)
    rel.relationship_status = "REMOVED"
    rel.removed_at = now
    rel.removed_by = removed_by
    rel.updated_at = now
    await session.flush()

    await _log_audit_event(
        session,
        "network.relationship.removed",
        rel.id,
        detail=f"removed_by={removed_by}",
        actor_id=removed_by,
    )
    return rel
