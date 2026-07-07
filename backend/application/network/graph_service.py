"""M38 Supplier Network Graph Service.

Builds and traverses the supplier relationship graph entirely in the application
layer using PostgreSQL adjacency-list rows. No external graph database required.

Graph representation:
  - Nodes: supplier IDs (strings)
  - Edges: SupplierRelationshipModel rows (directed)

Supported operations:
  - neighbors(supplier_id) — immediate neighbors in both directions
  - bfs_neighborhood(supplier_id, max_depth) — N-hop neighborhood
  - shortest_path(src, dst) — BFS shortest path between two nodes
  - connected_component(supplier_id) — all nodes reachable from supplier
  - degree_stats(organization_id) — inbound/outbound degree per node
"""

from __future__ import annotations

from collections import deque


async def get_relationships(
    organization_id: str,
    supplier_id: str | None = None,
    relationship_type: str | None = None,
    limit: int = 200,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SupplierRelationshipModel

    stmt = select(SupplierRelationshipModel).where(
        SupplierRelationshipModel.organization_id == organization_id,
        SupplierRelationshipModel.relationship_status == "ACTIVE",
    )
    if supplier_id:
        from sqlalchemy import or_

        stmt = stmt.where(
            or_(
                SupplierRelationshipModel.supplier_id == supplier_id,
                SupplierRelationshipModel.related_supplier_id == supplier_id,
            )
        )
    if relationship_type:
        stmt = stmt.where(SupplierRelationshipModel.relationship_type == relationship_type.upper())
    stmt = stmt.order_by(SupplierRelationshipModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def _load_adjacency(organization_id: str, session) -> dict[str, list[str]]:
    """Load all ACTIVE relationships into an adjacency list (directed, both dirs)."""
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SupplierRelationshipModel

    stmt = select(
        SupplierRelationshipModel.supplier_id,
        SupplierRelationshipModel.related_supplier_id,
    ).where(
        SupplierRelationshipModel.organization_id == organization_id,
        SupplierRelationshipModel.relationship_status == "ACTIVE",
    )
    rows = (await session.execute(stmt)).all()

    adj: dict[str, list[str]] = {}
    for row in rows:
        adj.setdefault(row.supplier_id, []).append(row.related_supplier_id)
        adj.setdefault(row.related_supplier_id, []).append(row.supplier_id)
    return adj


async def bfs_neighborhood(
    organization_id: str,
    supplier_id: str,
    max_depth: int = 2,
    session=None,
) -> dict[str, int]:
    """BFS from supplier_id up to max_depth hops.

    Returns {supplier_id: distance} for all reachable nodes (excluding origin).
    """
    adj = await _load_adjacency(organization_id, session)
    visited: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque([(supplier_id, 0)])
    seen = {supplier_id}

    while queue:
        node, depth = queue.popleft()
        if depth > 0:
            visited[node] = depth
        if depth >= max_depth:
            continue
        for neighbor in adj.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, depth + 1))

    return visited


async def shortest_path(
    organization_id: str,
    src: str,
    dst: str,
    session=None,
) -> list[str] | None:
    """BFS shortest path between src and dst. Returns ordered node list or None."""
    if src == dst:
        return [src]

    adj = await _load_adjacency(organization_id, session)
    parent: dict[str, str | None] = {src: None}
    queue: deque[str] = deque([src])

    while queue:
        node = queue.popleft()
        for neighbor in adj.get(node, []):
            if neighbor not in parent:
                parent[neighbor] = node
                if neighbor == dst:
                    path = []
                    cur: str | None = dst
                    while cur is not None:
                        path.append(cur)
                        cur = parent[cur]
                    path.reverse()
                    return path
                queue.append(neighbor)

    return None


async def connected_component(
    organization_id: str,
    supplier_id: str,
    session=None,
) -> set[str]:
    """All nodes reachable from supplier_id (undirected BFS)."""
    adj = await _load_adjacency(organization_id, session)
    visited = {supplier_id}
    queue: deque[str] = deque([supplier_id])

    while queue:
        node = queue.popleft()
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited


async def compute_degree_stats(
    organization_id: str,
    session,
) -> dict[str, dict[str, int]]:
    """Compute inbound and outbound degree per supplier.

    Returns {supplier_id: {"inbound": n, "outbound": m}}.
    """
    from sqlalchemy import func, select

    from infrastructure.persistence.models.network import SupplierRelationshipModel

    out_stmt = (
        select(
            SupplierRelationshipModel.supplier_id,
            func.count().label("cnt"),
        )
        .where(
            SupplierRelationshipModel.organization_id == organization_id,
            SupplierRelationshipModel.relationship_status == "ACTIVE",
        )
        .group_by(SupplierRelationshipModel.supplier_id)
    )
    in_stmt = (
        select(
            SupplierRelationshipModel.related_supplier_id.label("supplier_id"),
            func.count().label("cnt"),
        )
        .where(
            SupplierRelationshipModel.organization_id == organization_id,
            SupplierRelationshipModel.relationship_status == "ACTIVE",
        )
        .group_by(SupplierRelationshipModel.related_supplier_id)
    )

    out_rows = (await session.execute(out_stmt)).all()
    in_rows = (await session.execute(in_stmt)).all()

    stats: dict[str, dict[str, int]] = {}
    for row in out_rows:
        stats.setdefault(row.supplier_id, {"inbound": 0, "outbound": 0})
        stats[row.supplier_id]["outbound"] = row.cnt
    for row in in_rows:
        stats.setdefault(row.supplier_id, {"inbound": 0, "outbound": 0})
        stats[row.supplier_id]["inbound"] = row.cnt

    return stats
