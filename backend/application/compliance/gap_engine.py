"""Compliance Gap Engine.

Computes ComplianceGap records for an organisation by comparing:
  - All active RegulationRequirements
  - The set of RequirementMappings for the org
  - The severity and resolution status of mapped source entities

Gap types:
  missing_evidence     — requirement has zero mappings for this org
  missing_disclosure   — disclosure-oriented requirement (CSRD/ESRS) with no mapping
  unresolved_finding   — requirement is mapped to a Finding that is still open/unresolved
  missing_control      — requirement is mapped to a Risk with no mitigating action

Severity assignment:
  - Uses requirement.severity as the baseline
  - Escalates to Critical if a mapped finding severity is Critical
  - Never downgrade below requirement baseline

Gap recalculation is idempotent: caller deletes existing open gaps for the org,
then writes the freshly computed set. Historical resolved gaps are preserved.
"""

from __future__ import annotations

from datetime import UTC, datetime

from domain.compliance_gap import ComplianceGap
from domain.enums import EntityStatus
from domain.regulation import RegulationRequirement

_GAP_VERSION = "1.0"

_SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
_RANK_SEVERITY = {v: k for k, v in _SEVERITY_RANK.items()}

_DISCLOSURE_CODES = frozenset(
    {
        "CSRD",
        "ESRS",
        "ISSB",
        "TCFD",
        "EU_TAXONOMY",
    }
)


def _max_severity(a: str, b: str) -> str:
    ra, rb = _SEVERITY_RANK.get(a, 2), _SEVERITY_RANK.get(b, 2)
    return a if ra >= rb else b


def _is_disclosure_framework(code: str) -> bool:
    return any(code.startswith(fw) for fw in _DISCLOSURE_CODES)


def compute_gaps(
    requirements: list[RegulationRequirement],
    covered_requirement_ids: set[str],
    open_finding_by_requirement: dict[str, list[dict]],
    open_risk_by_requirement: dict[str, list[dict]],
    organization_id: str,
    supplier_id: str | None = None,
    regulation_versions: dict[str, str] | None = None,
) -> list[ComplianceGap]:
    """Compute compliance gaps for an organisation.

    Args:
        requirements: all active RegulationRequirements
        covered_requirement_ids: set of requirement IDs that have ≥1 mapping for this org
        open_finding_by_requirement: {req_id: [{"id":..., "severity":..., "description":...}]}
        open_risk_by_requirement:    {req_id: [{"id":..., "severity":..., "description":...}]}
        organization_id: org context
        supplier_id: if provided, scopes gaps to a specific supplier

    Returns:
        List of ComplianceGap domain objects (not yet persisted).
    """
    now = datetime.now(UTC)
    _versions = regulation_versions or {}
    gaps: list[ComplianceGap] = []

    for req in requirements:
        has_mapping = req.id in covered_requirement_ids
        open_findings = open_finding_by_requirement.get(req.id, [])
        open_risks = open_risk_by_requirement.get(req.id, [])
        reg_version = _versions.get(req.regulation_id, "1.0")

        if not has_mapping:
            # No mapping at all — missing evidence / missing disclosure
            gap_type = (
                "missing_disclosure" if _is_disclosure_framework(req.code) else "missing_evidence"
            )
            gaps.append(
                ComplianceGap(
                    organization_id=organization_id,
                    regulation_requirement_id=req.id,
                    supplier_id=supplier_id,
                    gap_type=gap_type,
                    severity=req.severity,
                    description=(
                        f"No evidence mapped to {req.reference} — {req.title}. "
                        "This requirement has no linked findings, risks, or recommendations."
                    ),
                    evidence_refs=[],
                    source_entity_type=None,
                    source_entity_id=None,
                    calculated_at=now,
                    calculation_version=_GAP_VERSION,
                    regulation_version_at_calculation=reg_version,
                    status=EntityStatus.ACTIVE,
                )
            )
        else:
            # Has mappings — check for unresolved issues
            for finding in open_findings:
                eff_severity = _max_severity(req.severity, finding.get("severity", "Medium"))
                gaps.append(
                    ComplianceGap(
                        organization_id=organization_id,
                        regulation_requirement_id=req.id,
                        supplier_id=supplier_id,
                        gap_type="unresolved_finding",
                        severity=eff_severity,
                        description=(
                            f"Open finding linked to {req.reference} — {req.title}: "
                            + finding.get("description", "")[:200]
                        ),
                        evidence_refs=[],
                        source_entity_type="finding",
                        source_entity_id=finding.get("id"),
                        calculated_at=now,
                        calculation_version=_GAP_VERSION,
                        regulation_version_at_calculation=reg_version,
                        status=EntityStatus.ACTIVE,
                    )
                )
            for risk in open_risks:
                eff_severity = _max_severity(req.severity, risk.get("severity", "Medium"))
                gaps.append(
                    ComplianceGap(
                        organization_id=organization_id,
                        regulation_requirement_id=req.id,
                        supplier_id=supplier_id,
                        gap_type="missing_control",
                        severity=eff_severity,
                        description=(
                            f"Open risk with no mitigating control linked to {req.reference} — "
                            f"{req.title}: " + risk.get("description", "")[:200]
                        ),
                        evidence_refs=[],
                        source_entity_type="risk",
                        source_entity_id=risk.get("id"),
                        calculated_at=now,
                        calculation_version=_GAP_VERSION,
                        regulation_version_at_calculation=reg_version,
                        status=EntityStatus.ACTIVE,
                    )
                )

    return gaps
