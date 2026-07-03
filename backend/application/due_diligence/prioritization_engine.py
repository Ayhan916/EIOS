"""CSDDD Art. 10 Prioritisation Engine (GAP-18).

Deterministic, auditable, reproducible — no LLM calls, no randomness.

Priority Score formula (weights from CSDDD Art. 10 + LkSG §5):
  score = severity * 0.40 + probability * 0.35 + people_affected * 0.25

All inputs are scaled to 0–4 so the maximum possible score is 4.0.

Reference: CSDDD Art. 10 — "companies shall prioritise adverse impacts
on the basis of their severity and probability".
"""

from __future__ import annotations

_SEVERITY_MAP: dict[str, float] = {
    "Critical": 4.0,
    "High": 3.0,
    "Moderate": 2.0,
    "Medium": 2.0,
    "Low": 1.0,
}

_TIER_FACTOR: dict[str, float] = {
    "Tier 1": 1.0,
    "Tier 2": 0.85,
    "Tier 3": 0.70,
}

# Weights per CSDDD Art. 10 ordering of criteria
_W_SEVERITY = 0.40
_W_PROBABILITY = 0.35
_W_PEOPLE = 0.25


def _severity_weight(risk_band: str) -> float:
    return _SEVERITY_MAP.get(risk_band, 1.0)


def _probability_weight(risk_score: float) -> float:
    """Scale risk_score (0–100) to 0–4."""
    return min(risk_score / 25.0, 4.0)


def _people_affected_weight(finding_count: int) -> float:
    """Scale finding count to 0–4 (logarithmic ceiling)."""
    if finding_count == 0:
        return 0.0
    if finding_count <= 2:
        return 1.0
    if finding_count <= 5:
        return 2.0
    if finding_count <= 10:
        return 3.0
    return 4.0


def _tier_factor(supplier_tier: str) -> float:
    return _TIER_FACTOR.get(supplier_tier, 1.0)


def _build_reasoning(
    supplier_name: str,
    risk_band: str,
    risk_score: float,
    finding_count: int,
    supplier_tier: str,
    score: float,
    rank: int,
) -> str:
    return (
        f"Supplier '{supplier_name}' ranked #{rank} (score {score:.2f}/4.00). "
        f"Severity: {risk_band} (weight {_severity_weight(risk_band):.1f}), "
        f"Probability: risk_score={risk_score:.1f} (weight {_probability_weight(risk_score):.2f}), "
        f"Scale: {finding_count} finding(s) (weight {_people_affected_weight(finding_count):.1f}). "
        f"Supplier tier: {supplier_tier} (factor {_tier_factor(supplier_tier):.2f}). "
        f"Regulation: CSDDD Art. 10; LkSG §5."
    )


def compute_prioritization(
    *,
    organization_id: str,
    suppliers: list[dict],
    supplier_scores: dict[str, dict],
    finding_counts: dict[str, int],
    resource_capacity_per_quarter: int = 4,
    decided_by_user_id: str = "",
) -> list[dict]:
    """Compute a deterministic, ranked list of prioritisation decisions.

    Args:
        suppliers: list of supplier dicts with keys id, name, supplier_tier.
        supplier_scores: {supplier_id: {risk_band, risk_score}} from SupplierScoreModel.
        finding_counts: {supplier_id: int} — open findings per supplier.
        resource_capacity_per_quarter: audit slots available per quarter.
        decided_by_user_id: user who triggered the computation.

    Returns:
        List of dicts, each representing one PrioritizationDecision row, sorted by
        priority_rank ascending (rank 1 = most urgent).
    """
    scored: list[dict] = []

    for s in suppliers:
        sid = s.get("id", "")
        name = s.get("name", "") or s.get("supplier_name", "")
        tier = s.get("supplier_tier", "Tier 1")

        sc = supplier_scores.get(sid) or {}
        risk_band = sc.get("risk_band", "Low")
        risk_score = float(sc.get("risk_score", 0.0))
        fc = finding_counts.get(sid, 0)

        sev = _severity_weight(risk_band)
        prob = _probability_weight(risk_score)
        ppl = _people_affected_weight(fc)
        tf = _tier_factor(tier)

        raw_score = sev * _W_SEVERITY + prob * _W_PROBABILITY + ppl * _W_PEOPLE
        score = round(raw_score * tf, 4)

        scored.append(
            {
                "organization_id": organization_id,
                "supplier_id": sid,
                "supplier_name": name,
                "severity_weight": sev,
                "probability_weight": round(prob, 4),
                "people_affected_weight": ppl,
                "priority_score": score,
                "resource_capacity_per_quarter": resource_capacity_per_quarter,
                "decided_by_user_id": decided_by_user_id,
                "regulation_refs": "CSDDD Art. 10; LkSG §5",
                "_risk_band": risk_band,
                "_risk_score": risk_score,
                "_finding_count": fc,
                "_tier": tier,
            }
        )

    # Sort descending by score; ties broken by supplier_id for determinism
    scored.sort(key=lambda x: (-x["priority_score"], x["supplier_id"]))

    results: list[dict] = []
    for rank, item in enumerate(scored, start=1):
        item["priority_rank"] = rank
        item["reasoning"] = _build_reasoning(
            supplier_name=item["supplier_name"],
            risk_band=item["_risk_band"],
            risk_score=item["_risk_score"],
            finding_count=item["_finding_count"],
            supplier_tier=item["_tier"],
            score=item["priority_score"],
            rank=rank,
        )
        # Remove internal scratch keys
        del item["_risk_band"], item["_risk_score"], item["_finding_count"], item["_tier"]
        results.append(item)

    return results
