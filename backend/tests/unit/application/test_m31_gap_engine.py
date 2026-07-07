"""Unit tests for M31 gap engine."""

from __future__ import annotations

from application.compliance.gap_engine import _is_disclosure_framework, _max_severity, compute_gaps
from domain.enums import EntityStatus
from domain.regulation import RegulationRequirement


def _make_req(req_id: str, code: str, severity: str = "High") -> RegulationRequirement:
    return RegulationRequirement(
        id=req_id,
        regulation_id="reg-1",
        code=code,
        reference="Art. X",
        title=f"Requirement {code}",
        description="",
        category="Environmental",
        pillar="E",
        severity=severity,
        obligation_type="mandatory",
        keywords=[],
        status=EntityStatus.ACTIVE,
    )


class TestMaxSeverity:
    def test_critical_beats_high(self):
        assert _max_severity("Critical", "High") == "Critical"

    def test_high_beats_medium(self):
        assert _max_severity("Medium", "High") == "High"

    def test_same_level_returns_that_level(self):
        assert _max_severity("Low", "Low") == "Low"


class TestIsDisclosureFramework:
    def test_csrd_is_disclosure(self):
        assert _is_disclosure_framework("CSRD-Art-19a") is True

    def test_esrs_is_disclosure(self):
        assert _is_disclosure_framework("ESRS-E1") is True

    def test_issb_is_disclosure(self):
        assert _is_disclosure_framework("ISSB-S1-Core") is True

    def test_tcfd_is_disclosure(self):
        assert _is_disclosure_framework("TCFD-Gov") is True

    def test_csddd_is_not_disclosure(self):
        # CSDDD is a due-diligence directive, not a disclosure standard
        assert _is_disclosure_framework("CSDDD-Art-5") is False

    def test_lksg_is_not_disclosure(self):
        assert _is_disclosure_framework("LkSG-3") is False


class TestComputeGaps:
    def test_missing_evidence_gap_for_uncovered_requirement(self):
        req = _make_req("req-1", "CSDDD-Art-5", severity="High")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
        )
        assert len(gaps) == 1
        assert gaps[0].gap_type == "missing_evidence"
        assert gaps[0].severity == "High"
        assert gaps[0].regulation_requirement_id == "req-1"

    def test_missing_disclosure_for_csrd_uncovered(self):
        req = _make_req("req-1", "CSRD-Art-19a", severity="High")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
        )
        assert gaps[0].gap_type == "missing_disclosure"

    def test_no_gap_when_requirement_covered_and_no_issues(self):
        req = _make_req("req-1", "ESRS-E1", severity="Medium")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids={"req-1"},
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
        )
        assert gaps == []

    def test_unresolved_finding_gap(self):
        req = _make_req("req-1", "CSDDD-Art-6", severity="Medium")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids={"req-1"},
            open_finding_by_requirement={
                "req-1": [{"id": "f-1", "severity": "Critical", "description": "No audit trail"}]
            },
            open_risk_by_requirement={},
            organization_id="org-1",
        )
        assert len(gaps) == 1
        assert gaps[0].gap_type == "unresolved_finding"
        assert gaps[0].severity == "Critical"  # escalated from finding
        assert gaps[0].source_entity_id == "f-1"

    def test_missing_control_gap_for_open_risk(self):
        req = _make_req("req-1", "LkSG-4", severity="High")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids={"req-1"},
            open_finding_by_requirement={},
            open_risk_by_requirement={
                "req-1": [{"id": "r-1", "severity": "High", "description": "No mitigation"}]
            },
            organization_id="org-1",
        )
        assert len(gaps) == 1
        assert gaps[0].gap_type == "missing_control"
        assert gaps[0].source_entity_type == "risk"

    def test_multiple_findings_create_multiple_gaps(self):
        req = _make_req("req-1", "CSDDD-Art-7", severity="Medium")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids={"req-1"},
            open_finding_by_requirement={
                "req-1": [
                    {"id": "f-1", "severity": "High", "description": "Issue 1"},
                    {"id": "f-2", "severity": "Medium", "description": "Issue 2"},
                ]
            },
            open_risk_by_requirement={},
            organization_id="org-1",
        )
        assert len(gaps) == 2
        entity_ids = {g.source_entity_id for g in gaps}
        assert "f-1" in entity_ids
        assert "f-2" in entity_ids

    def test_supplier_id_propagated(self):
        req = _make_req("req-1", "ESRS-S2", severity="High")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
            supplier_id="sup-42",
        )
        assert gaps[0].supplier_id == "sup-42"

    def test_gap_calculation_version_set(self):
        req = _make_req("req-1", "CSDDD-Art-5")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
        )
        assert gaps[0].calculation_version == "1.0"
        assert gaps[0].calculated_at is not None

    def test_empty_requirements_returns_no_gaps(self):
        gaps = compute_gaps(
            requirements=[],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
        )
        assert gaps == []
