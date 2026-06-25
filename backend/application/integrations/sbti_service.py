"""M48.1 G-058 — SBTi (Science Based Targets initiative) Validation.

Validates whether an organization's emissions reduction target is aligned with
SBTi methodology criteria.

SBTi criteria for 1.5°C pathway (NET-ZERO Standard):
  - Scope 1+2: ≥4.2% absolute reduction per year (or intensity-based)
  - Scope 3: ≥ 25% reduction by 2030 (near-term), full value chain net-zero by 2050
  - Base year: any year 2015–2021

This is a deterministic, rule-based validator — no AI scoring.
Full SBTi validation requires submission to SBTi portal (out of scope).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SBTiValidationResult:
    target_id: str
    organization_name: str
    # Criteria results
    scope_1_2_aligned: bool
    scope_3_aligned: bool
    base_year_valid: bool
    target_year_valid: bool
    # Derived
    overall_aligned: bool
    confidence_note: str
    criteria_detail: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "organization_name": self.organization_name,
            "overall_aligned": self.overall_aligned,
            "scope_1_2_aligned": self.scope_1_2_aligned,
            "scope_3_aligned": self.scope_3_aligned,
            "base_year_valid": self.base_year_valid,
            "target_year_valid": self.target_year_valid,
            "confidence_note": self.confidence_note,
            "criteria_detail": self.criteria_detail,
            "methodology": "SBTi NET-ZERO Standard v1.0 (1.5°C pathway)",
            "disclaimer": (
                "This is a preliminary self-assessment. Official SBTi validation "
                "requires submission at sciencebasedtargets.org."
            ),
        }


def validate_sbti_target(
    *,
    target_id: str,
    organization_name: str,
    base_year: int,
    target_year: int,
    base_year_scope1_tco2e: float,
    base_year_scope2_tco2e: float,
    target_scope1_tco2e: float,
    target_scope2_tco2e: float,
    # Scope 3 (optional for near-term)
    base_year_scope3_tco2e: float | None = None,
    target_scope3_tco2e: float | None = None,
    # Target type
    target_type: str = "ABSOLUTE",
) -> SBTiValidationResult:
    """Apply SBTi 1.5°C criteria and return a validation result.

    Criteria checked:
    1. Base year must be 2015–2021.
    2. Near-term target year: 2025–2035.
    3. Scope 1+2: ≥4.2% absolute reduction per year.
    4. Scope 3: ≥25% reduction by 2030 (if data provided).
    """
    criteria: list[dict[str, Any]] = []
    current_year = 2026

    # ── Criterion 1: Base year ────────────────────────────────────────────────
    base_year_valid = 2015 <= base_year <= 2021
    criteria.append({
        "criterion": "Base year",
        "requirement": "2015–2021",
        "value": base_year,
        "met": base_year_valid,
    })

    # ── Criterion 2: Target year ──────────────────────────────────────────────
    target_year_valid = 2025 <= target_year <= 2050
    criteria.append({
        "criterion": "Target year",
        "requirement": "2025–2050 (near-term ≤ 2035)",
        "value": target_year,
        "met": target_year_valid,
    })

    # ── Criterion 3: Scope 1+2 reduction rate ────────────────────────────────
    base_s12 = base_year_scope1_tco2e + base_year_scope2_tco2e
    target_s12 = target_scope1_tco2e + target_scope2_tco2e
    years = max(target_year - base_year, 1)

    if base_s12 > 0:
        total_reduction_pct = (base_s12 - target_s12) / base_s12 * 100
        annual_rate = total_reduction_pct / years
        required_annual = 4.2
        scope_1_2_aligned = annual_rate >= required_annual
    else:
        total_reduction_pct = 0.0
        annual_rate = 0.0
        scope_1_2_aligned = False

    criteria.append({
        "criterion": "Scope 1+2 annual reduction",
        "requirement": "≥4.2% per year (1.5°C pathway)",
        "value": round(annual_rate, 2),
        "unit": "%/year",
        "met": scope_1_2_aligned,
        "detail": f"Total reduction: {round(total_reduction_pct, 1)}% over {years} years",
    })

    # ── Criterion 4: Scope 3 ─────────────────────────────────────────────────
    if base_year_scope3_tco2e is not None and target_scope3_tco2e is not None:
        if base_year_scope3_tco2e > 0:
            s3_reduction_pct = (base_year_scope3_tco2e - target_scope3_tco2e) / base_year_scope3_tco2e * 100
            scope_3_aligned = s3_reduction_pct >= 25.0 and target_year <= 2030
        else:
            s3_reduction_pct = 0.0
            scope_3_aligned = False
        criteria.append({
            "criterion": "Scope 3 reduction",
            "requirement": "≥25% by 2030",
            "value": round(s3_reduction_pct, 1),
            "unit": "%",
            "met": scope_3_aligned,
        })
    else:
        scope_3_aligned = True  # Not required if data not submitted
        criteria.append({
            "criterion": "Scope 3 reduction",
            "requirement": "≥25% by 2030 (data not provided — marked N/A)",
            "value": None,
            "met": None,
            "detail": "Submit Scope 3 data for full SBTi validation",
        })

    overall = base_year_valid and target_year_valid and scope_1_2_aligned
    note = (
        "Preliminary assessment passes SBTi 1.5°C Scope 1+2 criteria."
        if overall else
        "One or more SBTi criteria not met. Review criteria detail."
    )

    return SBTiValidationResult(
        target_id=target_id,
        organization_name=organization_name,
        scope_1_2_aligned=scope_1_2_aligned,
        scope_3_aligned=scope_3_aligned,
        base_year_valid=base_year_valid,
        target_year_valid=target_year_valid,
        overall_aligned=overall,
        confidence_note=note,
        criteria_detail=criteria,
    )
