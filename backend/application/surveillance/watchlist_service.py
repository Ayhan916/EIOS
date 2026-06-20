"""M37 Supplier Watchlist Service.

Manual and automatic watchlist management.
Auto-triggers: repeated HIGH alerts, score deterioration, compliance gaps.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from application.surveillance.metrics import surveillance_counters

logger = structlog.get_logger(__name__)

_AUTO_ALERT_THRESHOLD = 3       # HIGH/CRITICAL alerts in last 30 days
_SCORE_DROP_THRESHOLD = -15.0   # ESG drop >= 15 points


async def _log_audit_event(
    session,
    action: str,
    entity_id: str,
    detail: str = "",
    actor_id: str = "surveillance_engine",
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
            entity_type="supplier_watchlist",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("watchlist_audit_failed", action=action, error=str(exc))


async def get_watchlist_entry(
    organization_id: str, supplier_id: str, session
) -> object | None:
    """Return the ACTIVE watchlist entry for (org, supplier), or None."""
    from infrastructure.persistence.models.surveillance import SupplierWatchlistModel
    from sqlalchemy import select

    stmt = select(SupplierWatchlistModel).where(
        SupplierWatchlistModel.organization_id == organization_id,
        SupplierWatchlistModel.supplier_id == supplier_id,
        SupplierWatchlistModel.watchlist_status == "ACTIVE",
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _get_any_watchlist_entry(
    organization_id: str, supplier_id: str, session
) -> object | None:
    """Return any watchlist entry for (org, supplier) regardless of status."""
    from infrastructure.persistence.models.surveillance import SupplierWatchlistModel
    from sqlalchemy import select

    stmt = select(SupplierWatchlistModel).where(
        SupplierWatchlistModel.organization_id == organization_id,
        SupplierWatchlistModel.supplier_id == supplier_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add_to_watchlist(
    *,
    organization_id: str,
    supplier_id: str,
    watch_reason: str,
    severity: str = "HIGH",
    added_by_type: str = "MANUAL",
    created_by: str | None = None,
    session,
) -> object:
    """Add a supplier to the watchlist.

    P0 fix: if the supplier was previously REMOVED, reactivates the existing row
    instead of inserting a new one (which would violate the unique constraint on
    organization_id + supplier_id).

    P2 fix: severity upgrades are audited; actor_id is propagated.
    """
    from infrastructure.persistence.models.surveillance import SupplierWatchlistModel

    _actor = created_by or "surveillance_engine"

    # --- 1. Already ACTIVE: upgrade severity if escalating, then return ---
    existing_active = await get_watchlist_entry(organization_id, supplier_id, session)
    if existing_active is not None:
        if _severity_rank(severity) > _severity_rank(existing_active.severity):
            old_severity = existing_active.severity
            existing_active.severity = severity.upper()
            existing_active.watch_reason = watch_reason
            existing_active.updated_at = datetime.now(UTC)
            await session.flush()
            await _log_audit_event(
                session,
                "surveillance.watchlist.severity_upgraded",
                existing_active.id,
                detail=f"from={old_severity} to={severity.upper()} supplier={supplier_id}",
                actor_id=_actor,
            )
        return existing_active

    # --- 2. Previously REMOVED: reactivate in-place (avoids IntegrityError) ---
    existing_any = await _get_any_watchlist_entry(organization_id, supplier_id, session)
    if existing_any is not None:
        now = datetime.now(UTC)
        existing_any.watchlist_status = "ACTIVE"
        existing_any.severity = severity.upper()
        existing_any.watch_reason = watch_reason
        existing_any.added_by_type = added_by_type
        existing_any.created_by = created_by
        existing_any.removed_at = None
        existing_any.removed_by = None
        existing_any.updated_at = now
        await session.flush()
        surveillance_counters.record_watchlist_added()
        await _log_audit_event(
            session,
            "surveillance.watchlist.added",
            existing_any.id,
            detail=f"supplier={supplier_id} reason={watch_reason[:100]} (reactivated)",
            actor_id=_actor,
        )
        return existing_any

    # --- 3. New entry ---
    now = datetime.now(UTC)
    entry = SupplierWatchlistModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        supplier_id=supplier_id,
        watch_reason=watch_reason,
        severity=severity.upper(),
        added_by_type=added_by_type,
        created_by=created_by,
        watchlist_status="ACTIVE",
    )
    session.add(entry)
    await session.flush()

    surveillance_counters.record_watchlist_added()
    await _log_audit_event(
        session,
        "surveillance.watchlist.added",
        entry.id,
        detail=f"supplier={supplier_id} reason={watch_reason[:100]}",
        actor_id=_actor,
    )
    return entry


async def remove_from_watchlist(
    organization_id: str,
    supplier_id: str,
    removed_by: str,
    session,
) -> object:
    existing = await get_watchlist_entry(organization_id, supplier_id, session)
    if existing is None:
        raise ValueError(f"Supplier {supplier_id} is not on the watchlist")

    now = datetime.now(UTC)
    existing.watchlist_status = "REMOVED"
    existing.removed_at = now
    existing.removed_by = removed_by
    existing.updated_at = now
    await session.flush()

    await _log_audit_event(
        session,
        "surveillance.watchlist.removed",
        existing.id,
        detail=f"supplier={supplier_id}",
        actor_id=removed_by,
    )
    return existing


async def list_watchlist(
    organization_id: str,
    *,
    active_only: bool = True,
    limit: int = 100,
    session,
) -> list:
    from infrastructure.persistence.models.surveillance import SupplierWatchlistModel
    from sqlalchemy import select

    stmt = select(SupplierWatchlistModel).where(
        SupplierWatchlistModel.organization_id == organization_id
    )
    if active_only:
        stmt = stmt.where(SupplierWatchlistModel.watchlist_status == "ACTIVE")
    stmt = stmt.order_by(SupplierWatchlistModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def auto_watchlist_from_alerts(
    organization_id: str,
    supplier_id: str,
    session,
) -> object | None:
    """Auto-add to watchlist if supplier has >= threshold HIGH/CRITICAL alerts."""
    from infrastructure.persistence.models.agent_monitoring import AgentAlertModel
    from sqlalchemy import func, select
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(days=30)
    count_stmt = select(func.count()).select_from(AgentAlertModel).where(
        AgentAlertModel.organization_id == organization_id,
        AgentAlertModel.supplier_id == supplier_id,
        AgentAlertModel.severity.in_(["HIGH", "CRITICAL"]),
        AgentAlertModel.created_at >= cutoff,
        AgentAlertModel.acknowledged_at.is_(None),
    )
    count = (await session.execute(count_stmt)).scalar_one()
    if count >= _AUTO_ALERT_THRESHOLD:
        return await add_to_watchlist(
            organization_id=organization_id,
            supplier_id=supplier_id,
            watch_reason=f"Auto-flagged: {count} unacknowledged HIGH/CRITICAL alerts in 30 days",
            severity="HIGH",
            added_by_type="AUTO_ALERTS",
            session=session,
        )
    return None


async def auto_watchlist_from_score_drop(
    organization_id: str,
    supplier_id: str,
    esg_delta: float,
    session,
) -> object | None:
    """Auto-add when ESG score drops more than threshold."""
    if esg_delta <= _SCORE_DROP_THRESHOLD:
        return await add_to_watchlist(
            organization_id=organization_id,
            supplier_id=supplier_id,
            watch_reason=f"Auto-flagged: ESG score dropped {abs(esg_delta):.1f} points",
            severity="CRITICAL" if esg_delta <= -20.0 else "HIGH",
            added_by_type="AUTO_SCORE",
            session=session,
        )
    return None


def _severity_rank(severity: str) -> int:
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(severity.upper(), 0)
