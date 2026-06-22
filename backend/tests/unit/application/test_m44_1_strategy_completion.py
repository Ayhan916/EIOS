"""M44.1 — Strategy Intelligence Completion: Unit Tests.

9 test classes covering all new services:
  TestStrategyTemplates, TestStressTestTemplates,
  TestStrategyMethodologies, TestScenarioComparison,
  TestAutomaticBaselineResolution, TestForecastWindowPolicy,
  TestQuarterlyMilestones, TestStrategyRollups, TestReportEnhancements
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from application.strategy.digital_twin_service import StrategyError


def _now():
    return datetime.now(timezone.utc)


def _uid():
    return str(uuid.uuid4())


def _make_model(**kwargs):
    """Create a SimpleNamespace pretending to be an ORM model row."""
    defaults = {
        "id": _uid(),
        "organization_id": "org-test",
        "status": "Draft",
        "version": 1,
        "owner": None,
        "created_by": "actor-1",
        "updated_by": "actor-1",
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _mock_session():
    s = MagicMock()
    s.add = MagicMock()
    s.flush = MagicMock()
    return s


# ── TestStrategyTemplates ─────────────────────────────────────────────────────

class TestStrategyTemplates:
    def test_create_scenario_template_valid(self):
        from application.strategy import template_service
        session = _mock_session()
        with patch("application.strategy.template_service.emit_audit_event"):
            rec = template_service.create_scenario_template(
                "org-1", "Net Zero Template", "NET_ZERO", "CLIMATE", "actor-1", session,
                description="Standard NZ scenario",
                default_assumptions={"emissions_growth_pct_annual": -2.0},
                default_time_horizon_years=10,
            )
        assert rec.template_name == "Net Zero Template"
        assert rec.template_type == "NET_ZERO"
        assert rec.scenario_type == "CLIMATE"
        assert rec.usage_count == 0
        assert rec.is_approved is False

    def test_create_scenario_template_invalid_type(self):
        from application.strategy import template_service
        session = _mock_session()
        with pytest.raises(StrategyError, match="Invalid template_type"):
            template_service.create_scenario_template(
                "org-1", "Bad Template", "NOT_VALID", "CLIMATE", "actor-1", session,
            )

    def test_create_scenario_template_invalid_scenario_type(self):
        from application.strategy import template_service
        session = _mock_session()
        with pytest.raises(StrategyError, match="Invalid scenario_type"):
            template_service.create_scenario_template(
                "org-1", "T", "NET_ZERO", "NONSENSE", "actor-1", session,
            )

    def test_list_scenario_templates(self):
        from application.strategy import template_service
        t1 = _make_model(template_name="T1", template_type="NET_ZERO",
                         scenario_type="CLIMATE", usage_count=0, is_approved=False,
                         default_assumptions={}, default_time_horizon_years=5)
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [t1]
        result = template_service.list_scenario_templates("org-test", session)
        assert len(result) == 1
        assert result[0].template_name == "T1"

    def test_instantiate_from_template_increments_usage(self):
        from application.strategy import template_service
        template = _make_model(
            organization_id="org-1",
            template_name="T", template_type="NET_ZERO",
            scenario_type="CLIMATE", usage_count=3, is_approved=True,
            default_assumptions={"emissions_growth_pct_annual": -1.5},
            default_time_horizon_years=5,
        )
        session = _mock_session()
        session.get.return_value = template

        created_scenario = _make_model(organization_id="org-1", name="Test",
                                       scenario_type="CLIMATE", scenario_status="Draft",
                                       time_horizon_years=5, created_by_user="actor-1",
                                       is_template=False)
        with patch("application.strategy.scenario_service.create_scenario", return_value=created_scenario), \
             patch("application.strategy.scenario_service.create_assumption"), \
             patch("application.strategy.template_service.emit_audit_event"):
            result = template_service.instantiate_from_template(
                "org-1", template.id, "My Scenario", "actor-1", session,
            )

        assert template.usage_count == 4
        assert result.name == "Test"


# ── TestStressTestTemplates ───────────────────────────────────────────────────

class TestStressTestTemplates:
    def test_create_stress_test_template_valid(self):
        from application.strategy import template_service
        session = _mock_session()
        with patch("application.strategy.template_service.emit_audit_event"):
            rec = template_service.create_stress_test_template(
                "org-1", "Climate Shock Template", "CLIMATE", "actor-1", session,
                severity_level="HIGH",
                default_assumptions={"carbon_price_shock_pct": 50.0},
            )
        assert rec.template_name == "Climate Shock Template"
        assert rec.template_type == "CLIMATE"
        assert rec.severity_level == "HIGH"
        assert rec.usage_count == 0

    def test_create_stress_test_template_invalid_type(self):
        from application.strategy import template_service
        session = _mock_session()
        with pytest.raises(StrategyError, match="Invalid template_type"):
            template_service.create_stress_test_template(
                "org-1", "T", "NOT_REAL", "actor-1", session,
            )

    def test_create_stress_test_template_invalid_severity(self):
        from application.strategy import template_service
        session = _mock_session()
        with pytest.raises(StrategyError, match="Invalid severity_level"):
            template_service.create_stress_test_template(
                "org-1", "T", "CLIMATE", "actor-1", session, severity_level="CATASTROPHIC",
            )

    def test_list_stress_test_templates(self):
        from application.strategy import template_service
        t1 = _make_model(template_name="T1", template_type="CLIMATE",
                         severity_level="MEDIUM", usage_count=0,
                         default_assumptions={}, methodology=None)
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [t1]
        result = template_service.list_stress_test_templates("org-test", session)
        assert len(result) == 1

    def test_all_template_types_valid(self):
        from application.strategy import template_service
        for ttype in ("CLIMATE", "FINANCIAL", "REGULATORY", "SUPPLY_CHAIN"):
            session = _mock_session()
            with patch("application.strategy.template_service.emit_audit_event"):
                rec = template_service.create_stress_test_template(
                    "org-1", f"{ttype} Template", ttype, "actor-1", session,
                )
            assert rec.template_type == ttype


# ── TestStrategyMethodologies ─────────────────────────────────────────────────

class TestStrategyMethodologies:
    def test_create_methodology(self):
        from application.strategy import methodology_service
        session = _mock_session()
        with patch("application.strategy.methodology_service.emit_audit_event"):
            rec = methodology_service.create_methodology(
                "org-1", "SBTi-Aligned", "actor-1", session,
                methodology_version="2.0.0",
                formula_description="Linear reduction from 2024 base",
                applicable_to=["FORECAST", "PATHWAY"],
            )
        assert rec.methodology_name == "SBTi-Aligned"
        assert rec.approval_status == "DRAFT"
        assert rec.approved_by is None
        assert rec.applicable_to == {"types": ["FORECAST", "PATHWAY"]}

    def test_approve_methodology(self):
        from application.strategy import methodology_service
        methodology = _make_model(
            organization_id="org-1",
            methodology_name="M1", methodology_version="1.0.0",
            approval_status="DRAFT", approved_by=None, approved_at=None,
            formula_description=None, assumptions={}, applicable_to={"types": []},
        )
        session = _mock_session()
        session.get.return_value = methodology
        with patch("application.strategy.methodology_service.emit_audit_event"):
            result = methodology_service.approve_methodology("org-1", methodology.id, "actor-1", session)
        assert result.approval_status == "APPROVED"
        assert result.approved_by == "actor-1"
        assert result.approved_at is not None

    def test_approve_deprecated_methodology_raises(self):
        from application.strategy import methodology_service
        methodology = _make_model(
            organization_id="org-1",
            methodology_name="M1", methodology_version="1.0.0",
            approval_status="DEPRECATED", approved_by=None, approved_at=None,
            formula_description=None, assumptions={}, applicable_to={"types": []},
        )
        session = _mock_session()
        session.get.return_value = methodology
        with pytest.raises(StrategyError, match="Cannot approve a deprecated"):
            methodology_service.approve_methodology("org-1", methodology.id, "actor-1", session)

    def test_deprecate_methodology(self):
        from application.strategy import methodology_service
        methodology = _make_model(
            organization_id="org-1",
            methodology_name="M1", methodology_version="1.0.0",
            approval_status="APPROVED", approved_by="actor-1", approved_at=_now(),
            formula_description=None, assumptions={}, applicable_to={"types": []},
        )
        session = _mock_session()
        session.get.return_value = methodology
        with patch("application.strategy.methodology_service.emit_audit_event"):
            result = methodology_service.deprecate_methodology("org-1", methodology.id, "actor-1", session)
        assert result.approval_status == "DEPRECATED"

    def test_list_methodologies(self):
        from application.strategy import methodology_service
        m1 = _make_model(methodology_name="M1", methodology_version="1.0",
                         approval_status="DRAFT", approved_by=None, approved_at=None,
                         formula_description=None, assumptions={}, applicable_to={"types": []})
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [m1]
        result = methodology_service.list_methodologies("org-test", session)
        assert len(result) == 1


# ── TestScenarioComparison ────────────────────────────────────────────────────

class TestScenarioComparison:
    def _make_execution(self, org_id, scenario_id, kpis=None, risks=None, emissions=None, financial=None):
        return _make_model(
            organization_id=org_id,
            scenario_id=scenario_id,
            twin_id=None,
            execution_status="Completed",
            executed_at=_now(),
            projected_kpis=kpis or {"revenue": 1000.0, "carbon_cost": 50.0},
            projected_risks=risks or {"risk_score": 5.0},
            projected_emissions=emissions or {"emissions_tco2e": 200.0},
            projected_financial=financial or {"revenue": 1000.0, "carbon_cost": 50.0},
            execution_metadata={},
            is_final=False,
        )

    def test_compare_two_scenarios(self):
        from application.strategy import comparison_service
        sid1, sid2 = _uid(), _uid()
        exec1 = self._make_execution("org-1", sid1,
                                     kpis={"revenue": 1000.0},
                                     emissions={"emissions_tco2e": 200.0},
                                     risks={"risk_score": 5.0},
                                     financial={"revenue": 1000.0})
        exec2 = self._make_execution("org-1", sid2,
                                     kpis={"revenue": 1200.0},
                                     emissions={"emissions_tco2e": 180.0},
                                     risks={"risk_score": 4.5},
                                     financial={"revenue": 1200.0})
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [exec1, exec2]
        with patch("application.strategy.comparison_service.emit_audit_event"):
            result = comparison_service.compare_scenarios("org-1", "Comparison A", [sid1, sid2], "actor-1", session)
        assert result.comparison_name == "Comparison A"
        assert sid2 in result.emissions_delta
        assert result.emissions_delta[sid2]["emissions_tco2e_delta"] == pytest.approx(-20.0, abs=0.1)

    def test_compare_too_few_scenarios_raises(self):
        from application.strategy import comparison_service
        session = _mock_session()
        with pytest.raises(StrategyError, match="at least 2"):
            comparison_service.compare_scenarios("org-1", "C", [_uid()], "actor-1", session)

    def test_compare_too_many_scenarios_raises(self):
        from application.strategy import comparison_service
        session = _mock_session()
        with pytest.raises(StrategyError, match="at most 10"):
            comparison_service.compare_scenarios("org-1", "C", [_uid()] * 11, "actor-1", session)

    def test_compare_insufficient_executions_raises(self):
        from application.strategy import comparison_service
        sid1, sid2 = _uid(), _uid()
        session = _mock_session()
        exec1 = self._make_execution("org-1", sid1)
        session.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [exec1, None]
        with pytest.raises(StrategyError, match="At least 2 scenarios must have"):
            comparison_service.compare_scenarios("org-1", "C", [sid1, sid2], "actor-1", session)

    def test_kpi_delta_computed_correctly(self):
        from application.strategy import comparison_service
        sid1, sid2 = _uid(), _uid()
        exec1 = self._make_execution("org-1", sid1,
                                     kpis={"revenue": 500.0},
                                     emissions={"emissions_tco2e": 100.0},
                                     risks={"risk_score": 3.0},
                                     financial={"revenue": 500.0})
        exec2 = self._make_execution("org-1", sid2,
                                     kpis={"revenue": 700.0},
                                     emissions={"emissions_tco2e": 90.0},
                                     risks={"risk_score": 2.5},
                                     financial={"revenue": 700.0})
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [exec1, exec2]
        with patch("application.strategy.comparison_service.emit_audit_event"):
            result = comparison_service.compare_scenarios("org-1", "C", [sid1, sid2], "actor-1", session)
        assert result.kpi_delta[sid2]["revenue"] == pytest.approx(200.0, abs=0.01)
        assert result.risk_delta[sid2]["risk_score_delta"] == pytest.approx(-0.5, abs=0.01)
        assert result.value_delta[sid2]["revenue_delta"] == pytest.approx(200.0, abs=0.01)


# ── TestAutomaticBaselineResolution ───────────────────────────────────────────

class TestAutomaticBaselineResolution:
    def test_resolve_with_override(self):
        from application.strategy.scenario_service import resolve_strategy_baseline
        session = _mock_session()
        override = {"emissions_tco2e": 500.0, "revenue": 10000.0}
        result = resolve_strategy_baseline("org-1", session, baseline_override=override)
        assert result == override
        session.query.assert_not_called()

    def test_resolve_with_twin_baseline_fallback(self):
        from application.strategy.scenario_service import resolve_strategy_baseline
        twin = _make_model(
            organization_id="org-1", name="T", is_active=True, is_final=False,
            emissions_baseline_tco2e=1500.0,
            financial_baseline={"revenue": 50000.0},
        )
        session = _mock_session()
        # First call → twin; second call → no snapshot
        session.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [twin, None]
        result = resolve_strategy_baseline("org-1", session)
        assert result.get("emissions_tco2e") == 1500.0
        assert result.get("revenue") == 50000.0

    def test_resolve_with_finalized_snapshot(self):
        from application.strategy.scenario_service import resolve_strategy_baseline
        twin = _make_model(organization_id="org-1", name="T", is_active=True, is_final=False,
                           emissions_baseline_tco2e=None, financial_baseline=None)
        snapshot = _make_model(
            organization_id="org-1", twin_id=twin.id, snapshot_type="ANNUAL",
            snapshot_period="2024", is_final=True, captured_at=_now(),
            sustainability_state={"emissions_tco2e": 800.0},
            financial_esg_state={"revenue": 20000.0},
        )
        session = _mock_session()
        # First call → twin; second call → snapshot
        session.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [twin, snapshot]
        result = resolve_strategy_baseline("org-1", session)
        # Snapshot fields merged: sustainability_state + financial_esg_state
        assert "emissions_tco2e" in result or "revenue" in result

    def test_resolve_no_twin_raises(self):
        from application.strategy.scenario_service import resolve_strategy_baseline
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        with pytest.raises(StrategyError, match="No baseline found"):
            resolve_strategy_baseline("org-1", session)


# ── TestForecastWindowPolicy ──────────────────────────────────────────────────

class TestForecastWindowPolicy:
    def _make_policy(self, org_id, min_w, max_w, default_w, name="P1"):
        return _make_model(
            organization_id=org_id,
            policy_name=name,
            min_window=min_w,
            max_window=max_w,
            default_window=default_w,
            applicable_methodology="WEIGHTED_MOVING_AVERAGE",
            is_active=True,
        )

    def test_validate_window_within_bounds(self):
        from application.strategy.forecast_service import validate_wma_window
        policy = self._make_policy("org-1", 2, 10, 5)
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = policy
        validate_wma_window("org-1", 5, session)  # should not raise

    def test_validate_window_below_min_raises(self):
        from application.strategy.forecast_service import validate_wma_window
        policy = self._make_policy("org-1", 3, 10, 5)
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = policy
        with pytest.raises(StrategyError, match="below minimum"):
            validate_wma_window("org-1", 1, session)

    def test_validate_window_above_max_raises(self):
        from application.strategy.forecast_service import validate_wma_window
        policy = self._make_policy("org-1", 2, 8, 5)
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = policy
        with pytest.raises(StrategyError, match="exceeds maximum"):
            validate_wma_window("org-1", 12, session)

    def test_no_policy_allows_any_window(self):
        from application.strategy.forecast_service import validate_wma_window
        session = _mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        validate_wma_window("org-1", 999, session)  # should not raise

    def test_create_window_policy_valid(self):
        from application.strategy.forecast_service import create_forecast_window_policy
        session = _mock_session()
        rec = create_forecast_window_policy(
            "org-1", "WMA Policy", 2, 12, 6, "actor-1", session
        )
        assert rec.min_window == 2
        assert rec.max_window == 12
        assert rec.default_window == 6
        assert rec.is_active is True

    def test_create_window_policy_invalid_range_raises(self):
        from application.strategy.forecast_service import create_forecast_window_policy
        session = _mock_session()
        with pytest.raises(StrategyError, match="max_window"):
            create_forecast_window_policy("org-1", "P", 10, 5, 7, "actor-1", session)

    def test_create_window_policy_default_out_of_range_raises(self):
        from application.strategy.forecast_service import create_forecast_window_policy
        session = _mock_session()
        with pytest.raises(StrategyError, match="default_window"):
            create_forecast_window_policy("org-1", "P", 2, 10, 15, "actor-1", session)


# ── TestQuarterlyMilestones ───────────────────────────────────────────────────

class TestQuarterlyMilestones:
    def test_annual_milestones_v2(self):
        from application.strategy.pathway_service import _compute_milestones_v2
        result = _compute_milestones_v2(1000.0, 0.0, 2024, 2034, frequency="ANNUAL")
        assert len(result) == 10  # one per year
        assert result[0]["frequency"] == "ANNUAL"
        assert result[-1]["emissions_tco2e"] == pytest.approx(0.0, abs=1.0)

    def test_quarterly_milestones_count(self):
        from application.strategy.pathway_service import _compute_milestones_v2
        result = _compute_milestones_v2(1000.0, 0.0, 2024, 2029, frequency="QUARTERLY")
        assert len(result) == 20  # 5 years × 4 quarters
        assert result[0]["frequency"] == "QUARTERLY"
        assert "Q" in result[0]["period"]

    def test_semiannual_milestones_count(self):
        from application.strategy.pathway_service import _compute_milestones_v2
        result = _compute_milestones_v2(1000.0, 0.0, 2024, 2029, frequency="SEMIANNUAL")
        assert len(result) == 10  # 5 years × 2 halves
        assert "H" in result[0]["period"]

    def test_linear_reduction_preserved(self):
        from application.strategy.pathway_service import _compute_milestones_v2
        result = _compute_milestones_v2(100.0, 0.0, 2024, 2026, frequency="ANNUAL")
        assert result[0]["emissions_tco2e"] == pytest.approx(50.0, abs=1.0)
        assert result[1]["emissions_tco2e"] == pytest.approx(0.0, abs=1.0)

    def test_create_pathway_with_quarterly_frequency(self):
        from application.strategy import pathway_service
        from datetime import datetime as _dt, timezone as _tz
        session = _mock_session()
        current_year = _dt.now(_tz.utc).year
        target_year = current_year + 2
        with patch("application.strategy.pathway_service.emit_audit_event"):
            rec = pathway_service.create_pathway(
                "org-1", "Quarterly Pathway", "EXPECTED", target_year, "actor-1", session,
                baseline_emissions_tco2e=1000.0,
                target_emissions_tco2e=0.0,
                milestone_frequency="QUARTERLY",
            )
        assert rec.milestone_frequency == "QUARTERLY"
        milestones = rec.milestones["milestones"]
        assert len(milestones) == 8  # 2 years × 4 quarters

    def test_create_pathway_default_annual_preserves_5_milestones(self):
        from application.strategy import pathway_service
        from datetime import datetime as _dt, timezone as _tz
        session = _mock_session()
        target_year = _dt.now(_tz.utc).year + 10
        with patch("application.strategy.pathway_service.emit_audit_event"):
            rec = pathway_service.create_pathway(
                "org-1", "Annual Pathway", "EXPECTED", target_year, "actor-1", session,
                baseline_emissions_tco2e=1000.0,
                target_emissions_tco2e=0.0,
                milestone_frequency="ANNUAL",
            )
        assert rec.milestone_frequency == "ANNUAL"
        assert len(rec.milestones["milestones"]) == 5  # backward compat: 5 milestones


# ── TestStrategyRollups ───────────────────────────────────────────────────────

class TestStrategyRollups:
    def test_rollup_includes_new_aggregates(self):
        from application.strategy.rollup_service import strategy_rollup
        session = _mock_session()
        session.query.return_value.filter.return_value.scalar.return_value = 0
        session.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0
        result = strategy_rollup("org-1", session)
        assert "avg_forecast_value" in result
        assert "avg_forecast_emissions" in result
        assert "avg_pathway_reduction_pct" in result
        assert "scenario_templates" in result
        assert "stress_test_templates" in result
        assert "strategy_methodologies" in result
        assert "scenario_comparisons" in result

    def test_rollup_all_keys_present(self):
        from application.strategy.rollup_service import strategy_rollup
        session = _mock_session()
        session.query.return_value.filter.return_value.scalar.return_value = 2
        session.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 1
        result = strategy_rollup("org-1", session)
        expected_keys = [
            "organization_id", "digital_twins", "scenarios", "scenario_executions",
            "climate_stress_tests", "financial_stress_tests", "total_stress_tests",
            "forecasts", "board_simulations", "transition_pathways", "finalized_reports",
            "avg_forecast_value", "avg_forecast_emissions", "avg_pathway_reduction_pct",
            "scenario_templates", "stress_test_templates", "strategy_methodologies", "scenario_comparisons",
        ]
        for k in expected_keys:
            assert k in result, f"Missing key: {k}"


# ── TestReportEnhancements ────────────────────────────────────────────────────

class TestReportEnhancements:
    def test_report_includes_methodology_appendix(self):
        from application.strategy import reporting_service
        session = _mock_session()
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        with patch("application.strategy.reporting_service.emit_audit_event"):
            rec = reporting_service.generate_strategic_report(
                "org-1", "Q2 Report", "2024-Q2", "actor-1", session,
            )
        assert rec.methodology_appendix is not None
        assert "forecast_methodologies" in rec.methodology_appendix
        assert rec.assumption_appendix is not None

    def test_forecast_summary_includes_trend_direction_improving(self):
        from application.strategy import reporting_service
        row = _make_model(
            organization_id="org-1",
            forecast_model_id=_uid(),
            forecast_type="EMISSIONS",
            target_metric="emissions_tco2e",
            forecast_year=2025,
            baseline_value=1000.0,
            forecast_value=800.0,
            lower_bound=700.0,
            upper_bound=900.0,
            confidence_level=0.85,
            scenario_id=None,
            is_final=False,
        )
        session = _mock_session()
        session.query.return_value.filter.return_value.all.return_value = [row]
        rec = reporting_service.generate_forecast_summary("org-1", "2024", "actor-1", session)
        assert rec.trend_direction == "IMPROVING"
        assert rec.forecast_delta is not None
        assert rec.forecast_delta < 0
        assert rec.scenario_confidence == pytest.approx(0.85, abs=0.01)

    def test_forecast_summary_stable_trend(self):
        from application.strategy import reporting_service
        row = _make_model(
            organization_id="org-1",
            forecast_model_id=_uid(),
            forecast_type="EMISSIONS",
            target_metric="emissions_tco2e",
            forecast_year=2025,
            baseline_value=1000.0,
            forecast_value=1001.0,
            lower_bound=990.0,
            upper_bound=1010.0,
            confidence_level=0.90,
            scenario_id=None,
            is_final=False,
        )
        session = _mock_session()
        session.query.return_value.filter.return_value.all.return_value = [row]
        rec = reporting_service.generate_forecast_summary("org-1", "2024", "actor-1", session)
        assert rec.trend_direction == "STABLE"
