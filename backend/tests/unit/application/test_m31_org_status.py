"""Unit tests for M31 organisation compliance status calculator."""

from __future__ import annotations

import pytest

from application.compliance.org_status import (
    compute_framework_status,
    compute_org_status,
    _COMPLIANT_THRESHOLD,
    _PARTIAL_THRESHOLD,
)
from domain.compliance_gap import ComplianceGap
from domain.enums import EntityStatus
from domain.regulation import RegulationRequirement


def _make_req(req_id: str, code: str, severity: str = "High") -> RegulationRequirement:
    return RegulationRequirement(
        id=req_id,
        regulation_id="reg-1",
        code=code,
        reference="Art. X",
        title=f"Req {code}",
        description="",
        category="Environmental",
        pillar="E",
        severity=severity,
        obligation_type="mandatory",
        keywords=[],
        status=EntityStatus.ACTIVE,
    )


def _make_gap(gap_id: str, req_id: str, severity: str = "High") -> ComplianceGap:
    from datetime import UTC, datetime

    return ComplianceGap(
        id=gap_id,
        organization_id="org-1",
        regulation_requirement_id=req_id,
        gap_type="missing_evidence",
        severity=severity,
        description="",
        calculated_at=datetime.now(UTC),
        status=EntityStatus.ACTIVE,
    )


class TestComputeFrameworkStatus:
    def test_unknown_when_no_requirements(self):
        result = compute_framework_status(
            regulation_code="CSRD",
            regulation_name="CSRD",
            requirements=[],
            covered_ids=set(),
            open_gaps=[],
        )
        assert result.status == "Unknown"

    def test_unknown_when_no_mappings(self):
        reqs = [_make_req("r1", "CSRD-1"), _make_req("r2", "CSRD-2")]
        result = compute_framework_status(
            regulation_code="CSRD",
            regulation_name="CSRD",
            requirements=reqs,
            covered_ids=set(),
            open_gaps=[],
        )
        assert result.status == "Unknown"

    def test_compliant_at_80_percent_no_critical_gaps(self):
        reqs = [_make_req(f"r{i}", f"CSRD-{i}") for i in range(10)]
        covered = {r.id for r in reqs[:8]}  # 80% covered
        result = compute_framework_status(
            regulation_code="CSRD",
            regulation_name="CSRD",
            requirements=reqs,
            covered_ids=covered,
            open_gaps=[],
        )
        assert result.status == "Compliant"
        assert result.coverage_ratio >= _COMPLIANT_THRESHOLD

    def test_partially_compliant_at_60_percent(self):
        reqs = [_make_req(f"r{i}", f"ESRS-{i}") for i in range(10)]
        covered = {r.id for r in reqs[:6]}  # 60%
        result = compute_framework_status(
            regulation_code="ESRS",
            regulation_name="ESRS",
            requirements=reqs,
            covered_ids=covered,
            open_gaps=[],
        )
        assert result.status == "Partially Compliant"

    def test_non_compliant_at_40_percent(self):
        reqs = [_make_req(f"r{i}", f"CSDDD-{i}") for i in range(10)]
        covered = {r.id for r in reqs[:4]}  # 40%
        result = compute_framework_status(
            regulation_code="CSDDD",
            regulation_name="CSDDD",
            requirements=reqs,
            covered_ids=covered,
            open_gaps=[_make_gap("g1", "r0", "Critical")],
        )
        assert result.status == "Non-Compliant"

    def test_critical_gap_count_counted(self):
        reqs = [_make_req(f"r{i}", f"CSRD-{i}") for i in range(5)]
        covered = {r.id for r in reqs}
        gaps = [_make_gap("g1", reqs[0].id, "Critical"), _make_gap("g2", reqs[1].id, "High")]
        result = compute_framework_status(
            regulation_code="CSRD",
            regulation_name="CSRD",
            requirements=reqs,
            covered_ids=covered,
            open_gaps=gaps,
        )
        assert result.critical_gap_count == 1
        assert result.high_gap_count == 1

    def test_top_gap_codes_populated(self):
        reqs = [_make_req(f"r{i}", f"LkSG-{i}") for i in range(10)]
        result = compute_framework_status(
            regulation_code="LkSG",
            regulation_name="LkSG",
            requirements=reqs,
            covered_ids=set(),
            open_gaps=[],
        )
        assert len(result.top_gap_requirement_codes) <= 5


class TestComputeOrgStatus:
    def test_returns_all_frameworks(self):
        reqs_a = [_make_req(f"a{i}", f"CSRD-{i}") for i in range(5)]
        reqs_b = [_make_req(f"b{i}", f"ESRS-{i}") for i in range(3)]
        status = compute_org_status(
            organization_id="org-1",
            requirements_by_regulation={
                "reg-a": ("CSRD", reqs_a),
                "reg-b": ("ESRS", reqs_b),
            },
            covered_ids=set(),
            open_gaps=[],
        )
        assert len(status.frameworks) == 2
        assert status.organization_id == "org-1"

    def test_total_open_gaps_correct(self):
        reqs = [_make_req(f"r{i}", f"CSDDD-{i}") for i in range(3)]
        gaps = [_make_gap(f"g{i}", reqs[i].id) for i in range(3)]
        status = compute_org_status(
            organization_id="org-1",
            requirements_by_regulation={"reg-1": ("CSDDD", reqs)},
            covered_ids=set(),
            open_gaps=gaps,
        )
        assert status.total_open_gaps == 3

    def test_non_compliant_sorted_first(self):
        reqs_a = [_make_req(f"a{i}", f"CSRD-{i}") for i in range(5)]
        reqs_b = [_make_req(f"b{i}", f"CSDDD-{i}") for i in range(5)]
        covered_all_a = {r.id for r in reqs_a}
        status = compute_org_status(
            organization_id="org-1",
            requirements_by_regulation={
                "reg-a": ("CSRD", reqs_a),
                "reg-b": ("CSDDD", reqs_b),
            },
            covered_ids=covered_all_a,
            open_gaps=[],
        )
        # CSDDD uncovered → Non-Compliant/Unknown should appear before Compliant CSRD
        statuses = [f.status for f in status.frameworks]
        csrd_idx = next(i for i, f in enumerate(status.frameworks) if f.regulation_code == "CSRD")
        csddd_idx = next(i for i, f in enumerate(status.frameworks) if f.regulation_code == "CSDDD")
        assert csddd_idx < csrd_idx  # non-compliant/unknown before compliant

    def test_overall_coverage_ratio_computed(self):
        reqs = [_make_req(f"r{i}", f"ESRS-{i}") for i in range(4)]
        covered = {reqs[0].id, reqs[1].id}  # 50%
        status = compute_org_status(
            organization_id="org-1",
            requirements_by_regulation={"reg-1": ("ESRS", reqs)},
            covered_ids=covered,
            open_gaps=[],
        )
        assert abs(status.overall_coverage_ratio - 0.5) < 0.01
