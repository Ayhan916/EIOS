"""M38 Network Centrality — Degree Centrality and Connected Component Metrics.

Computes and persists SupplierCriticality records with:
  - inbound_degree
  - outbound_degree
  - degree_centrality = (inbound + outbound) / (2 * (n-1)) where n = node count
  - connected_component_size — nodes reachable via BFS
"""

from __future__ import annotations

import uuid
from collections import deque
from datetime import UTC, datetime

import structlog

from application.network.graph_service import compute_degree_stats

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
            entity_type="supplier_criticality",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("network_centrality_audit_failed", action=action, error=str(exc))


async def compute_centrality(
    organization_id: str,
    session,
) -> list[dict]:
    """Compute degree centrality for all suppliers with at least one relationship.

    P2 M38.1: loads adjacency ONCE and computes all connected components in a
    single in-memory BFS pass. Total DB queries: 3 (out-degree, in-degree, adjacency).

    Returns list of dicts with supplier_id, inbound, outbound, degree_centrality,
    connected_component_size.
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SupplierRelationshipModel

    degree_stats = await compute_degree_stats(organization_id, session)
    if not degree_stats:
        return []

    # P2 M38.1: load adjacency once (1 query) rather than once per node
    adj_stmt = select(
        SupplierRelationshipModel.supplier_id,
        SupplierRelationshipModel.related_supplier_id,
    ).where(
        SupplierRelationshipModel.organization_id == organization_id,
        SupplierRelationshipModel.relationship_status == "ACTIVE",
    )
    adj_rows = (await session.execute(adj_stmt)).all()

    adj: dict[str, list[str]] = {}
    for row in adj_rows:
        adj.setdefault(row.supplier_id, []).append(row.related_supplier_id)
        adj.setdefault(row.related_supplier_id, []).append(row.supplier_id)

    # Single-pass BFS over all nodes to compute component sizes
    component_size_by_supplier: dict[str, int] = {}
    unvisited = set(adj.keys())

    while unvisited:
        start = next(iter(unvisited))
        component: set[str] = set()
        q: deque[str] = deque([start])
        component.add(start)

        while q:
            node = q.popleft()
            for neighbor in adj.get(node, []):
                if neighbor not in component:
                    component.add(neighbor)
                    q.append(neighbor)

        size = len(component)
        for node in component:
            component_size_by_supplier[node] = size
        unvisited -= component

    n = len(degree_stats)
    max_degree = max(1, 2 * (n - 1)) if n > 1 else 1

    results = []
    for supplier_id, stats in degree_stats.items():
        inbound = stats["inbound"]
        outbound = stats["outbound"]
        degree_centrality = (inbound + outbound) / max_degree
        component_size = component_size_by_supplier.get(supplier_id, 1)

        results.append(
            {
                "supplier_id": supplier_id,
                "inbound_degree": inbound,
                "outbound_degree": outbound,
                "degree_centrality": round(min(degree_centrality, 1.0), 4),
                "connected_component_size": component_size,
            }
        )

    results.sort(key=lambda x: x["degree_centrality"], reverse=True)

    await _log_audit_event(
        session,
        "network.criticality.refreshed",
        organization_id,
        detail=f"supplier_count={len(results)}",
    )
    return results


async def upsert_criticality(
    organization_id: str,
    supplier_id: str,
    centrality_data: dict,
    dependency_score: float,
    assessment_count: int,
    finding_count: int,
    open_remediation_count: int,
    session,
) -> object:
    """Compute and persist SupplierCriticality for one supplier.

    Criticality score (weighted sum, all inputs 0–1):
      0.25 × degree_centrality
      0.25 × dependency_score
      0.20 × finding_severity_factor
      0.20 × assessment_risk_factor
      0.10 × remediation_factor
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SupplierCriticalityModel

    degree_centrality = centrality_data.get("degree_centrality", 0.0)
    inbound = centrality_data.get("inbound_degree", 0)
    outbound = centrality_data.get("outbound_degree", 0)
    component_size = centrality_data.get("connected_component_size", 1)

    finding_factor = min(finding_count / 10.0, 1.0)
    assessment_factor = min(assessment_count / 5.0, 1.0)
    remediation_factor = min(open_remediation_count / 5.0, 1.0)

    score = (
        0.25 * degree_centrality
        + 0.25 * min(dependency_score, 1.0)
        + 0.20 * finding_factor
        + 0.20 * assessment_factor
        + 0.10 * remediation_factor
    )
    score = round(min(score, 1.0), 4)

    if score < 0.25:
        criticality = "LOW"
    elif score < 0.50:
        criticality = "MEDIUM"
    elif score < 0.75:
        criticality = "HIGH"
    else:
        criticality = "CRITICAL"

    now = datetime.now(UTC)
    inputs = {
        "degree_centrality": degree_centrality,
        "dependency_score": dependency_score,
        "finding_factor": finding_factor,
        "assessment_factor": assessment_factor,
        "remediation_factor": remediation_factor,
        "weights": {
            "centrality": 0.25,
            "dependency": 0.25,
            "finding": 0.20,
            "assessment": 0.20,
            "remediation": 0.10,
        },
    }

    stmt = select(SupplierCriticalityModel).where(
        SupplierCriticalityModel.organization_id == organization_id,
        SupplierCriticalityModel.supplier_id == supplier_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.criticality = criticality
        existing.criticality_score = score
        existing.degree_centrality = degree_centrality
        existing.inbound_degree = inbound
        existing.outbound_degree = outbound
        existing.connected_component_size = component_size
        existing.dependency_score = dependency_score
        existing.assessment_count = assessment_count
        existing.finding_count = finding_count
        existing.open_remediation_count = open_remediation_count
        existing.calculation_inputs = inputs
        existing.calculated_at = now
        existing.updated_at = now
        await session.flush()
        return existing

    record = SupplierCriticalityModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        supplier_id=supplier_id,
        criticality=criticality,
        criticality_score=score,
        degree_centrality=degree_centrality,
        inbound_degree=inbound,
        outbound_degree=outbound,
        connected_component_size=component_size,
        dependency_score=dependency_score,
        assessment_count=assessment_count,
        finding_count=finding_count,
        open_remediation_count=open_remediation_count,
        calculation_inputs=inputs,
        calculated_at=now,
    )
    session.add(record)
    await session.flush()
    return record


async def get_criticality(
    organization_id: str,
    supplier_id: str,
    session,
) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SupplierCriticalityModel

    stmt = select(SupplierCriticalityModel).where(
        SupplierCriticalityModel.organization_id == organization_id,
        SupplierCriticalityModel.supplier_id == supplier_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_criticality(
    organization_id: str,
    criticality_level: str | None = None,
    limit: int = 100,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SupplierCriticalityModel

    stmt = select(SupplierCriticalityModel).where(
        SupplierCriticalityModel.organization_id == organization_id
    )
    if criticality_level:
        stmt = stmt.where(SupplierCriticalityModel.criticality == criticality_level.upper())
    stmt = stmt.order_by(SupplierCriticalityModel.criticality_score.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
