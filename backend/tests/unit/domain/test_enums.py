"""Tests for EIOS domain enumerations."""

from domain.enums import ConfidenceLevel, ControlType, EntityStatus, EvidenceType, RiskLevel


class TestEntityStatus:
    def test_has_exactly_nine_states(self) -> None:
        assert len(EntityStatus) == 9

    def test_state_values(self) -> None:
        assert EntityStatus.CREATED == "Created"
        assert EntityStatus.DRAFT == "Draft"
        assert EntityStatus.VALIDATED == "Validated"
        assert EntityStatus.REVIEWED == "Reviewed"
        assert EntityStatus.APPROVED == "Approved"
        assert EntityStatus.ACTIVE == "Active"
        assert EntityStatus.SUSPENDED == "Suspended"
        assert EntityStatus.ARCHIVED == "Archived"
        assert EntityStatus.DELETED == "Deleted"

    def test_is_string_enum(self) -> None:
        assert isinstance(EntityStatus.DRAFT, str)
        assert EntityStatus.DRAFT == "Draft"


class TestRiskLevel:
    def test_has_four_levels(self) -> None:
        assert len(RiskLevel) == 4

    def test_levels(self) -> None:
        assert RiskLevel.LOW == "Low"
        assert RiskLevel.MEDIUM == "Medium"
        assert RiskLevel.HIGH == "High"
        assert RiskLevel.CRITICAL == "Critical"


class TestConfidenceLevel:
    def test_has_three_levels(self) -> None:
        assert len(ConfidenceLevel) == 3

    def test_levels(self) -> None:
        assert ConfidenceLevel.LOW == "Low"
        assert ConfidenceLevel.MEDIUM == "Medium"
        assert ConfidenceLevel.HIGH == "High"


class TestControlType:
    def test_has_three_types(self) -> None:
        assert len(ControlType) == 3

    def test_types(self) -> None:
        assert ControlType.PREVENTIVE == "Preventive"
        assert ControlType.DETECTIVE == "Detective"
        assert ControlType.CORRECTIVE == "Corrective"


class TestEvidenceType:
    def test_has_six_types(self) -> None:
        assert len(EvidenceType) == 6

    def test_types(self) -> None:
        assert EvidenceType.DOCUMENT == "Document"
        assert EvidenceType.REPORT == "Report"
        assert EvidenceType.PUBLICATION == "Publication"
        assert EvidenceType.WEBSITE == "Website"
        assert EvidenceType.DATA == "Data"
        assert EvidenceType.TESTIMONY == "Testimony"
