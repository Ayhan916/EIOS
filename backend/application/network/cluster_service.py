"""M38 Incident Cluster Service — CRUD and resolution."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

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
            entity_type="incident_cluster",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("cluster_audit_failed", action=action, error=str(exc))


async def list_clusters(
    organization_id: str,
    cluster_status: str | None = None,
    limit: int = 50,
    session=None,
) -> list:
    from infrastructure.persistence.models.network import IncidentClusterModel
    from sqlalchemy import select

    stmt = select(IncidentClusterModel).where(
        IncidentClusterModel.organization_id == organization_id
    )
    if cluster_status:
        stmt = stmt.where(
            IncidentClusterModel.cluster_status == cluster_status.upper()
        )
    stmt = stmt.order_by(IncidentClusterModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_cluster(
    cluster_id: str,
    organization_id: str,
    session,
) -> object | None:
    from infrastructure.persistence.models.network import IncidentClusterModel
    from sqlalchemy import select

    stmt = select(IncidentClusterModel).where(
        IncidentClusterModel.id == cluster_id,
        IncidentClusterModel.organization_id == organization_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def resolve_cluster(
    cluster_id: str,
    organization_id: str,
    resolved_by: str,
    session,
) -> object:
    cluster = await get_cluster(cluster_id, organization_id, session)
    if cluster is None:
        raise ValueError(f"Cluster not found: {cluster_id}")
    if cluster.cluster_status == "RESOLVED":
        raise ValueError("Cluster already resolved")

    now = datetime.now(UTC)
    cluster.cluster_status = "RESOLVED"
    cluster.resolved_at = now
    cluster.resolved_by = resolved_by
    cluster.updated_at = now
    await session.flush()

    await _log_audit_event(
        session,
        "network.cluster.resolved",
        cluster.id,
        detail=f"resolved_by={resolved_by}",
        actor_id=resolved_by,
    )
    return cluster
