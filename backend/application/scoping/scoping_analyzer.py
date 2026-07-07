"""Deterministic scoping analyzer for CSDDD Art. 8 Abs. 3.

Pure function — no database writes, no LLM, fully auditable.

Inputs:
  - ScopingConfig (thresholds, high-risk countries/sectors)
  - List of (supplier_id, supplier_name, country, industry, risk_score, risk_band)

Outputs:
  - List of ScopingResult (one per supplier, with priority + reasons)

Priority logic (deterministic, in order of precedence):
  P1: risk_score >= config.risk_score_threshold_p1
      OR country in config.high_risk_countries
      OR industry in config.high_risk_sectors
  P2: risk_score >= config.risk_score_threshold_p2 (but < P1 threshold)
  P3: everything else
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.enums import ScopingPriority
from domain.scoping import ScopingConfig, ScopingResult


@dataclass
class SupplierInput:
    supplier_id: str
    supplier_name: str
    country: str
    industry: str
    risk_score: float
    risk_band: str


def analyze(config: ScopingConfig, suppliers: list[SupplierInput]) -> list[ScopingResult]:
    """Run deterministic scoping analysis. Returns one ScopingResult per supplier."""
    results = []
    high_risk_countries_lower = {c.lower().strip() for c in config.high_risk_countries}
    {s.lower().strip() for s in config.high_risk_sectors}

    for s in suppliers:
        reasons: list[str] = []
        country_lower = s.country.lower().strip()
        industry_lower = s.industry.lower().strip()

        # Check P1 triggers
        p1_triggers = False

        if s.risk_score >= config.risk_score_threshold_p1:
            reasons.append(
                f"Risikoscore {s.risk_score:.1f} ≥ P1-Schwellenwert {config.risk_score_threshold_p1:.1f}"
            )
            p1_triggers = True

        if country_lower in high_risk_countries_lower:
            reasons.append(f"Hochrisikoland: {s.country}")
            p1_triggers = True

        # sector match: check if any high-risk sector is contained in the supplier's industry string
        matched_sectors = [
            sec for sec in config.high_risk_sectors if sec.lower().strip() in industry_lower
        ]
        if matched_sectors:
            reasons.append(f"Hochrisikobranche: {', '.join(matched_sectors)}")
            p1_triggers = True

        if p1_triggers:
            priority = ScopingPriority.PRIORITY_1
            if not reasons:
                reasons.append("Mindestens ein P1-Kriterium erfüllt")
        elif s.risk_score >= config.risk_score_threshold_p2:
            priority = ScopingPriority.PRIORITY_2
            reasons.append(
                f"Risikoscore {s.risk_score:.1f} ≥ P2-Schwellenwert {config.risk_score_threshold_p2:.1f}"
            )
        else:
            priority = ScopingPriority.PRIORITY_3
            reasons.append(
                f"Risikoscore {s.risk_score:.1f} unterhalb aller Schwellenwerte — vereinfachte DD"
            )

        results.append(
            ScopingResult(
                supplier_id=s.supplier_id,
                supplier_name=s.supplier_name,
                country=s.country,
                industry=s.industry,
                risk_score=s.risk_score,
                risk_band=s.risk_band,
                priority=priority,
                reasons=reasons,
                manually_overridden=False,
                override_reason=None,
            )
        )

    # Sort: P1 first, then P2, then P3, then by score desc within each tier
    _order = {
        ScopingPriority.PRIORITY_1: 0,
        ScopingPriority.PRIORITY_2: 1,
        ScopingPriority.PRIORITY_3: 2,
    }
    results.sort(key=lambda r: (_order[r.priority], -r.risk_score))
    return results
