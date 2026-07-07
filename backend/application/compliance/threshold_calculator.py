"""CSDDD Threshold Calculator — CSDDD-010 (Art. 2).

Pure deterministic function — no LLM, no randomness.
Art. 2 CSDDD thresholds (EU 2024/1760):
  Tier 1 (from 26 Jul 2027): ≥5,000 employees AND ≥€1,500M net revenue worldwide
  Tier 2 (from 26 Jul 2028): ≥1,000 employees AND ≥€450M net revenue worldwide

Borderline: <20% below a threshold on EITHER dimension.
"""

from __future__ import annotations

from domain.enums import CSDDDThresholdLevel
from domain.threshold_monitor import CompanyProfile, ThresholdStatus

_TIER1_EMPLOYEES = 5_000
_TIER1_REVENUE_M = 1_500.0
_TIER1_DEADLINE = "2027-07-26"

_TIER2_EMPLOYEES = 1_000
_TIER2_REVENUE_M = 450.0
_TIER2_DEADLINE = "2028-07-26"

_BORDERLINE_PCT = 0.20  # within 20% below threshold = borderline


def _near(value: float, threshold: float) -> bool:
    """True if value is within BORDERLINE_PCT below threshold (but not yet there)."""
    return value < threshold and value >= threshold * (1 - _BORDERLINE_PCT)


def calculate(profile: CompanyProfile) -> ThresholdStatus:
    """Compute CSDDD threshold status for a company profile. Deterministic."""
    emp = profile.employee_count_worldwide
    rev = profile.net_revenue_eur_millions

    tier1_emp = emp >= _TIER1_EMPLOYEES
    tier1_rev = rev >= _TIER1_REVENUE_M
    tier2_emp = emp >= _TIER2_EMPLOYEES
    tier2_rev = rev >= _TIER2_REVENUE_M

    # Level determination
    if tier1_emp and tier1_rev:
        level = CSDDDThresholdLevel.TIER_1.value
    elif tier2_emp and tier2_rev:
        level = CSDDDThresholdLevel.TIER_2.value
    else:
        level = CSDDDThresholdLevel.NOT_APPLICABLE.value

    # Borderline check (only when not already in scope)
    is_borderline = False
    borderline_msg = ""
    if level == CSDDDThresholdLevel.NOT_APPLICABLE.value:
        near_t1 = _near(emp, _TIER1_EMPLOYEES) or _near(rev, _TIER1_REVENUE_M)
        near_t2 = _near(emp, _TIER2_EMPLOYEES) or _near(rev, _TIER2_REVENUE_M)
        if near_t1:
            is_borderline = True
            level = CSDDDThresholdLevel.BORDERLINE.value
            borderline_msg = (
                f"Your company is within 20% of the Tier 1 threshold "
                f"(≥{_TIER1_EMPLOYEES:,} employees / ≥€{_TIER1_REVENUE_M:,.0f}M revenue, deadline {_TIER1_DEADLINE}). "
                f"Start preparing now."
            )
        elif near_t2:
            is_borderline = True
            level = CSDDDThresholdLevel.BORDERLINE.value
            borderline_msg = (
                f"Your company is within 20% of the Tier 2 threshold "
                f"(≥{_TIER2_EMPLOYEES:,} employees / ≥€{_TIER2_REVENUE_M:,.0f}M revenue, deadline {_TIER2_DEADLINE}). "
                f"Begin initial DD preparations."
            )

    # Recommendation
    if level == CSDDDThresholdLevel.TIER_1.value:
        recommendation = (
            f"Your company is subject to CSDDD Tier 1 obligations from {_TIER1_DEADLINE}. "
            f"Full DD implementation required. Ensure board approval (Art. 22) and annual reporting (Art. 16)."
        )
    elif level == CSDDDThresholdLevel.TIER_2.value:
        recommendation = (
            f"Your company is subject to CSDDD Tier 2 obligations from {_TIER2_DEADLINE}. "
            f"Implement DD policy (Art. 7) and grievance mechanism (Art. 14) as priority."
        )
    elif level == CSDDDThresholdLevel.BORDERLINE.value:
        recommendation = borderline_msg
    else:
        recommendation = (
            "Your company is currently below CSDDD thresholds. "
            "Monitor annually — regulatory scope may expand."
        )

    return ThresholdStatus(
        organization_id=profile.organization_id,
        fiscal_year=profile.fiscal_year,
        level=level,
        employee_count=emp,
        net_revenue_eur_millions=rev,
        tier1_employee_met=tier1_emp,
        tier1_revenue_met=tier1_rev,
        tier1_deadline=_TIER1_DEADLINE,
        tier2_employee_met=tier2_emp,
        tier2_revenue_met=tier2_rev,
        tier2_deadline=_TIER2_DEADLINE,
        is_borderline=is_borderline,
        borderline_message=borderline_msg,
        recommendation=recommendation,
    )
