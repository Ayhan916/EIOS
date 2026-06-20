"""M37 Surveillance Signal Service.

Immutable signal creation, status transitions, deduplication, audit, notifications.
Signals are observations — never modified after creation.
Status transitions: ACTIVE → ACKNOWLEDGED | EXPIRED | DISMISSED.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog

from application.surveillance.metrics import surveillance_counters

logger = structlog.get_logger(__name__)

_SIGNAL_TTL_DAYS: dict[str, int] = {
    "DRIFT": 30,
    "EMERGING_RISK": 30,
    "CORRELATED_RISK": 60,
    "EARLY_WARNING": 14,
    "PREDICTIVE_ESCALATION": 90,
}


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
            entity_type="surveillance_signal",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("surveillance_audit_failed", action=action, error=str(exc))


async def find_active_duplicate(
    organization_id: str,
    supplier_id: str | None,
    signal_type: str,
    dedupe_key: str | None,
    session,
) -> object | None:
    """Return an ACTIVE signal with the same dedupe_key, or None."""
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from sqlalchemy import select

    if dedupe_key is None:
        return None

    stmt = (
        select(SurveillanceSignalModel)
        .where(
            SurveillanceSignalModel.organization_id == organization_id,
            SurveillanceSignalModel.dedupe_key == dedupe_key,
            SurveillanceSignalModel.signal_status == "ACTIVE",
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_signal(
    *,
    organization_id: str,
    signal_type: str,
    source_type: str,
    severity: str,
    title: str,
    description: str,
    confidence: float = 1.0,
    supplier_id: str | None = None,
    source_id: str | None = None,
    episode_id: str | None = None,
    dedupe_key: str | None = None,
    explainability: dict | None = None,
    skip_if_active: bool = True,
    session,
) -> object:
    """Create a new surveillance signal.

    Immutable at creation. Deduplication via dedupe_key prevents duplicate
    ACTIVE signals for the same event.
    """
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    now = datetime.now(UTC)

    if skip_if_active and dedupe_key:
        existing = await find_active_duplicate(
            organization_id, supplier_id, signal_type, dedupe_key, session
        )
        if existing is not None:
            return existing

    ttl_days = _SIGNAL_TTL_DAYS.get(signal_type, 30)
    expires_at = now + timedelta(days=ttl_days)

    # Explainability snapshot — immutable
    snapshot = {
        "rule_triggered": explainability.get("rule_triggered", "") if explainability else "",
        "source_data": explainability.get("source_data", {}) if explainability else {},
        "thresholds": explainability.get("thresholds", {}) if explainability else {},
        "confidence": confidence,
        "detected_at": now.isoformat(),
        "signal_type": signal_type,
        "severity": severity,
        **(explainability or {}),
    }

    signal = SurveillanceSignalModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        supplier_id=supplier_id,
        source_type=source_type,
        source_id=source_id,
        signal_type=signal_type,
        severity=severity.upper(),
        confidence=confidence,
        title=title,
        description=description,
        detected_at=now,
        expires_at=expires_at,
        signal_status="ACTIVE",
        episode_id=episode_id,
        explainability_json=snapshot,
        dedupe_key=dedupe_key,
    )
    session.add(signal)
    await session.flush()

    surveillance_counters.record_signal_created(severity=severity.upper())
    await _log_audit_event(session, "surveillance.signal.created", signal.id, detail=title)
    await _maybe_notify(signal, organization_id, session)

    # M39 cross-module: critical signals → ESGAction (idempotent)
    if severity.upper() == "CRITICAL":
        try:
            from application.operating_system.action_service import ingest_from_module_idempotent
            await ingest_from_module_idempotent(
                organization_id=organization_id,
                source_type="SURVEILLANCE_SIGNAL",
                source_id=signal.id,
                title=f"Critical surveillance signal: {title}",
                priority="CRITICAL",
                description=description,
                session=session,
            )
        except Exception:
            pass  # Do not fail signal creation on M39 wiring error

    return signal


async def _maybe_notify(signal, organization_id: str, session) -> None:
    """Send at most one HIGH/CRITICAL surveillance notification per user per hour.

    Uses an hour-granularity dedupe key so the M24 notification layer
    suppresses all but the first alert within each clock hour, preventing
    storms when many signals fire in a single scheduler cycle.
    """
    if signal.severity not in ("HIGH", "CRITICAL"):
        return
    try:
        from application.notification_service import notify
        from infrastructure.persistence.models.user import UserModel
        from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
        from sqlalchemy import func, select

        users_stmt = select(UserModel).where(
            UserModel.organization_id == organization_id,
            UserModel.is_active == True,  # noqa: E712
        )
        users = list((await session.execute(users_stmt)).scalars().all())
        if not users:
            return

        # Count active HIGH/CRITICAL signals created this hour (including current).
        hour_start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        count_stmt = (
            select(func.count())
            .select_from(SurveillanceSignalModel)
            .where(
                SurveillanceSignalModel.organization_id == organization_id,
                SurveillanceSignalModel.signal_status == "ACTIVE",
                SurveillanceSignalModel.severity.in_(["HIGH", "CRITICAL"]),
                SurveillanceSignalModel.detected_at >= hour_start,
            )
        )
        alert_count = (await session.execute(count_stmt)).scalar_one()

        # One dedupe key per (user, org, hour) — M24 layer drops subsequent calls.
        hour_str = datetime.now(UTC).strftime("%Y-%m-%dT%H")
        for user in users:
            dedupe = f"surveillance_digest:{organization_id}:{user.id}:{hour_str}"
            await notify(
                session=session,
                user_id=user.id,
                organization_id=organization_id,
                notification_type="surveillance_alert",
                title=f"{alert_count} surveillance alert(s) detected",
                body=f"Latest: [{signal.severity}] {signal.title[:200]}",
                entity_type="surveillance_signal",
                entity_id=signal.id,
                dedupe_key=dedupe,
            )
    except Exception as exc:
        logger.warning("surveillance_notification_failed", signal_id=signal.id, error=str(exc))


async def acknowledge_signal(
    signal_id: str,
    organization_id: str,
    acknowledged_by: str,
    session,
) -> object:
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from sqlalchemy import select

    stmt = select(SurveillanceSignalModel).where(
        SurveillanceSignalModel.id == signal_id,
        SurveillanceSignalModel.organization_id == organization_id,
    )
    signal = (await session.execute(stmt)).scalar_one_or_none()
    if signal is None:
        raise ValueError(f"Signal not found: {signal_id}")
    if signal.signal_status != "ACTIVE":
        raise ValueError(f"Cannot acknowledge signal with status: {signal.signal_status}")

    now = datetime.now(UTC)
    signal.signal_status = "ACKNOWLEDGED"
    signal.acknowledged_by = acknowledged_by
    signal.acknowledged_at = now
    signal.updated_at = now
    await session.flush()

    await _log_audit_event(
        session, "surveillance.signal.acknowledged", signal.id,
        actor_id=acknowledged_by,
    )
    return signal


async def dismiss_signal(
    signal_id: str,
    organization_id: str,
    dismissed_by: str,
    session,
) -> object:
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from sqlalchemy import select

    stmt = select(SurveillanceSignalModel).where(
        SurveillanceSignalModel.id == signal_id,
        SurveillanceSignalModel.organization_id == organization_id,
    )
    signal = (await session.execute(stmt)).scalar_one_or_none()
    if signal is None:
        raise ValueError(f"Signal not found: {signal_id}")
    if signal.signal_status not in ("ACTIVE", "ACKNOWLEDGED"):
        raise ValueError(f"Cannot dismiss signal with status: {signal.signal_status}")

    signal.signal_status = "DISMISSED"
    signal.acknowledged_by = dismissed_by
    signal.updated_at = datetime.now(UTC)
    await session.flush()

    await _log_audit_event(
        session, "surveillance.signal.dismissed", signal.id,
        actor_id=dismissed_by,
    )
    return signal


async def expire_stale_signals(session) -> int:
    """Expire ACTIVE signals past their expires_at. Returns count.

    Emits surveillance.signal.expired audit event for every expired signal.
    """
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from sqlalchemy import select

    now = datetime.now(UTC)
    stmt = select(SurveillanceSignalModel).where(
        SurveillanceSignalModel.signal_status == "ACTIVE",
        SurveillanceSignalModel.expires_at <= now,
    )
    stale = list((await session.execute(stmt)).scalars().all())
    for s in stale:
        s.signal_status = "EXPIRED"
        s.updated_at = now
        await _log_audit_event(
            session, "surveillance.signal.expired", s.id, detail="ttl_expired"
        )
    await session.flush()
    return len(stale)


async def list_signals(
    organization_id: str,
    *,
    supplier_id: str | None = None,
    signal_type: str | None = None,
    severity: str | None = None,
    signal_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session,
) -> list:
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from sqlalchemy import select

    stmt = select(SurveillanceSignalModel).where(
        SurveillanceSignalModel.organization_id == organization_id
    )
    if supplier_id:
        stmt = stmt.where(SurveillanceSignalModel.supplier_id == supplier_id)
    if signal_type:
        stmt = stmt.where(SurveillanceSignalModel.signal_type == signal_type)
    if severity:
        stmt = stmt.where(SurveillanceSignalModel.severity == severity.upper())
    if signal_status:
        stmt = stmt.where(SurveillanceSignalModel.signal_status == signal_status.upper())
    stmt = stmt.order_by(SurveillanceSignalModel.detected_at.desc()).offset(offset).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_signal(signal_id: str, organization_id: str, session) -> object | None:
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from sqlalchemy import select

    stmt = select(SurveillanceSignalModel).where(
        SurveillanceSignalModel.id == signal_id,
        SurveillanceSignalModel.organization_id == organization_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()
