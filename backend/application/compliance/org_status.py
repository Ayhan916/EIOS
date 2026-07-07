"""Organisation-level compliance status calculator.

Computes per-framework compliance status from:
  - The set of covered requirement IDs (have ≥1 mapping)
  - The set of open gaps (severity + type)

Status values:
  Compliant         — ≥80% requirements covered, no Critical/High open gaps
  Partially Compliant — ≥50% requirements covered, or some High/Critical gaps
  Non-Compliant     — <50% requirements covered, or Critical gaps
  Unknown           — 0 requirements known (e.g. framework not yet seeded)

Every status record documents the thresholds used so results are reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.compliance_gap import ComplianceGap
from domain.regulation import RegulationRequirement

_COMPLIANT_THRESHOLD = 0.80
_PARTIAL_THRESHOLD = 0.50
_CALC_VERSION = "1.0"


@dataclass
class FrameworkStatus:
    regulation_code: str
    regulation_name: str
    status: str  # Compliant / Partially Compliant / Non-Compliant / Unknown
    total_requirements: int
    covered_requirements: int
    coverage_ratio: float
    open_gap_count: int
    critical_gap_count: int
    high_gap_count: int
    medium_gap_count: int
    low_gap_count: int
    explanation: str
    calculation_version: str = _CALC_VERSION
    top_gap_requirement_codes: list[str] = field(default_factory=list)


@dataclass
class OrgComplianceStatus:
    organization_id: str
    frameworks: list[FrameworkStatus]
    total_open_gaps: int
    total_critical_gaps: int
    overall_coverage_ratio: float
    calculation_version: str = _CALC_VERSION


def compute_framework_status(
    regulation_code: str,
    regulation_name: str,
    requirements: list[RegulationRequirement],
    covered_ids: set[str],
    open_gaps: list[ComplianceGap],
) -> FrameworkStatus:
    total = len(requirements)
    if total == 0:
        return FrameworkStatus(
            regulation_code=regulation_code,
            regulation_name=regulation_name,
            status="Unknown",
            total_requirements=0,
            covered_requirements=0,
            coverage_ratio=0.0,
            open_gap_count=0,
            critical_gap_count=0,
            high_gap_count=0,
            medium_gap_count=0,
            low_gap_count=0,
            explanation="No requirements found for this framework.",
        )

    req_ids = {r.id for r in requirements}
    covered = len(req_ids & covered_ids)
    ratio = covered / total

    # Gaps scoped to this framework's requirements
    fw_gaps = [g for g in open_gaps if g.regulation_requirement_id in req_ids]
    critical = sum(1 for g in fw_gaps if g.severity == "Critical")
    high = sum(1 for g in fw_gaps if g.severity == "High")
    medium = sum(1 for g in fw_gaps if g.severity == "Medium")
    low = sum(1 for g in fw_gaps if g.severity == "Low")

    # Derive status
    if total == 0 or covered == 0:
        status = "Unknown"
        explanation = "No requirements are covered. Begin mapping findings and risks."
    elif ratio >= _COMPLIANT_THRESHOLD and critical == 0 and high == 0:
        status = "Compliant"
        explanation = (
            f"{covered}/{total} requirements covered ({ratio:.0%}), no Critical or High gaps."
        )
    elif ratio >= _PARTIAL_THRESHOLD or (critical == 0):
        status = "Partially Compliant"
        explanation = (
            f"{covered}/{total} requirements covered ({ratio:.0%}). "
            f"{critical} Critical, {high} High open gaps require attention."
        )
    else:
        status = "Non-Compliant"
        explanation = (
            f"Only {covered}/{total} requirements covered ({ratio:.0%}). "
            f"{critical} Critical, {high} High open gaps. Immediate action required."
        )

    # Surface top uncovered high-severity requirement codes
    uncovered_reqs = [r for r in requirements if r.id not in covered_ids]
    top_gaps = sorted(
        uncovered_reqs,
        key=lambda r: {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(r.severity, 2),
        reverse=True,
    )[:5]

    return FrameworkStatus(
        regulation_code=regulation_code,
        regulation_name=regulation_name,
        status=status,
        total_requirements=total,
        covered_requirements=covered,
        coverage_ratio=ratio,
        open_gap_count=len(fw_gaps),
        critical_gap_count=critical,
        high_gap_count=high,
        medium_gap_count=medium,
        low_gap_count=low,
        explanation=explanation,
        top_gap_requirement_codes=[r.code for r in top_gaps],
    )


def compute_org_status(
    organization_id: str,
    requirements_by_regulation: dict[str, tuple[str, list[RegulationRequirement]]],
    covered_ids: set[str],
    open_gaps: list[ComplianceGap],
) -> OrgComplianceStatus:
    """Compute full org-level compliance status across all frameworks.

    Args:
        requirements_by_regulation: {regulation_id: (regulation_code, [requirements])}
        covered_ids: set of requirement IDs with ≥1 mapping
        open_gaps: all unresolved ComplianceGap records for the org
    """
    frameworks: list[FrameworkStatus] = []

    for _reg_id, (reg_code, reqs) in requirements_by_regulation.items():
        fw_status = compute_framework_status(
            regulation_code=reg_code,
            regulation_name=reg_code,
            requirements=reqs,
            covered_ids=covered_ids,
            open_gaps=open_gaps,
        )
        frameworks.append(fw_status)

    # Sort: Non-Compliant first, then Partially, then Compliant
    _order = {"Non-Compliant": 0, "Partially Compliant": 1, "Unknown": 2, "Compliant": 3}
    frameworks.sort(key=lambda f: _order.get(f.status, 2))

    all_reqs = sum(f.total_requirements for f in frameworks)
    all_covered = sum(f.covered_requirements for f in frameworks)
    overall_ratio = all_covered / all_reqs if all_reqs else 0.0

    return OrgComplianceStatus(
        organization_id=organization_id,
        frameworks=frameworks,
        total_open_gaps=len(open_gaps),
        total_critical_gaps=sum(1 for g in open_gaps if g.severity == "Critical"),
        overall_coverage_ratio=overall_ratio,
    )
