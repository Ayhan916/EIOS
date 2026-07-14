"""Supply Chain Graph domain value objects (E5-F3).

SupplyChainEdge  — one directed relationship: buyer → supplier at a given tier.
SupplyChainNode  — one supplier in the graph with its risk score snapshot.
SupplyChainGraph — the full BFS-expanded graph for a root supplier.

All objects are immutable. The graph is assembled by SupplyChainGraphService
and can be passed freely without mutation risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SupplyChainEdge:
    """A directed supply chain relationship.

    Attributes:
        buyer_id:       Supplier that buys from `supplier_id`.
        supplier_id:    The upstream supplier providing goods/services.
        tier:           Network depth from root (1 = direct, 2 = indirect, ...).
        commodity_code: HS/NACE code identifying what is being supplied.
        confidence:     0.0–1.0 — reliability of this edge (e.g. verified vs. inferred).
    """

    buyer_id: str
    supplier_id: str
    tier: int
    commodity_code: str
    confidence: float


@dataclass(frozen=True)
class SupplyChainNode:
    """One supplier node in the graph with its latest risk snapshot.

    Attributes:
        supplier_id:  Unique identifier.
        name:         Display name.
        tier:         Shortest path distance from the root supplier.
        risk_score:   Latest composite risk score (0–100), 0 if unknown.
        risk_band:    "Low" | "Moderate" | "High" | "Critical" | "Unknown".
    """

    supplier_id: str
    name: str
    tier: int
    risk_score: float
    risk_band: str


@dataclass(frozen=True)
class TierExposure:
    """Aggregated risk exposure for one tier level.

    Attributes:
        tier:                 Tier number (1, 2, 3 ...).
        supplier_count:       Number of suppliers at this tier.
        avg_risk_score:       Weighted average risk score across this tier.
        max_risk_score:       Highest individual risk score at this tier.
        critical_count:       Suppliers with band "Critical".
        high_count:           Suppliers with band "High".
    """

    tier: int
    supplier_count: int
    avg_risk_score: float
    max_risk_score: float
    critical_count: int
    high_count: int


@dataclass(frozen=True)
class SupplyChainGraph:
    """Full supply chain graph rooted at one supplier.

    Attributes:
        root_supplier_id:     The root supplier (the organisation's direct partner).
        nodes:                All discovered suppliers keyed by supplier_id.
        edges:                All directed edges in the graph.
        tier_exposure:        Per-tier risk aggregation, keyed by tier number.
        aggregated_risk_score: Weighted composite across all tiers
                               (tier 1 weight=1.0, tier 2=0.5, tier 3=0.25).
        max_tier_reached:     Deepest tier expanded in this traversal.
    """

    root_supplier_id: str
    nodes: dict[str, SupplyChainNode]
    edges: tuple[SupplyChainEdge, ...]
    tier_exposure: dict[int, TierExposure]
    aggregated_risk_score: float
    max_tier_reached: int
