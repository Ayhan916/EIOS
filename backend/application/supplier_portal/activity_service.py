"""M35 Supplier Activity Service.

Query and append to the immutable supplier activity timeline.

All queries are scoped by supplier_id — no cross-supplier access.

log_event()           — append an event (used by other services)
list_activity()       — paginated timeline for a supplier
list_activity_by_user()— filter by supplier_user_id
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


async def log_event(
    supplier_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    supplier_user_id: str | None = None,
    metadata: dict | None = None,
    session=None,
) -> object:
    """Append an immutable activity event."""
    from infrastructure.persistence.models.supplier_portal import SupplierActivityEventModel

    now = datetime.now(UTC)
    model = SupplierActivityEventModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        supplier_user_id=supplier_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata or {}),
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    try:
        await session.flush()
    except Exception as exc:
        logger.warning("activity_log_failed", error=str(exc))
    return model


async def list_activity(
    supplier_id: str,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session=None,
) -> list:
    """Paginated timeline for a supplier (newest first)."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import SupplierActivityEventModel

    stmt = select(SupplierActivityEventModel).where(
        SupplierActivityEventModel.supplier_id == supplier_id
    )
    if event_type:
        stmt = stmt.where(SupplierActivityEventModel.event_type == event_type)
    stmt = stmt.order_by(SupplierActivityEventModel.created_at.desc()).limit(limit).offset(offset)
    return list((await session.execute(stmt)).scalars().all())


async def list_activity_by_user(
    supplier_id: str,
    supplier_user_id: str,
    limit: int = 50,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import SupplierActivityEventModel

    stmt = (
        select(SupplierActivityEventModel)
        .where(
            SupplierActivityEventModel.supplier_id == supplier_id,
            SupplierActivityEventModel.supplier_user_id == supplier_user_id,
        )
        .order_by(SupplierActivityEventModel.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
