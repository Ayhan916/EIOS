"""Domain model — Impact Severity Assessment (CSDDD Art. 3/6, OECD RBC Guidelines).

Severity is determined by three OECD dimensions (each 1–5):
  gravity       — seriousness of harm (1 = minor, 5 = catastrophic)
  scope         — breadth: number of people / geographic extent
  remediability — how hard to reverse the impact (1 = fully reversible, 5 = irremediable)

severity_score = (gravity * 0.40 + scope * 0.30 + remediability * 0.30 − 1) / 4 * 10
                 → 0.0 – 10.0 scale

Likelihood (1–5) is tracked separately but feeds the priority_score:
  priority_score = severity_score * (likelihood / 5)

Severity levels:
  CRITICAL  ≥ 8.0
  HIGH      ≥ 6.0
  MEDIUM    ≥ 3.0
  LOW       < 3.0
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ImpactAssessment:
    id: str
    organization_id: str
    title: str
    impact_type: str            # ImpactType
    entity_type: str            # ImpactEntityType
    entity_id: str | None       # UUID of linked finding/risk/supplier
    gravity: int                # 1–5
    scope: int                  # 1–5
    remediability: int          # 1–5
    likelihood: int             # 1–5
    severity_score: float       # computed, 0–10
    priority_score: float       # severity × (likelihood/5)
    severity_level: str         # SeverityLevel
    justification: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
