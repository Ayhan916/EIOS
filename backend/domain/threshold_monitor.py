"""Domain model — CSDDD Threshold Monitor (CSDDD-010, Art. 2).

Art. 2 CSDDD defines tiered thresholds:
  Tier 1 (from 26 Jul 2027): ≥5,000 employees AND ≥€1.5B net revenue worldwide
  Tier 2 (from 26 Jul 2028): ≥1,000 employees AND ≥€450M net revenue worldwide
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CompanyProfile:
    """Company financial/workforce profile for a fiscal year."""
    id: str
    organization_id: str
    fiscal_year: int
    employee_count_worldwide: int
    net_revenue_eur_millions: float    # in millions EUR
    headquarters_country: str          # ISO-3166-1 alpha-2
    sector: str
    non_eu_company: bool
    notes: str
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ThresholdStatus:
    """Result of deterministic threshold calculation."""
    organization_id: str
    fiscal_year: int
    level: str                         # CSDDDThresholdLevel
    employee_count: int
    net_revenue_eur_millions: float
    # Tier 1
    tier1_employee_met: bool
    tier1_revenue_met: bool
    tier1_deadline: str                # "2027-07-26"
    # Tier 2
    tier2_employee_met: bool
    tier2_revenue_met: bool
    tier2_deadline: str                # "2028-07-26"
    # Borderline
    is_borderline: bool
    borderline_message: str
    # Next action
    recommendation: str
