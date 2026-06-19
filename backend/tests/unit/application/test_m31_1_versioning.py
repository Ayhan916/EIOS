"""Unit tests for M31.1 framework versioning in gaps and mappings."""

from __future__ import annotations

from domain.enums import EntityStatus
from domain.regulation import RegulationRequirement

from application.compliance.gap_engine import compute_gaps
from application.compliance.mapping_engine import auto_map_entity, create_manual_mapping
from application.compliance.seed_regulations import _bump_version


def _make_req(req_id: str, code: str, regulation_id: str = "reg-1") -> RegulationRequirement:
    return RegulationRequirement(
        id=req_id,
        regulation_id=regulation_id,
        code=code,
        reference="Art. X",
        title=f"Requirement {code}",
        description="",
        category="Environmental",
        pillar="E",
        severity="High",
        obligation_type="mandatory",
        keywords=["climate", "risk"],
        status=EntityStatus.ACTIVE,
    )


# ── Version bump helper ───────────────────────────────────────────────────────


class TestBumpVersion:
    def test_1_0_becomes_1_1(self):
        assert _bump_version("1.0") == "1.1"

    def test_1_1_becomes_1_2(self):
        assert _bump_version("1.1") == "1.2"

    def test_1_9_becomes_1_10(self):
        assert _bump_version("1.9") == "1.10"

    def test_malformed_version_appends_1(self):
        assert _bump_version("v2") == "v2.1"

    def test_two_dot_version_bumps_minor(self):
        # Only 2-part versions are bumped; others get .1 appended
        assert _bump_version("2.0") == "2.1"


# ── Gap engine: regulation_version_at_calculation ────────────────────────────


class TestGapVersionTracing:
    def test_gap_stores_regulation_version(self):
        req = _make_req("req-1", "CSDDD-Art-5", regulation_id="reg-csddd")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
            regulation_versions={"reg-csddd": "1.1"},
        )
        assert len(gaps) == 1
        assert gaps[0].regulation_version_at_calculation == "1.1"

    def test_gap_defaults_to_1_0_when_version_not_provided(self):
        req = _make_req("req-1", "CSDDD-Art-5", regulation_id="reg-csddd")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
            regulation_versions=None,
        )
        assert gaps[0].regulation_version_at_calculation == "1.0"

    def test_unresolved_finding_gap_stores_version(self):
        req = _make_req("req-1", "CSDDD-Art-6", regulation_id="reg-csddd")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids={"req-1"},
            open_finding_by_requirement={
                "req-1": [{"id": "f-1", "severity": "High", "description": "Issue"}]
            },
            open_risk_by_requirement={},
            organization_id="org-1",
            regulation_versions={"reg-csddd": "1.2"},
        )
        assert gaps[0].regulation_version_at_calculation == "1.2"

    def test_missing_control_gap_stores_version(self):
        req = _make_req("req-1", "LkSG-4", regulation_id="reg-lksg")
        gaps = compute_gaps(
            requirements=[req],
            covered_requirement_ids={"req-1"},
            open_finding_by_requirement={},
            open_risk_by_requirement={
                "req-1": [{"id": "r-1", "severity": "Medium", "description": "Risk"}]
            },
            organization_id="org-1",
            regulation_versions={"reg-lksg": "2.0"},
        )
        assert gaps[0].regulation_version_at_calculation == "2.0"

    def test_historical_gap_preserves_old_version(self):
        """Framework evolves from 1.0 → 1.1.  Older gap still references 1.0."""
        req = _make_req("req-old", "ESRS-E1", regulation_id="reg-esrs")

        # Calculation at version 1.0
        gaps_v1 = compute_gaps(
            requirements=[req],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
            regulation_versions={"reg-esrs": "1.0"},
        )
        assert gaps_v1[0].regulation_version_at_calculation == "1.0"

        # Framework evolves to 1.1 — recalculate fresh gaps
        gaps_v2 = compute_gaps(
            requirements=[req],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
            regulation_versions={"reg-esrs": "1.1"},
        )
        # New gap has new version
        assert gaps_v2[0].regulation_version_at_calculation == "1.1"
        # Old gap object is unchanged (it would be in the DB with version 1.0)
        assert gaps_v1[0].regulation_version_at_calculation == "1.0"

    def test_multiple_regs_each_store_own_version(self):
        req_csrd = _make_req("req-csrd", "CSRD-Art-19a", regulation_id="reg-csrd")
        req_lksg = _make_req("req-lksg", "LkSG-4", regulation_id="reg-lksg")
        gaps = compute_gaps(
            requirements=[req_csrd, req_lksg],
            covered_requirement_ids=set(),
            open_finding_by_requirement={},
            open_risk_by_requirement={},
            organization_id="org-1",
            regulation_versions={"reg-csrd": "1.1", "reg-lksg": "2.0"},
        )
        by_req = {g.regulation_requirement_id: g for g in gaps}
        assert by_req["req-csrd"].regulation_version_at_calculation == "1.1"
        assert by_req["req-lksg"].regulation_version_at_calculation == "2.0"


# ── Mapping engine: regulation_version_at_mapping ────────────────────────────


class TestMappingVersionTracing:
    def test_manual_mapping_stores_regulation_version(self):
        mapping = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="f-1",
            rationale="Tested",
            regulation_version="1.1",
        )
        assert mapping.regulation_version_at_mapping == "1.1"

    def test_manual_mapping_defaults_to_1_0(self):
        mapping = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="f-1",
            rationale="Tested",
        )
        assert mapping.regulation_version_at_mapping == "1.0"

    def test_auto_map_stores_version_per_requirement(self):
        req = _make_req("req-csrd", "CSRD-Art-19a", regulation_id="reg-csrd")
        mappings = auto_map_entity(
            organization_id="org-1",
            entity_type="finding",
            entity_id="f-1",
            entity_text="CSRD climate sustainability reporting",
            requirements=[req],
            regulation_version_by_id={"reg-csrd": "1.2"},
        )
        assert len(mappings) == 1
        assert mappings[0].regulation_version_at_mapping == "1.2"

    def test_auto_map_defaults_to_1_0_when_no_version_map(self):
        req = _make_req("req-1", "CSDDD-Art-5", regulation_id="reg-csddd")
        mappings = auto_map_entity(
            organization_id="org-1",
            entity_type="risk",
            entity_id="r-1",
            entity_text="risk climate",
            requirements=[req],
        )
        if mappings:
            assert mappings[0].regulation_version_at_mapping == "1.0"

    def test_mapping_version_is_preserved_after_framework_update(self):
        """Mapping created at v1.0 retains that version even after framework → v1.1."""
        mapping_v1 = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="f-1",
            rationale="Mapped at v1",
            regulation_version="1.0",
        )
        # Simulate framework update — creates new mappings with v1.1
        mapping_v2 = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="f-2",
            rationale="Mapped at v1.1",
            regulation_version="1.1",
        )
        assert mapping_v1.regulation_version_at_mapping == "1.0"
        assert mapping_v2.regulation_version_at_mapping == "1.1"
