"""CSDDD-005 — Downstream Activity Chain API (Art. 2/3).

Endpoints (authenticated):
  GET  /activity-chain/visualization-data   graph nodes+edges for full chain view
  GET  /activity-chain/stats                upstream/downstream stats summary

Security:
  - organization_id MANDATORY on all queries
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from domain.user import User
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel
from interfaces.api.deps import get_current_user, get_sync_db

router = APIRouter(prefix="/activity-chain", tags=["activity-chain"])

_RISK_COLOR = {
    "Critical": "#ef4444",
    "High": "#f97316",
    "Medium": "#eab308",
    "Low": "#22c55e",
    "Unknown": "#94a3b8",
}


@router.get("/visualization-data")
def get_visualization_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    """Return graph nodes + edges for the full upstream/downstream chain visualization."""
    org_id = str(user.organization_id)

    suppliers = (
        db.query(SupplierModel)
        .filter(
            SupplierModel.organization_id == org_id,
            SupplierModel.supplier_status.notin_(["Inactive", "Archived", "Deleted"]),
        )
        .all()
    )

    # Build score lookup (latest score per supplier)
    supplier_ids = [s.id for s in suppliers]
    scores: dict[str, Any] = {}
    if supplier_ids:
        for sup_id in supplier_ids:
            score_row = (
                db.query(SupplierScoreModel)
                .filter(SupplierScoreModel.supplier_id == sup_id)
                .order_by(SupplierScoreModel.created_at.desc())
                .first()
            )
            if score_row:
                scores[str(sup_id)] = {
                    "risk_score": score_row.risk_score,
                    "risk_band": score_row.risk_band,
                }

    nodes = []
    edges = []

    # Center node = the company itself
    nodes.append(
        {
            "id": "company",
            "type": "company",
            "label": "Mein Unternehmen",
            "chain_direction": "both",
            "tier": 0,
            "risk_score": None,
            "risk_band": None,
            "color": "#3b82f6",
        }
    )

    for s in suppliers:
        sid = str(s.id)
        score_data = scores.get(sid, {})
        risk_band = score_data.get("risk_band", "Unknown")
        color = _RISK_COLOR.get(risk_band, _RISK_COLOR["Unknown"])

        direction = getattr(s, "chain_direction", "upstream") or "upstream"
        tier_label = getattr(s, "supplier_tier", "Tier 1") or "Tier 1"
        try:
            tier_num = int(tier_label.replace("Tier", "").strip())
        except (ValueError, AttributeError):
            tier_num = 1

        nodes.append(
            {
                "id": sid,
                "type": direction,
                "label": s.name,
                "chain_direction": direction,
                "downstream_type": getattr(s, "downstream_type", None),
                "tier": tier_num,
                "country": s.country,
                "industry": s.industry,
                "risk_score": score_data.get("risk_score"),
                "risk_band": risk_band,
                "color": color,
            }
        )

        # Edge from company to tier-1, else from tier (N-1) placeholder to tier N
        edges.append(
            {
                "id": f"e-{sid}",
                "source": "company",
                "target": sid,
                "direction": direction,
            }
        )

    upstream = [n for n in nodes if n["chain_direction"] == "upstream"]
    downstream = [n for n in nodes if n["chain_direction"] == "downstream"]
    both = [n for n in nodes if n["chain_direction"] == "both" and n["id"] != "company"]

    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total": len(suppliers),
            "upstream": len(upstream),
            "downstream": len(downstream),
            "both": len(both),
            "high_risk": sum(1 for n in nodes[1:] if n.get("risk_band") in ("Critical", "High")),
        },
    }


@router.get("/stats")
def get_chain_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    org_id = str(user.organization_id)
    all_suppliers = (
        db.query(SupplierModel)
        .filter(
            SupplierModel.organization_id == org_id,
            SupplierModel.supplier_status.notin_(["Inactive", "Archived", "Deleted"]),
        )
        .all()
    )

    upstream = [
        s
        for s in all_suppliers
        if (getattr(s, "chain_direction", "upstream") or "upstream") == "upstream"
    ]
    downstream = [
        s
        for s in all_suppliers
        if (getattr(s, "chain_direction", "upstream") or "upstream") == "downstream"
    ]
    both = [
        s
        for s in all_suppliers
        if (getattr(s, "chain_direction", "upstream") or "upstream") == "both"
    ]

    # Downstream type breakdown
    type_breakdown: dict[str, int] = {}
    for s in downstream + both:
        dt = getattr(s, "downstream_type", None) or "other"
        type_breakdown[dt] = type_breakdown.get(dt, 0) + 1

    return {
        "total": len(all_suppliers),
        "upstream_count": len(upstream),
        "downstream_count": len(downstream),
        "both_count": len(both),
        "downstream_coverage_pct": round(len(downstream) / len(all_suppliers) * 100, 1)
        if all_suppliers
        else 0.0,
        "downstream_type_breakdown": type_breakdown,
    }
