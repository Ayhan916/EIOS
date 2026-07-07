"""Tests for CSDDD Scenario Simulation Engine (TASK-003 Phase 5).

Critical invariants tested here:
  - Determinism: same input → same output, always (M43)
  - Clamping: output always in [1, 10]
  - Coverage: every scenario × every sector combination runs without error
  - Direction: factors > 1.0 never decrease a score
  - Isolation: base matrix is not mutated by simulation
"""

from __future__ import annotations

import pytest

from application.sector_intelligence.simulation_engine import (
    _SCENARIO_TEMPLATES,
    ScenarioSimulationEngine,
)
from domain.enums import CSDDDRight, ScenarioType
from domain.sector_risk_register import SimulationResult


@pytest.fixture
def engine() -> ScenarioSimulationEngine:
    return ScenarioSimulationEngine()


class TestDeterminism:
    """M43 compliance: simulation must be reproducible and auditable."""

    def test_same_input_same_output(self, engine: ScenarioSimulationEngine) -> None:
        r1 = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        r2 = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        assert r1.scenario_scores == r2.scenario_scores

    def test_all_scenarios_deterministic(self, engine: ScenarioSimulationEngine) -> None:
        for scenario in ScenarioType:
            r1 = engine.simulate("13", scenario)
            r2 = engine.simulate("13", scenario)
            assert r1.scenario_scores == r2.scenario_scores, (
                f"Simulation not deterministic for scenario {scenario.value}"
            )

    def test_different_sectors_give_different_results(
        self, engine: ScenarioSimulationEngine
    ) -> None:
        r_automotive = engine.simulate("29", ScenarioType.LABOUR_UNREST)
        r_textiles = engine.simulate("13", ScenarioType.LABOUR_UNREST)
        # Textiles has higher baseline, so scenario scores should differ
        assert r_automotive.scenario_scores != r_textiles.scenario_scores

    def test_explanation_text_is_static(self, engine: ScenarioSimulationEngine) -> None:
        r1 = engine.simulate("29", ScenarioType.NATURAL_DISASTER)
        r2 = engine.simulate("29", ScenarioType.NATURAL_DISASTER)
        assert r1.explanation == r2.explanation


class TestScoreClamping:
    def test_all_scores_in_range_1_to_10(self, engine: ScenarioSimulationEngine) -> None:
        for scenario in ScenarioType:
            result = engine.simulate("13", scenario)  # textiles: high baseline
            for right, score in result.scenario_scores.items():
                assert 1 <= score <= 10, (
                    f"{scenario.value} / {right.value}: scenario score {score} out of range"
                )

    def test_high_baseline_never_exceeds_10(self, engine: ScenarioSimulationEngine) -> None:
        # Textiles child labour baseline=8, forced labour=9
        result = engine.simulate("13", ScenarioType.SUPPLY_SHORTAGE)
        assert result.scenario_scores[CSDDDRight.FORCED_LABOUR] == 10
        assert result.scenario_scores[CSDDDRight.CHILD_LABOUR] <= 10

    def test_low_baseline_never_goes_below_1(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("62", ScenarioType.GEOPOLITICAL_CONFLICT)
        for score in result.scenario_scores.values():
            assert score >= 1


class TestFactorDirection:
    def test_factors_above_1_never_decrease_score(self, engine: ScenarioSimulationEngine) -> None:
        for scenario in ScenarioType:
            template = _SCENARIO_TEMPLATES[scenario]
            result = engine.simulate("29", scenario)
            for right, factor in template.factors.items():
                if factor > 1.0:
                    assert result.delta[right] >= 0, (
                        f"{scenario.value} / {right.value}: factor {factor} but delta is negative"
                    )

    def test_unaffected_rights_have_zero_delta(self, engine: ScenarioSimulationEngine) -> None:
        template = _SCENARIO_TEMPLATES[ScenarioType.GEOPOLITICAL_CONFLICT]
        result = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        for right in CSDDDRight:
            if right not in template.factors:
                assert result.delta[right] == 0, (
                    f"{right.value} not in factors but has non-zero delta"
                )

    def test_factor_1_0_unchanged(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("29", ScenarioType.SANCTIONS_ESCALATION)
        template = _SCENARIO_TEMPLATES[ScenarioType.SANCTIONS_ESCALATION]
        from application.sector_intelligence.base_matrix import get_scores

        baseline = get_scores("29")
        for right in CSDDDRight:
            if right not in template.factors:
                assert result.scenario_scores[right] == baseline[right]


class TestResultStructure:
    def test_result_has_all_21_rights(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("29", ScenarioType.LABOUR_UNREST)
        assert len(result.baseline_scores) == 21
        assert len(result.scenario_scores) == 21
        assert len(result.delta) == 21
        assert len(result.explanation) == 21

    def test_delta_is_scenario_minus_baseline(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("29", ScenarioType.NATURAL_DISASTER)
        for right in CSDDDRight:
            expected_delta = result.scenario_scores[right] - result.baseline_scores[right]
            assert result.delta[right] == expected_delta

    def test_nace_code_zero_padded(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("1", ScenarioType.GEOPOLITICAL_CONFLICT)
        assert result.nace_2digit == "01"

    def test_sector_name_populated(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        assert result.sector_name
        assert "motor" in result.sector_name.lower() or "vehicle" in result.sector_name.lower()

    def test_scenario_name_populated(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        assert result.scenario_name
        assert len(result.scenario_name) > 3

    def test_simulated_at_is_iso_string(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        assert "T" in result.simulated_at  # ISO 8601 format
        assert (
            "+" in result.simulated_at or "Z" in result.simulated_at or "UTC" in result.simulated_at
        )

    def test_calibration_version_passed_through(self, engine: ScenarioSimulationEngine) -> None:
        from application.sector_intelligence.base_matrix import CALIBRATION_VERSION

        result = engine.simulate("29", ScenarioType.REGULATORY_CHANGE)
        assert result.calibration_version == CALIBRATION_VERSION


class TestBaseMatrixIsolation:
    def test_simulation_does_not_mutate_base_matrix(self, engine: ScenarioSimulationEngine) -> None:
        from application.sector_intelligence.base_matrix import get_score

        before = get_score("29", CSDDDRight.FORCED_LABOUR)
        engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        after = get_score("29", CSDDDRight.FORCED_LABOUR)
        assert before == after


class TestAllScenarios:
    """Every scenario must run for every calibrated sector without error."""

    @pytest.mark.parametrize("scenario", list(ScenarioType))
    @pytest.mark.parametrize("nace", ["01", "07", "13", "29", "49", "62"])
    def test_simulate_succeeds(
        self,
        engine: ScenarioSimulationEngine,
        nace: str,
        scenario: ScenarioType,
    ) -> None:
        result = engine.simulate(nace, scenario)
        assert isinstance(result, SimulationResult)
        assert result.nace_2digit == nace


class TestHelperMethods:
    def test_highest_risk_rights_returns_top_n(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("13", ScenarioType.SUPPLY_SHORTAGE)
        top = engine.highest_risk_rights(result, top_n=3)
        assert len(top) == 3
        scores = [s for _, s in top]
        assert scores == sorted(scores, reverse=True)

    def test_highest_risk_rights_default_top_5(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("13", ScenarioType.GEOPOLITICAL_CONFLICT)
        top = engine.highest_risk_rights(result)
        assert len(top) == 5

    def test_rights_above_threshold_correct(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("13", ScenarioType.SUPPLY_SHORTAGE)
        above = engine.rights_above_threshold(result, threshold=8)
        for _, score in above:
            assert score >= 8
        # verify none missing
        expected = [r for r, s in result.scenario_scores.items() if s >= 8]
        assert len(above) == len(expected)

    def test_simulate_all_scenarios_returns_6(self, engine: ScenarioSimulationEngine) -> None:
        all_results = engine.simulate_all_scenarios("29")
        assert len(all_results) == 6
        for scenario in ScenarioType:
            assert scenario in all_results

    def test_available_templates_returns_6(self, engine: ScenarioSimulationEngine) -> None:
        templates = engine.available_templates()
        assert len(templates) == 6


class TestM43Compliance:
    """Explicit M43 compliance tests: no LLM in simulate path."""

    def test_simulate_does_not_import_groq(self, engine: ScenarioSimulationEngine) -> None:
        import sys

        groq_loaded_before = "groq" in sys.modules or any("groq" in k for k in sys.modules)
        engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        # If Groq was not loaded before, it must not be loaded after
        if not groq_loaded_before:
            groq_loaded_after = any("groq" in k for k in sys.modules)
            assert not groq_loaded_after, "simulate() must not invoke Groq LLM"

    def test_simulate_result_is_fully_explainable(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
        for right, text in result.explanation.items():
            assert isinstance(text, str)
            assert len(text) > 10, f"Explanation for {right.value} is too short"

    def test_integer_arithmetic_only(self, engine: ScenarioSimulationEngine) -> None:
        result = engine.simulate("29", ScenarioType.REGULATORY_CHANGE)
        for score in result.scenario_scores.values():
            assert isinstance(score, int)
        for delta in result.delta.values():
            assert isinstance(delta, int)
