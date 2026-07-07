"""M37 Risk Episode Service.

Episodes group related surveillance signals into a risk narrative.
Status: OPEN → MONITORING → RESOLVED (humans resolve, agents can escalate to MONITORING).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from application.surveillance.metrics import surveillance_counters

logger = structlog.get_logger(__name__)


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
            entity_type="risk_episode",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("episode_audit_failed", action=action, error=str(exc))


async def create_episode(
    *,
    organization_id: str,
    title: str,
    description: str,
    severity: str = "HIGH",
    supplier_id: str | None = None,
    created_by: str | None = None,
    session,
) -> object:
    from infrastructure.persistence.models.surveillance import RiskEpisodeModel

    now = datetime.now(UTC)
    episode = RiskEpisodeModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        supplier_id=supplier_id,
        title=title,
        description=description,
        severity=severity.upper(),
        episode_status="OPEN",
        started_at=now,
        signal_count=0,
    )
    session.add(episode)
    await session.flush()

    surveillance_counters.record_episode_created()
    await _log_audit_event(
        session,
        "surveillance.episode.created",
        episode.id,
        detail=title,
        actor_id=created_by or "surveillance_engine",
    )
    return episode


async def attach_signal_to_episode(
    episode_id: str,
    signal,
    session,
    organization_id: str | None = None,
) -> None:
    """Link a signal to an episode and increment signal count.

    P3 fix: organization_id guard prevents cross-tenant attachment.
    When provided, the episode lookup is scoped to the given org.
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.surveillance import RiskEpisodeModel

    stmt = select(RiskEpisodeModel).where(RiskEpisodeModel.id == episode_id)
    if organization_id is not None:
        stmt = stmt.where(RiskEpisodeModel.organization_id == organization_id)
    episode = (await session.execute(stmt)).scalar_one_or_none()
    if episode is None:
        return

    signal.episode_id = episode_id
    signal.updated_at = datetime.now(UTC)
    episode.signal_count = (episode.signal_count or 0) + 1
    episode.updated_at = datetime.now(UTC)
    await session.flush()


async def transition_episode(
    episode_id: str,
    organization_id: str,
    new_status: str,
    user_id: str,
    session,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.surveillance import RiskEpisodeModel

    # P1 governance fix: MONITORING → OPEN is removed. Once escalated to
    # monitoring, the episode must progress forward to RESOLVED, not backward.
    allowed = {
        "OPEN": ["MONITORING", "RESOLVED"],
        "MONITORING": ["RESOLVED"],
        "RESOLVED": [],
    }

    stmt = select(RiskEpisodeModel).where(
        RiskEpisodeModel.id == episode_id,
        RiskEpisodeModel.organization_id == organization_id,
    )
    episode = (await session.execute(stmt)).scalar_one_or_none()
    if episode is None:
        raise ValueError(f"Episode not found: {episode_id}")

    new_status_upper = new_status.upper()
    if new_status_upper not in allowed.get(episode.episode_status, []):
        raise ValueError(f"Cannot transition from {episode.episode_status} to {new_status_upper}")

    now = datetime.now(UTC)
    episode.episode_status = new_status_upper
    episode.updated_at = now
    if new_status_upper == "RESOLVED":
        episode.closed_at = now
        episode.resolved_by = user_id
    await session.flush()

    await _log_audit_event(
        session,
        f"surveillance.episode.{new_status_upper.lower()}",
        episode.id,
        detail=f"by={user_id}",
        actor_id=user_id,
    )
    return episode


async def list_episodes(
    organization_id: str,
    *,
    supplier_id: str | None = None,
    episode_status: str | None = None,
    limit: int = 50,
    session,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.surveillance import RiskEpisodeModel

    stmt = select(RiskEpisodeModel).where(RiskEpisodeModel.organization_id == organization_id)
    if supplier_id:
        stmt = stmt.where(RiskEpisodeModel.supplier_id == supplier_id)
    if episode_status:
        stmt = stmt.where(RiskEpisodeModel.episode_status == episode_status.upper())
    stmt = stmt.order_by(RiskEpisodeModel.started_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_episode(episode_id: str, organization_id: str, session) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.surveillance import RiskEpisodeModel

    stmt = select(RiskEpisodeModel).where(
        RiskEpisodeModel.id == episode_id,
        RiskEpisodeModel.organization_id == organization_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()
