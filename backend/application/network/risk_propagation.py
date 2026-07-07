"""M38 Network Risk Propagation Engine.

Propagates risk signals outward from an origin supplier through the relationship
graph. Confidence and severity attenuate deterministically with distance.

Attenuation model:
  propagated_confidence = source_confidence
                        × relationship_confidence
                        × ATTENUATION_FACTOR ^ (distance - 1)

  ATTENUATION_FACTOR = 0.6  (40% decay per additional hop)
  MIN_CONFIDENCE     = 0.10  (signals below this threshold are not stored)

Severity downgrades by distance:
  distance 1 → original severity
  distance 2 → one step down (CRITICAL→HIGH, HIGH→MEDIUM, MEDIUM→LOW)
  distance 3+ → two steps down (floor at LOW)
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
            entity_type="network_exposure_signal",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("network_signal_audit_failed", action=action, error=str(exc))


ATTENUATION_FACTOR = 0.6
MIN_CONFIDENCE = 0.10

_SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
_SEVERITY_RANK = {s: i for i, s in enumerate(_SEVERITY_ORDER)}


def _attenuate_severity(severity: str, distance: int) -> str:
    """Downgrade severity by (distance-1) steps, flooring at LOW."""
    rank = _SEVERITY_RANK.get(severity.upper(), 2)
    new_rank = max(0, rank - (distance - 1))
    return _SEVERITY_ORDER[new_rank]


async def propagate_signal(
    organization_id: str,
    origin_supplier_id: str,
    source_confidence: float,
    source_severity: str,
    exposure_type: str,
    rationale: str,
    source_signal_id: str | None = None,
    source_finding_id: str | None = None,
    max_depth: int = 3,
    session=None,
) -> list[object]:
    """BFS from origin, emitting NetworkExposureSignalModel for each reachable node.

    Skips nodes where propagated_confidence < MIN_CONFIDENCE.
    Deduplicates against existing ACTIVE signals in the DB and against
    signals created in the same call (confidence-revision race protection).
    Returns all created exposure records.
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.network import (
        NetworkExposureSignalModel,
        SupplierRelationshipModel,
    )

    # Load all active relationships in one query
    adj_stmt = select(
        SupplierRelationshipModel.supplier_id,
        SupplierRelationshipModel.related_supplier_id,
        SupplierRelationshipModel.confidence,
    ).where(
        SupplierRelationshipModel.organization_id == organization_id,
        SupplierRelationshipModel.relationship_status == "ACTIVE",
    )
    rows = (await session.execute(adj_stmt)).all()

    # Build undirected adjacency with edge confidence
    adj: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        adj.setdefault(row.supplier_id, []).append((row.related_supplier_id, row.confidence))
        adj.setdefault(row.related_supplier_id, []).append((row.supplier_id, row.confidence))

    # P0 M38.1: load existing ACTIVE signals for this origin+type so we skip them
    existing_stmt = select(NetworkExposureSignalModel.impacted_supplier_id).where(
        NetworkExposureSignalModel.organization_id == organization_id,
        NetworkExposureSignalModel.origin_supplier_id == origin_supplier_id,
        NetworkExposureSignalModel.exposure_type == exposure_type,
        NetworkExposureSignalModel.exposure_status == "ACTIVE",
    )
    already_signaled: set[str] = set((await session.execute(existing_stmt)).scalars().all())

    # BFS
    from collections import deque

    # (node, distance, path, cumulative_confidence)
    queue: deque[tuple[str, int, list[str], float]] = deque(
        [(origin_supplier_id, 0, [origin_supplier_id], source_confidence)]
    )
    visited: dict[str, float] = {origin_supplier_id: source_confidence}
    # P0 M38.1: tracks nodes persisted in this call to prevent confidence-revision duplicates
    persisted_nodes: set[str] = set()
    created: list[object] = []
    now = datetime.now(UTC)

    while queue:
        node, dist, path, conf = queue.popleft()
        if dist >= max_depth:
            continue

        for neighbor, edge_conf in adj.get(node, []):
            hop_conf = conf * edge_conf * (ATTENUATION_FACTOR**dist)
            if hop_conf < MIN_CONFIDENCE:
                continue
            if neighbor == origin_supplier_id:
                continue
            if neighbor in visited and visited[neighbor] >= hop_conf:
                continue
            visited[neighbor] = hop_conf

            new_path = path + [neighbor]
            new_dist = dist + 1
            attenuated_severity = _attenuate_severity(source_severity, new_dist)

            # Skip if already persisted (same call) or exists in DB
            if neighbor not in persisted_nodes and neighbor not in already_signaled:
                persisted_nodes.add(neighbor)
                exposure = NetworkExposureSignalModel(
                    id=str(uuid.uuid4()),
                    status="Active",
                    version=1,
                    created_at=now,
                    updated_at=now,
                    organization_id=organization_id,
                    origin_supplier_id=origin_supplier_id,
                    impacted_supplier_id=neighbor,
                    exposure_type=exposure_type,
                    propagation_path=new_path,
                    path_length=new_dist,
                    confidence=round(hop_conf, 4),
                    severity=attenuated_severity,
                    rationale=f"{rationale} (propagated via {new_dist} hop(s))",
                    source_signal_id=source_signal_id,
                    source_finding_id=source_finding_id,
                    exposure_status="ACTIVE",
                    detected_at=now,
                    calculation_inputs={
                        "source_confidence": source_confidence,
                        "source_severity": source_severity,
                        "attenuation_factor": ATTENUATION_FACTOR,
                        "edge_confidence": edge_conf,
                        "distance": new_dist,
                    },
                )
                session.add(exposure)
                network_counters.record_exposure_created()
                created.append(exposure)

            queue.append((neighbor, new_dist, new_path, hop_conf))

    if created:
        await session.flush()
        await _log_audit_event(
            session,
            "network.signal.propagated",
            origin_supplier_id,
            detail=(
                f"exposure_type={exposure_type} signals_created={len(created)} "
                f"origin={origin_supplier_id}"
            ),
        )

    return created


async def list_exposure_signals(
    organization_id: str,
    impacted_supplier_id: str | None = None,
    origin_supplier_id: str | None = None,
    exposure_status: str | None = None,
    limit: int = 100,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import NetworkExposureSignalModel

    stmt = select(NetworkExposureSignalModel).where(
        NetworkExposureSignalModel.organization_id == organization_id
    )
    if impacted_supplier_id:
        stmt = stmt.where(NetworkExposureSignalModel.impacted_supplier_id == impacted_supplier_id)
    if origin_supplier_id:
        stmt = stmt.where(NetworkExposureSignalModel.origin_supplier_id == origin_supplier_id)
    if exposure_status:
        stmt = stmt.where(NetworkExposureSignalModel.exposure_status == exposure_status.upper())
    stmt = stmt.order_by(NetworkExposureSignalModel.detected_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
