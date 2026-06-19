"""M32 Evidence Coverage Engine.

Computes explainable evidence coverage for a disclosure requirement.

Coverage score is a weighted sum of four independent factors:
  - Quantity  (30%): evidence count, saturates at 5 items
  - Quality   (30%): average reliability_score of linked evidence (0–1)
  - Diversity (20%): fraction of distinct evidence types present (0–1)
  - Confidence(20%): average mapping confidence of linked requirement mappings (0–1)

Score → Category:
  [0.00, 0.25) → Weak
  [0.25, 0.50) → Moderate
  [0.50, 0.75) → Strong
  [0.75, 1.00] → Complete
"""

from __future__ import annotations

from dataclasses import dataclass, field

_QUANTITY_WEIGHT = 0.30
_QUALITY_WEIGHT = 0.30
_DIVERSITY_WEIGHT = 0.20
_CONFIDENCE_WEIGHT = 0.20

_QUANTITY_SATURATION = 5  # 5+ pieces of evidence → full quantity score

_ALL_EVIDENCE_TYPES = {"Document", "Report", "Publication", "Website", "Data", "Testimony"}


@dataclass
class CoverageResult:
    score: float
    category: str
    factors: list[dict] = field(default_factory=list)


def compute_coverage(
    *,
    evidence_items: list[dict],
    mapping_confidences: list[float],
) -> CoverageResult:
    """
    evidence_items: list of evidence dicts — each must have:
      - "reliability_score": float (0–1), defaults to 0.5 if absent
      - "evidence_type": str, one of the known types
    mapping_confidences: list of confidence values (0–1) for requirement mappings
    """
    factors: list[dict] = []

    # ── Quantity ──────────────────────────────────────────────────────────────
    count = len(evidence_items)
    quantity_score = min(count / _QUANTITY_SATURATION, 1.0)
    factors.append({
        "factor": "quantity",
        "description": f"{count} evidence item(s); saturates at {_QUANTITY_SATURATION}",
        "raw": count,
        "score": round(quantity_score, 4),
        "weight": _QUANTITY_WEIGHT,
        "contribution": round(quantity_score * _QUANTITY_WEIGHT, 4),
    })

    # ── Quality ───────────────────────────────────────────────────────────────
    if evidence_items:
        quality_score = sum(
            float(e.get("reliability_score") or 0.5) for e in evidence_items
        ) / len(evidence_items)
    else:
        quality_score = 0.0
    factors.append({
        "factor": "quality",
        "description": "Average evidence reliability score",
        "raw": round(quality_score, 4),
        "score": round(quality_score, 4),
        "weight": _QUALITY_WEIGHT,
        "contribution": round(quality_score * _QUALITY_WEIGHT, 4),
    })

    # ── Diversity ─────────────────────────────────────────────────────────────
    present_types = {str(e.get("evidence_type") or "").strip() for e in evidence_items}
    present_types.discard("")
    known_present = present_types & _ALL_EVIDENCE_TYPES
    diversity_score = len(known_present) / len(_ALL_EVIDENCE_TYPES) if evidence_items else 0.0
    factors.append({
        "factor": "diversity",
        "description": f"{len(known_present)} of {len(_ALL_EVIDENCE_TYPES)} evidence types present: {sorted(known_present)}",
        "raw": len(known_present),
        "score": round(diversity_score, 4),
        "weight": _DIVERSITY_WEIGHT,
        "contribution": round(diversity_score * _DIVERSITY_WEIGHT, 4),
    })

    # ── Confidence ────────────────────────────────────────────────────────────
    if mapping_confidences:
        confidence_score = sum(mapping_confidences) / len(mapping_confidences)
    else:
        confidence_score = 0.0
    factors.append({
        "factor": "confidence",
        "description": f"Average requirement mapping confidence ({len(mapping_confidences)} mapping(s))",
        "raw": round(confidence_score, 4),
        "score": round(confidence_score, 4),
        "weight": _CONFIDENCE_WEIGHT,
        "contribution": round(confidence_score * _CONFIDENCE_WEIGHT, 4),
    })

    # ── Weighted total ────────────────────────────────────────────────────────
    total = (
        quantity_score * _QUANTITY_WEIGHT
        + quality_score * _QUALITY_WEIGHT
        + diversity_score * _DIVERSITY_WEIGHT
        + confidence_score * _CONFIDENCE_WEIGHT
    )
    total = round(min(total, 1.0), 4)
    category = _categorise(total)

    return CoverageResult(score=total, category=category, factors=factors)


def _categorise(score: float) -> str:
    if score >= 0.75:
        return "Complete"
    if score >= 0.50:
        return "Strong"
    if score >= 0.25:
        return "Moderate"
    return "Weak"
