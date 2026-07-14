"""Tests for application/supply_chain/graph_service.py — E5-F3.

Tests verify:
  - empty graph when root has no edges
  - single-level BFS (tier 1 only)
  - two-level BFS (tier 1 → tier 2)
  - max_tier limits expansion
  - cycle prevention (visited set)
  - risk aggregation weights (tier1=1.0, tier2=0.5, tier3=0.25)
  - TierExposure counts (critical_count, high_count)
  - aggregated_risk_score zero when all nodes have score=0
  - SupplyChainGraph is immutable (frozen dataclass)
  - pure function _compute_tier_exposure
  - pure function _compute_aggregated_risk
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.supply_chain.graph_service import (
    SupplyChainGraphService,
    _compute_aggregated_risk,
    _compute_tier_exposure,
)
from domain.supply_chain_graph import (
    SupplyChainEdge,
    SupplyChainGraph,
    SupplyChainNode,
    TierExposure,
)

pytestmark = pytest.mark.unit


# ── helpers ───────────────────────────────────────────────────────────────────


def _edge_row(buyer_id: str, supplier_id: str, tier: int = 1, confidence: float = 1.0):
    row = MagicMock()
    row.buyer_id = buyer_id
    row.supplier_id = supplier_id
    row.tier = tier
    row.commodity_code = "HS-1234"
    row.confidence = confidence
    return row


def _supplier_row(sid: str, name: str):
    row = MagicMock()
    row.id = sid
    row.name = name
    return row


def _score_row(supplier_id: str, score: float, band: str):
    row = MagicMock()
    row.supplier_id = supplier_id
    row.risk_score = score
    row.risk_band = band
    return row


def _make_node(supplier_id: str, tier: int, risk_score: float = 0.0, risk_band: str = "Unknown"):
    return SupplyChainNode(
        supplier_id=supplier_id,
        name=supplier_id,
        tier=tier,
        risk_score=risk_score,
        risk_band=risk_band,
    )


def _make_session_for_graph(
    edge_map: dict[str, list],     # buyer_id → list of edge rows returned per BFS step
    supplier_rows: list | None = None,
    score_rows: list | None = None,
) -> AsyncMock:
    """Build a session mock for SupplyChainGraphService.build_graph().

    edge_map maps buyer_id to a list of edge rows.  The mock cycles through
    side_effect calls: first N calls are edge queries (one per BFS node),
    last two calls are the name/score backfill queries.
    """
    session = AsyncMock()
    call_results: list[MagicMock] = []

    # Collect all BFS buyers in order: root first, then discovered nodes
    # We build side_effect lazily by mapping each execute() call to the right rows.
    # Since AsyncMock side_effect is sequential, we pre-compute BFS order.
    # For simplicity, tests keep graphs small and provide results in expected order.

    for buyer_id, rows in edge_map.items():
        r = MagicMock()
        r.scalars.return_value.all.return_value = rows
        call_results.append(r)

    # name backfill
    r_names = MagicMock()
    r_names.all.return_value = supplier_rows or []
    call_results.append(r_names)

    # score backfill
    r_scores = MagicMock()
    r_scores.all.return_value = score_rows or []
    call_results.append(r_scores)

    session.execute = AsyncMock(side_effect=call_results)
    return session


# ── empty graph ───────────────────────────────────────────────────────────────


class TestEmptyGraph:
    @pytest.mark.asyncio
    async def test_empty_when_no_edges(self) -> None:
        session = _make_session_for_graph({"root-1": []})
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1")
        assert isinstance(graph, SupplyChainGraph)
        assert graph.nodes == {}
        assert graph.edges == ()
        assert graph.aggregated_risk_score == 0.0
        assert graph.max_tier_reached == 0

    @pytest.mark.asyncio
    async def test_root_not_in_nodes(self) -> None:
        session = _make_session_for_graph({"root-1": []})
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1")
        assert "root-1" not in graph.nodes

    @pytest.mark.asyncio
    async def test_empty_graph_is_immutable(self) -> None:
        session = _make_session_for_graph({"root-1": []})
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1")
        with pytest.raises((AttributeError, TypeError)):
            graph.max_tier_reached = 99  # type: ignore[misc]


# ── single tier ───────────────────────────────────────────────────────────────


class TestSingleTier:
    @pytest.mark.asyncio
    async def test_tier1_node_added(self) -> None:
        edges = [_edge_row("root-1", "sup-A")]
        # BFS: root → sup-A; sup-A has no edges (stops at max_tier=1 for tier 1 → no expansion)
        session = _make_session_for_graph(
            {"root-1": edges, "sup-A": []},
            supplier_rows=[_supplier_row("sup-A", "Supplier A")],
            score_rows=[],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1", max_tier=3)
        assert "sup-A" in graph.nodes
        assert graph.nodes["sup-A"].tier == 1

    @pytest.mark.asyncio
    async def test_tier1_edge_recorded(self) -> None:
        edges = [_edge_row("root-1", "sup-A")]
        session = _make_session_for_graph(
            {"root-1": edges, "sup-A": []},
            supplier_rows=[_supplier_row("sup-A", "Supplier A")],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1")
        assert len(graph.edges) == 1
        assert graph.edges[0].supplier_id == "sup-A"
        assert graph.edges[0].buyer_id == "root-1"

    @pytest.mark.asyncio
    async def test_supplier_name_backfilled(self) -> None:
        edges = [_edge_row("root-1", "sup-A")]
        session = _make_session_for_graph(
            {"root-1": edges, "sup-A": []},
            supplier_rows=[_supplier_row("sup-A", "Acme Corp")],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1")
        assert graph.nodes["sup-A"].name == "Acme Corp"

    @pytest.mark.asyncio
    async def test_risk_score_backfilled(self) -> None:
        edges = [_edge_row("root-1", "sup-A")]
        session = _make_session_for_graph(
            {"root-1": edges, "sup-A": []},
            supplier_rows=[_supplier_row("sup-A", "Acme")],
            score_rows=[_score_row("sup-A", 42.0, "Moderate")],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1")
        assert graph.nodes["sup-A"].risk_score == 42.0
        assert graph.nodes["sup-A"].risk_band == "Moderate"

    @pytest.mark.asyncio
    async def test_max_tier_reached_is_1(self) -> None:
        edges = [_edge_row("root-1", "sup-A")]
        session = _make_session_for_graph(
            {"root-1": edges, "sup-A": []},
            supplier_rows=[_supplier_row("sup-A", "A")],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1")
        assert graph.max_tier_reached == 1


# ── two-tier BFS ──────────────────────────────────────────────────────────────


class TestTwoTierBFS:
    @pytest.mark.asyncio
    async def test_tier2_node_added(self) -> None:
        tier1_edges = [_edge_row("root-1", "sup-A")]
        tier2_edges = [_edge_row("sup-A", "sup-B")]
        session = _make_session_for_graph(
            {"root-1": tier1_edges, "sup-A": tier2_edges, "sup-B": []},
            supplier_rows=[
                _supplier_row("sup-A", "Supplier A"),
                _supplier_row("sup-B", "Supplier B"),
            ],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1", max_tier=3)
        assert "sup-B" in graph.nodes
        assert graph.nodes["sup-B"].tier == 2

    @pytest.mark.asyncio
    async def test_two_edges_recorded(self) -> None:
        tier1_edges = [_edge_row("root-1", "sup-A")]
        tier2_edges = [_edge_row("sup-A", "sup-B")]
        session = _make_session_for_graph(
            {"root-1": tier1_edges, "sup-A": tier2_edges, "sup-B": []},
            supplier_rows=[
                _supplier_row("sup-A", "A"),
                _supplier_row("sup-B", "B"),
            ],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1", max_tier=3)
        assert len(graph.edges) == 2
        assert graph.max_tier_reached == 2


# ── max_tier limit ────────────────────────────────────────────────────────────


class TestMaxTierLimit:
    @pytest.mark.asyncio
    async def test_max_tier_1_stops_at_tier1(self) -> None:
        tier1_edges = [_edge_row("root-1", "sup-A")]
        # With max_tier=1, BFS pops (root-1, depth=0) and queues sup-A at depth 1.
        # Then (sup-A, depth=1) is popped but depth >= max_tier so we skip its edges.
        session = _make_session_for_graph(
            {"root-1": tier1_edges},
            supplier_rows=[_supplier_row("sup-A", "A")],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1", max_tier=1)
        assert "sup-A" in graph.nodes
        assert graph.max_tier_reached == 1


# ── cycle prevention ──────────────────────────────────────────────────────────


class TestCyclePrevention:
    @pytest.mark.asyncio
    async def test_cycle_not_duplicated(self) -> None:
        """A→B→A cycle: B tries to re-add A but A is already in visited."""
        edges_root = [_edge_row("root-1", "sup-A")]
        edges_a = [_edge_row("sup-A", "root-1")]  # points back to root
        session = _make_session_for_graph(
            {"root-1": edges_root, "sup-A": edges_a},
            supplier_rows=[_supplier_row("sup-A", "A")],
        )
        svc = SupplyChainGraphService(session)
        graph = await svc.build_graph("root-1", max_tier=3)
        # root-1 should not appear in nodes (it was never a discovered supplier)
        assert "root-1" not in graph.nodes
        # sup-A is in nodes but not duplicated
        assert list(graph.nodes.keys()).count("sup-A") == 1


# ── pure function: _compute_tier_exposure ────────────────────────────────────


class TestComputeTierExposure:
    def test_single_tier(self) -> None:
        nodes = {
            "a": _make_node("a", tier=1, risk_score=50.0, risk_band="High"),
            "b": _make_node("b", tier=1, risk_score=100.0, risk_band="Critical"),
        }
        exposure = _compute_tier_exposure(nodes)
        assert 1 in exposure
        te = exposure[1]
        assert te.supplier_count == 2
        assert te.avg_risk_score == 75.0
        assert te.max_risk_score == 100.0
        assert te.critical_count == 1
        assert te.high_count == 1

    def test_two_tiers(self) -> None:
        nodes = {
            "a": _make_node("a", tier=1, risk_score=40.0, risk_band="Moderate"),
            "b": _make_node("b", tier=2, risk_score=80.0, risk_band="High"),
        }
        exposure = _compute_tier_exposure(nodes)
        assert set(exposure.keys()) == {1, 2}
        assert exposure[1].supplier_count == 1
        assert exposure[2].supplier_count == 1

    def test_empty_nodes(self) -> None:
        exposure = _compute_tier_exposure({})
        assert exposure == {}

    def test_tier_exposure_is_frozen(self) -> None:
        nodes = {"a": _make_node("a", tier=1, risk_score=10.0)}
        exposure = _compute_tier_exposure(nodes)
        with pytest.raises((AttributeError, TypeError)):
            exposure[1].supplier_count = 99  # type: ignore[misc]


# ── pure function: _compute_aggregated_risk ───────────────────────────────────


class TestComputeAggregatedRisk:
    def test_zero_when_no_nodes(self) -> None:
        assert _compute_aggregated_risk({}) == 0.0

    def test_zero_when_all_scores_zero(self) -> None:
        nodes = {
            "a": _make_node("a", tier=1, risk_score=0.0),
            "b": _make_node("b", tier=2, risk_score=0.0),
        }
        assert _compute_aggregated_risk(nodes) == 0.0

    def test_tier1_weight_full(self) -> None:
        """Single tier-1 node with score=60 → aggregated = 60."""
        nodes = {"a": _make_node("a", tier=1, risk_score=60.0)}
        result = _compute_aggregated_risk(nodes)
        assert result == 60.0

    def test_tier2_half_weight(self) -> None:
        """tier1=60 (w=1.0) + tier2=60 (w=0.5) → (60+30)/(1.0+0.5) = 60."""
        nodes = {
            "a": _make_node("a", tier=1, risk_score=60.0),
            "b": _make_node("b", tier=2, risk_score=60.0),
        }
        result = _compute_aggregated_risk(nodes)
        assert abs(result - 60.0) < 0.01

    def test_high_tier2_increases_aggregate(self) -> None:
        """tier1=20 (w=1.0) + tier2=100 (w=0.5) → (20+50)/(1.0+0.5) ≈ 46.67"""
        nodes = {
            "a": _make_node("a", tier=1, risk_score=20.0),
            "b": _make_node("b", tier=2, risk_score=100.0),
        }
        result = _compute_aggregated_risk(nodes)
        assert abs(result - (70 / 1.5)) < 0.01

    def test_tier3_quarter_weight(self) -> None:
        """Only tier-3 node with score=80 → weight=0.25 → aggregate=80."""
        nodes = {"a": _make_node("a", tier=3, risk_score=80.0)}
        result = _compute_aggregated_risk(nodes)
        assert result == 80.0
