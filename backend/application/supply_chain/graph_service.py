"""Supply chain graph traversal and risk aggregation — E5-F3.

SupplyChainGraphService.build_graph():
  - BFS from root_supplier_id through SupplyChainEdgeModel rows
  - Stops at max_tier (default 3)
  - Attaches latest risk snapshot from SupplierScoreModel when available

SupplyChainGraphService.aggregate_risk():
  - Tier weights: tier 1=1.0, tier 2=0.5, tier 3=0.25
  - Returns per-tier TierExposure and one composite aggregated_risk_score

No LLM calls — purely deterministic graph logic (ADR-010 spirit).
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from sqlalchemy import select

from domain.supply_chain_graph import (
    SupplyChainEdge,
    SupplyChainGraph,
    SupplyChainNode,
    TierExposure,
)
from infrastructure.persistence.models.supply_chain_edge import SupplyChainEdgeModel
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Tier weight for risk aggregation — drops by half per tier
_TIER_WEIGHTS: dict[int, float] = {1: 1.0, 2: 0.5, 3: 0.25}
_DEFAULT_TIER_WEIGHT = 0.1  # fallback for tiers beyond 3


class SupplyChainGraphService:
    """Build and analyse the supply chain graph for a given root supplier."""

    def __init__(self, session: "AsyncSession") -> None:
        self._session = session

    # ── public API ─────────────────────────────────────────────────────────────

    async def build_graph(
        self,
        root_supplier_id: str,
        max_tier: int = 3,
    ) -> SupplyChainGraph:
        """BFS-expand the supply chain from root_supplier_id up to max_tier.

        The root supplier itself is not added as a node — only its downstream
        suppliers (tier 1, 2, 3 …) appear as nodes.

        Returns a fully assembled, immutable SupplyChainGraph.
        """
        visited: set[str] = {root_supplier_id}
        queue: deque[tuple[str, int]] = deque([(root_supplier_id, 0)])

        nodes: dict[str, SupplyChainNode] = {}
        edges: list[SupplyChainEdge] = []

        while queue:
            buyer_id, current_depth = queue.popleft()
            if current_depth >= max_tier:
                continue

            next_tier = current_depth + 1
            edge_rows = (
                await self._session.execute(
                    select(SupplyChainEdgeModel).where(
                        SupplyChainEdgeModel.buyer_id == buyer_id
                    )
                )
            ).scalars().all()

            for row in edge_rows:
                edges.append(
                    SupplyChainEdge(
                        buyer_id=row.buyer_id,
                        supplier_id=row.supplier_id,
                        tier=next_tier,
                        commodity_code=row.commodity_code or "",
                        confidence=row.confidence,
                    )
                )
                if row.supplier_id not in visited:
                    visited.add(row.supplier_id)
                    queue.append((row.supplier_id, next_tier))
                    # Will be backfilled with risk snapshot below
                    nodes[row.supplier_id] = SupplyChainNode(
                        supplier_id=row.supplier_id,
                        name=row.supplier_id,  # placeholder — resolved below
                        tier=next_tier,
                        risk_score=0.0,
                        risk_band="Unknown",
                    )

        if nodes:
            nodes = await self._backfill_names_and_scores(nodes)

        max_tier_reached = max((n.tier for n in nodes.values()), default=0)
        tier_exposure = _compute_tier_exposure(nodes)
        aggregated = _compute_aggregated_risk(nodes)

        return SupplyChainGraph(
            root_supplier_id=root_supplier_id,
            nodes=nodes,
            edges=tuple(edges),
            tier_exposure=tier_exposure,
            aggregated_risk_score=round(aggregated, 2),
            max_tier_reached=max_tier_reached,
        )

    # ── private helpers ────────────────────────────────────────────────────────

    async def _backfill_names_and_scores(
        self,
        nodes: dict[str, SupplyChainNode],
    ) -> dict[str, SupplyChainNode]:
        """Replace placeholder nodes with real names and latest risk scores."""
        supplier_ids = list(nodes.keys())

        # Supplier names
        name_rows = (
            await self._session.execute(
                select(SupplierModel.id, SupplierModel.name).where(
                    SupplierModel.id.in_(supplier_ids)
                )
            )
        ).all()
        name_map: dict[str, str] = {row.id: row.name for row in name_rows}

        # Latest risk scores (subquery: max created_at per supplier)
        score_rows = (
            await self._session.execute(
                select(
                    SupplierScoreModel.supplier_id,
                    SupplierScoreModel.risk_score,
                    SupplierScoreModel.risk_band,
                )
                .where(SupplierScoreModel.supplier_id.in_(supplier_ids))
                .order_by(
                    SupplierScoreModel.supplier_id,
                    SupplierScoreModel.created_at.desc(),
                )
                .distinct(SupplierScoreModel.supplier_id)
            )
        ).all()
        score_map: dict[str, tuple[float, str]] = {
            row.supplier_id: (row.risk_score, row.risk_band) for row in score_rows
        }

        updated: dict[str, SupplyChainNode] = {}
        for sid, node in nodes.items():
            risk_score, risk_band = score_map.get(sid, (0.0, "Unknown"))
            updated[sid] = SupplyChainNode(
                supplier_id=sid,
                name=name_map.get(sid, sid),
                tier=node.tier,
                risk_score=float(risk_score),
                risk_band=risk_band,
            )
        return updated


# ── pure functions (no I/O) ────────────────────────────────────────────────────


def _compute_tier_exposure(nodes: dict[str, SupplyChainNode]) -> dict[int, TierExposure]:
    """Aggregate risk stats per tier level."""
    buckets: dict[int, list[SupplyChainNode]] = {}
    for node in nodes.values():
        buckets.setdefault(node.tier, []).append(node)

    exposure: dict[int, TierExposure] = {}
    for tier, tier_nodes in sorted(buckets.items()):
        scores = [n.risk_score for n in tier_nodes]
        bands = [n.risk_band for n in tier_nodes]
        avg = sum(scores) / len(scores) if scores else 0.0
        exposure[tier] = TierExposure(
            tier=tier,
            supplier_count=len(tier_nodes),
            avg_risk_score=round(avg, 2),
            max_risk_score=round(max(scores, default=0.0), 2),
            critical_count=sum(1 for b in bands if b == "Critical"),
            high_count=sum(1 for b in bands if b == "High"),
        )
    return exposure


def _compute_aggregated_risk(nodes: dict[str, SupplyChainNode]) -> float:
    """Weighted-average risk score across all tiers.

    tier 1 weight = 1.0, tier 2 = 0.5, tier 3 = 0.25, deeper = 0.1
    """
    if not nodes:
        return 0.0

    total_weighted = 0.0
    total_weight = 0.0
    for node in nodes.values():
        w = _TIER_WEIGHTS.get(node.tier, _DEFAULT_TIER_WEIGHT)
        total_weighted += node.risk_score * w
        total_weight += w

    return total_weighted / total_weight if total_weight > 0 else 0.0
