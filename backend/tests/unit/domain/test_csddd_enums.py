"""Tests for CSDDD Sector Risk Register domain enums (TASK-003 Phase 1)."""

from __future__ import annotations

import pytest

from domain.enums import (
    CalibrationStatus,
    CSDDDRight,
    ScenarioSuggestionStatus,
    ScenarioType,
)


class TestCSDDDRight:
    def test_has_exactly_21_rights(self) -> None:
        # CSDDD Annex I — any change here is a breaking contract change
        assert len(CSDDDRight) == 21

    def test_all_values_are_snake_case_strings(self) -> None:
        for right in CSDDDRight:
            assert right.value == right.value.lower()
            assert " " not in right.value

    def test_core_ilo_rights_present(self) -> None:
        assert CSDDDRight.CHILD_LABOUR in CSDDDRight
        assert CSDDDRight.FORCED_LABOUR in CSDDDRight
        assert CSDDDRight.FREEDOM_OF_ASSOCIATION in CSDDDRight
        assert CSDDDRight.COLLECTIVE_BARGAINING in CSDDDRight
        assert CSDDDRight.OCCUPATIONAL_SAFETY in CSDDDRight

    def test_environmental_rights_present(self) -> None:
        assert CSDDDRight.ENVIRONMENTAL_DESTRUCTION in CSDDDRight
        assert CSDDDRight.HARMFUL_CHEMICALS in CSDDDRight
        assert CSDDDRight.BIODIVERSITY in CSDDDRight
        assert CSDDDRight.MERCURY in CSDDDRight
        assert CSDDDRight.HAZARDOUS_WASTE in CSDDDRight

    def test_social_rights_present(self) -> None:
        assert CSDDDRight.LAND_RIGHTS in CSDDDRight
        assert CSDDDRight.WATER_RIGHTS in CSDDDRight
        assert CSDDDRight.PRIVACY in CSDDDRight
        assert CSDDDRight.MODERN_SLAVERY in CSDDDRight
        assert CSDDDRight.MIGRANT_WORKER_RIGHTS in CSDDDRight
        assert CSDDDRight.COMMUNITY_RIGHTS in CSDDDRight

    def test_string_coercion(self) -> None:
        assert CSDDDRight("child_labour") is CSDDDRight.CHILD_LABOUR
        assert CSDDDRight("forced_labour") is CSDDDRight.FORCED_LABOUR

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            CSDDDRight("not_a_right")

    def test_no_duplicate_values(self) -> None:
        values = [r.value for r in CSDDDRight]
        assert len(values) == len(set(values))


class TestScenarioType:
    def test_has_exactly_6_types(self) -> None:
        assert len(ScenarioType) == 6

    def test_expected_types_present(self) -> None:
        assert ScenarioType.GEOPOLITICAL_CONFLICT in ScenarioType
        assert ScenarioType.SANCTIONS_ESCALATION in ScenarioType
        assert ScenarioType.NATURAL_DISASTER in ScenarioType
        assert ScenarioType.REGULATORY_CHANGE in ScenarioType
        assert ScenarioType.LABOUR_UNREST in ScenarioType
        assert ScenarioType.SUPPLY_SHORTAGE in ScenarioType

    def test_string_coercion(self) -> None:
        assert ScenarioType("geopolitical_conflict") is ScenarioType.GEOPOLITICAL_CONFLICT

    def test_no_duplicate_values(self) -> None:
        values = [s.value for s in ScenarioType]
        assert len(values) == len(set(values))


class TestCalibrationStatus:
    def test_has_three_states(self) -> None:
        assert len(CalibrationStatus) == 3

    def test_expected_states(self) -> None:
        assert CalibrationStatus.PENDING.value == "pending"
        assert CalibrationStatus.APPROVED.value == "approved"
        assert CalibrationStatus.REJECTED.value == "rejected"


class TestScenarioSuggestionStatus:
    def test_has_three_states(self) -> None:
        assert len(ScenarioSuggestionStatus) == 3

    def test_expected_states(self) -> None:
        assert ScenarioSuggestionStatus.PENDING.value == "pending"
        assert ScenarioSuggestionStatus.ACTIVE.value == "active"
        assert ScenarioSuggestionStatus.DISMISSED.value == "dismissed"
