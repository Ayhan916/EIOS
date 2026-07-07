"""Unit tests for M31 mapping engine."""

from __future__ import annotations

from application.compliance.mapping_engine import (
    _HIGH_CONFIDENCE,
    _LOW_CONFIDENCE,
    auto_map_entity,
    create_manual_mapping,
)
from domain.enums import EntityStatus
from domain.regulation import RegulationRequirement


def _make_req(code: str, keywords: list[str], severity: str = "High") -> RegulationRequirement:
    return RegulationRequirement(
        regulation_id="reg-1",
        code=code,
        reference=f"Art. {code}",
        title=f"Requirement {code}",
        description="",
        category="Environmental",
        pillar="E",
        severity=severity,
        obligation_type="mandatory",
        keywords=keywords,
        status=EntityStatus.ACTIVE,
    )


class TestCreateManualMapping:
    def test_creates_mapping_with_required_fields(self):
        m = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="finding-1",
            rationale="Matches due diligence obligation",
        )
        assert m.organization_id == "org-1"
        assert m.regulation_requirement_id == "req-1"
        assert m.entity_type == "finding"
        assert m.entity_id == "finding-1"
        assert m.mapping_method == "manual"
        assert m.rationale == "Matches due diligence obligation"

    def test_default_confidence_is_0_9(self):
        m = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="risk",
            entity_id="risk-1",
            rationale="test",
        )
        assert m.confidence == 0.9

    def test_confidence_clamped_to_valid_range(self):
        m_high = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="f-1",
            rationale="",
            confidence=1.5,
        )
        m_low = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="f-2",
            rationale="",
            confidence=-0.5,
        )
        assert m_high.confidence == 1.0
        assert m_low.confidence == 0.0

    def test_default_rationale_provided_when_empty(self):
        m = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="f-1",
            rationale="",
        )
        assert len(m.rationale) > 0

    def test_supplier_and_assessment_ids_optional(self):
        m = create_manual_mapping(
            organization_id="org-1",
            regulation_requirement_id="req-1",
            entity_type="finding",
            entity_id="f-1",
            rationale="test",
            supplier_id="sup-1",
            assessment_id="ass-1",
        )
        assert m.supplier_id == "sup-1"
        assert m.assessment_id == "ass-1"


class TestAutoMapEntity:
    def test_returns_empty_when_no_keyword_match(self):
        req = _make_req("CSRD-1", ["due diligence policy", "corporate policy"])
        result = auto_map_entity(
            organization_id="org-1",
            entity_type="finding",
            entity_id="f-1",
            entity_text="Water treatment facility failed inspection",
            requirements=[req],
        )
        assert result == []

    def test_matches_single_keyword(self):
        req = _make_req("CSRD-1", ["due diligence policy", "corporate policy"])
        result = auto_map_entity(
            organization_id="org-1",
            entity_type="finding",
            entity_id="f-1",
            entity_text="The supplier has no due diligence policy in place",
            requirements=[req],
        )
        assert len(result) == 1
        assert result[0].regulation_requirement_id == req.id
        assert result[0].mapping_method == "rule_based"
        assert result[0].confidence == _LOW_CONFIDENCE

    def test_high_confidence_on_two_or_more_keywords(self):
        req = _make_req("CSRD-1", ["due diligence policy", "corporate policy"])
        result = auto_map_entity(
            organization_id="org-1",
            entity_type="finding",
            entity_id="f-1",
            entity_text="No corporate policy or due diligence policy exists",
            requirements=[req],
        )
        assert result[0].confidence == _HIGH_CONFIDENCE

    def test_matches_multiple_requirements(self):
        reqs = [
            _make_req("CSRD-1", ["climate change", "GHG"]),
            _make_req("CSDDD-1", ["grievance mechanism", "complaint"]),
        ]
        text = "Supplier has no grievance mechanism and ignores GHG targets"
        result = auto_map_entity(
            organization_id="org-1",
            entity_type="risk",
            entity_id="r-1",
            entity_text=text,
            requirements=reqs,
        )
        codes = {r.regulation_requirement_id for r in result}
        assert reqs[0].id in codes
        assert reqs[1].id in codes

    def test_case_insensitive_matching(self):
        req = _make_req("TCFD-1", ["TCFD Governance", "Board Climate Oversight"])
        result = auto_map_entity(
            organization_id="org-1",
            entity_type="finding",
            entity_id="f-1",
            entity_text="board climate oversight was not documented",
            requirements=[req],
        )
        assert len(result) == 1

    def test_rationale_includes_matched_keywords(self):
        req = _make_req("ISSB-1", ["IFRS S1", "sustainability KPIs"])
        result = auto_map_entity(
            organization_id="org-1",
            entity_type="recommendation",
            entity_id="rec-1",
            entity_text="Implement IFRS S1 disclosures and measure sustainability KPIs",
            requirements=[req],
        )
        assert "IFRS S1" in result[0].rationale or "sustainability KPIs" in result[0].rationale

    def test_no_match_returns_empty_list_not_none(self):
        result = auto_map_entity(
            organization_id="org-1",
            entity_type="finding",
            entity_id="f-1",
            entity_text="generic text with no regulatory keywords",
            requirements=[],
        )
        assert result == []
