"""M38 Cascading Risk Engine.

Detects risk spreading across related suppliers:
  - Multiple connected suppliers with HIGH/CRITICAL signals within a time window
  - Cluster deterioration (connected suppliers trending Deteriorating)
  - Shared root-cause groupings

Generates CASCADE_RISK NetworkExposureSignals and IncidentCluster records.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog

from application.network.metrics import network_counters

logger = structlog.get_logger(__name__)


async def _log_audit_event(
    session,
    action: str,
    entity_id: str,
    entity_type: str = "network_cascade",
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
            entity_type=entity_type,
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("network_cascade_audit_failed", action=action, error=str(exc))

_CASCADE_WINDOW_HOURS = 72
_CASCADE_MIN_SUPPLIERS = 2


async def detect_cascading_risk(
    organization_id: str,
    session,
) -> list[object]:
    """Detect supplier clusters with concurrent HIGH/CRITICAL signals.

    For each connected component with ≥2 suppliers carrying ACTIVE HIGH/CRITICAL
    signals, generate a CASCADE_RISK exposure signal originating from the highest-
    severity supplier.

    Returns list of created NetworkExposureSignalModel records.
    """
    from infrastructure.persistence.models.network import (
        NetworkExposureSignalModel,
        SupplierRelationshipModel,
    )
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
    from sqlalchemy import select

    cutoff = datetime.now(UTC) - timedelta(hours=_CASCADE_WINDOW_HOURS)

    # Suppliers with recent ACTIVE HIGH/CRITICAL signals
    sig_stmt = select(
        SurveillanceSignalModel.supplier_id,
        SurveillanceSignalModel.severity,
        SurveillanceSignalModel.id,
        SurveillanceSignalModel.title,
    ).where(
        SurveillanceSignalModel.organization_id == organization_id,
        SurveillanceSignalModel.signal_status == "ACTIVE",
        SurveillanceSignalModel.severity.in_(["HIGH", "CRITICAL"]),
        SurveillanceSignalModel.detected_at >= cutoff,
        SurveillanceSignalModel.supplier_id.is_not(None),
    )
    sig_rows = (await session.execute(sig_stmt)).all()

    if not sig_rows:
        return []

    # Best (highest severity) signal per supplier
    _rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    supplier_signals: dict[str, dict] = {}
    for row in sig_rows:
        sid = row.supplier_id
        if sid not in supplier_signals or _rank.get(row.severity, 0) > _rank.get(
            supplier_signals[sid]["severity"], 0
        ):
            supplier_signals[sid] = {
                "signal_id": row.id,
                "severity": row.severity,
                "title": row.title,
            }

    at_risk = set(supplier_signals.keys())
    if len(at_risk) < _CASCADE_MIN_SUPPLIERS:
        return []

    # Load adjacency
    rel_stmt = select(
        SupplierRelationshipModel.supplier_id,
        SupplierRelationshipModel.related_supplier_id,
    ).where(
        SupplierRelationshipModel.organization_id == organization_id,
        SupplierRelationshipModel.relationship_status == "ACTIVE",
    )
    rel_rows = (await session.execute(rel_stmt)).all()

    adj: dict[str, set[str]] = {}
    for row in rel_rows:
        adj.setdefault(row.supplier_id, set()).add(row.related_supplier_id)
        adj.setdefault(row.related_supplier_id, set()).add(row.supplier_id)

    # Find connected components among at-risk suppliers
    visited: set[str] = set()
    components: list[set[str]] = []
    for s in at_risk:
        if s in visited:
            continue
        component: set[str] = set()
        queue = [s]
        while queue:
            node = queue.pop()
            if node in visited or node not in at_risk:
                continue
            visited.add(node)
            component.add(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited and neighbor in at_risk:
                    queue.append(neighbor)
        if len(component) >= _CASCADE_MIN_SUPPLIERS:
            components.append(component)

    if not components:
        return []

    created = []
    now = datetime.now(UTC)

    for component in components:
        # Origin = highest-severity supplier in component
        origin = max(
            component,
            key=lambda s: _rank.get(supplier_signals[s]["severity"], 0),
        )
        origin_info = supplier_signals[origin]

        for impacted in component:
            if impacted == origin:
                continue

            # P0 M38.1: skip if ACTIVE CASCADE signal already exists for this pair
            dup_stmt = select(NetworkExposureSignalModel.id).where(
                NetworkExposureSignalModel.organization_id == organization_id,
                NetworkExposureSignalModel.origin_supplier_id == origin,
                NetworkExposureSignalModel.impacted_supplier_id == impacted,
                NetworkExposureSignalModel.exposure_type == "CASCADE",
                NetworkExposureSignalModel.exposure_status == "ACTIVE",
            )
            if (await session.execute(dup_stmt)).scalar_one_or_none() is not None:
                continue

            exposure = NetworkExposureSignalModel(
                id=str(uuid.uuid4()),
                status="Active",
                version=1,
                created_at=now,
                updated_at=now,
                organization_id=organization_id,
                origin_supplier_id=origin,
                impacted_supplier_id=impacted,
                exposure_type="CASCADE",
                propagation_path=[origin, impacted],
                path_length=1,
                confidence=0.75,
                severity=origin_info["severity"],
                rationale=(
                    f"Cascading risk: {len(component)} connected suppliers with "
                    f"concurrent HIGH/CRITICAL signals within {_CASCADE_WINDOW_HOURS}h window"
                ),
                source_signal_id=origin_info["signal_id"],
                exposure_status="ACTIVE",
                detected_at=now,
                calculation_inputs={
                    "window_hours": _CASCADE_WINDOW_HOURS,
                    "component_size": len(component),
                    "at_risk_suppliers": list(component),
                },
            )
            session.add(exposure)
            network_counters.record_exposure_created()
            created.append(exposure)

    if created:
        await session.flush()
        await _log_audit_event(
            session,
            "network.cascade.detected",
            organization_id,
            entity_type="network_cascade",
            detail=(
                f"component_size={len(components[0]) if components else 0} "
                f"signal_count={len(created)}"
            ),
        )

    return created


async def cluster_incidents(
    organization_id: str,
    session,
) -> list[object]:
    """Group findings and signals by shared root-cause patterns.

    Groups are formed by:
      - shared country
      - shared industry
      - shared regulatory framework failures

    Skips groupings with fewer than 2 affected suppliers.
    Returns created IncidentClusterModel records.
    """
    from infrastructure.persistence.models.network import IncidentClusterModel
    from infrastructure.persistence.models.finding import FindingModel
    from sqlalchemy import select

    try:
        finding_stmt = select(
            FindingModel.id,
            FindingModel.supplier_id,
            FindingModel.category,
            FindingModel.severity,
        ).where(
            FindingModel.organization_id == organization_id,
            FindingModel.finding_status.in_(["Open", "In Progress"]),
            FindingModel.supplier_id.is_not(None),
        )
        finding_rows = (await session.execute(finding_stmt)).all()
    except Exception:
        finding_rows = []

    by_category: dict[str, dict] = {}
    for row in finding_rows:
        cat = row.category or "Unknown"
        entry = by_category.setdefault(cat, {"suppliers": set(), "findings": []})
        entry["suppliers"].add(row.supplier_id)
        entry["findings"].append(row.id)

    created = []
    now = datetime.now(UTC)

    for category, data in by_category.items():
        if len(data["suppliers"]) < 2:
            continue

        cluster_name = f"Finding cluster: {category}"
        dedup_stmt = select(IncidentClusterModel).where(
            IncidentClusterModel.organization_id == organization_id,
            IncidentClusterModel.cluster_name == cluster_name,
            IncidentClusterModel.cluster_status == "ACTIVE",
        )
        existing = (await session.execute(dedup_stmt)).scalar_one_or_none()
        if existing is not None:
            # Update affected suppliers list
            existing_suppliers = set(existing.affected_supplier_ids)
            existing_suppliers.update(data["suppliers"])
            existing.affected_supplier_ids = list(existing_suppliers)
            existing.finding_ids = list(
                set(existing.finding_ids) | set(data["findings"])
            )
            existing.updated_at = now
            await session.flush()
            await _log_audit_event(
                session,
                "network.cluster.updated",
                existing.id,
                entity_type="incident_cluster",
                detail=f"category={category} supplier_count={len(existing.affected_supplier_ids)}",
            )
            continue

        cluster = IncidentClusterModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            organization_id=organization_id,
            cluster_name=cluster_name,
            root_cause=f"Multiple suppliers with open findings in category: {category}",
            severity="HIGH" if len(data["suppliers"]) >= 5 else "MEDIUM",
            cluster_status="ACTIVE",
            affected_supplier_ids=list(data["suppliers"]),
            finding_ids=data["findings"],
            signal_ids=[],
            risk_ids=[],
            compliance_gap_ids=[],
            calculation_inputs={"category": category, "supplier_count": len(data["suppliers"])},
        )
        session.add(cluster)
        await session.flush()
        network_counters.record_cluster_created()
        await _log_audit_event(
            session,
            "network.cluster.created",
            cluster.id,
            entity_type="incident_cluster",
            detail=f"category={category} supplier_count={len(data['suppliers'])}",
        )
        created.append(cluster)

    return created
