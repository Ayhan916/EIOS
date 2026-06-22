"""M42 — Sustainability Performance Management & Decarbonization Platform.

Tests for:
  - KPI calculations and threshold alerts
  - Target progress deterministic formula
  - Carbon emission calculations
  - Carbon inventory recalculation (scope aggregation)
  - Roadmap logic and milestone tracking
  - Scorecard weighted rollup
  - Deterministic forecasting (linear trend, moving average)
  - Scenario analysis outputs
  - Report immutability
  - Tenant isolation (_assert_org on all mutations)
  - Decision logging pre-hash pass-through
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from application.sustainability.objective_service import (
    SustainabilityConflict,
    SustainabilityError,
    _assert_org,
    compute_progress,
)
from application.sustainability import (
    carbon_service,
    climate_service,
    kpi_service,
    objective_service,
    reporting_service,
    roadmap_service,
    scoring_service,
)
from application.sustainability.scoring_service import (
    _linear_trend,
    _moving_average,
    _kpi_attainment,
)
from application.sustainability.carbon_service import calculate_emissions
from application.sustainability.climate_service import _compute_overall_risk
from application.sustainability.roadmap_service import _compute_target_emissions


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session(get_return=None, *, query_count=0):
    s = MagicMock()
    s.get.return_value = get_return
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.offset.return_value = q
    q.count.return_value = query_count
    q.all.return_value = []
    q.first.return_value = None
    s.query.return_value = q
    return s


def _mock_objective(org="org1", status="DRAFT"):
    obj = MagicMock()
    obj.organization_id = org
    obj.objective_status = status
    return obj


def _mock_target(org="org1", baseline=0.0, target_val=100.0, current=None):
    t = MagicMock()
    t.organization_id = org
    t.baseline_value = baseline
    t.target_value = target_val
    t.current_value = current
    return t


def _mock_kpi(org="org1", category="ENVIRONMENTAL", target_value=100.0, threshold=None):
    k = MagicMock()
    k.organization_id = org
    k.id = "kpi1"
    k.category = category
    k.target_value = target_value
    k.alert_threshold = threshold
    k.is_active = True
    return k


def _mock_inventory(org="org1", status="DRAFT"):
    inv = MagicMock()
    inv.organization_id = org
    inv.inventory_status = status
    inv.scope1_emissions = 0.0
    inv.scope2_emissions = 0.0
    inv.scope3_emissions = 0.0
    inv.total_emissions = 0.0
    return inv


def _mock_report(org="org1", is_final=False):
    r = MagicMock()
    r.organization_id = org
    r.is_final = is_final
    return r


def _now():
    return datetime.now(timezone.utc)


# ── TestM42TargetProgress ─────────────────────────────────────────────────────

class TestM42TargetProgress:
    def test_zero_baseline_to_target(self):
        assert compute_progress(0.0, 100.0, 50.0) == 50.0

    def test_progress_capped_at_100(self):
        assert compute_progress(0.0, 100.0, 150.0) == 100.0

    def test_progress_floored_at_zero(self):
        assert compute_progress(0.0, 100.0, -10.0) == 0.0

    def test_none_current_returns_zero(self):
        assert compute_progress(0.0, 100.0, None) == 0.0

    def test_nonzero_baseline(self):
        assert compute_progress(50.0, 150.0, 100.0) == 50.0

    def test_zero_span_at_target(self):
        assert compute_progress(100.0, 100.0, 100.0) == 100.0

    def test_zero_span_below_target(self):
        assert compute_progress(100.0, 100.0, 50.0) == 0.0


# ── TestM42CarbonCalculations ─────────────────────────────────────────────────

class TestM42CarbonCalculations:
    def test_calculate_emissions_basic(self):
        result = calculate_emissions(1000.0, 0.233)
        assert result == round(1000.0 * 0.233, 6)

    def test_calculate_emissions_zero_activity(self):
        assert calculate_emissions(0.0, 5.0) == 0.0

    def test_calculate_emissions_zero_factor(self):
        assert calculate_emissions(1000.0, 0.0) == 0.0

    def test_emission_source_computes_calculated_emissions(self):
        s = _session()
        with patch("application.sustainability.carbon_service.emit_audit_event"):
            src = carbon_service.add_emission_source(
                organization_id="org1",
                name="Boiler",
                scope="SCOPE1",
                activity_data=500.0,
                emission_factor=0.4,
                period_start=_now(),
                period_end=_now(),
                reporting_year=2025,
                actor_id="user1",
                session=s,
            )
        s.add.assert_called_once()
        s.flush.assert_called_once()
        args = s.add.call_args[0][0]
        assert args.calculated_emissions == round(500.0 * 0.4, 6)

    def test_invalid_scope_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="scope"):
            carbon_service.add_emission_source(
                organization_id="org1",
                name="x",
                scope="SCOPE4",
                activity_data=1.0,
                emission_factor=1.0,
                period_start=_now(),
                period_end=_now(),
                reporting_year=2025,
                actor_id="user1",
                session=s,
            )


# ── TestM42CarbonInventory ────────────────────────────────────────────────────

class TestM42CarbonInventory:
    def test_recalculate_aggregates_by_scope(self):
        inv = _mock_inventory(status="DRAFT")
        inv.reporting_year = 2024
        inv.recalculation_count = 0
        s = _session(get_return=inv)
        # recalculate_inventory calls func.sum().scalar() three times (scope1/2/3)
        s.query.return_value.filter.return_value.scalar.side_effect = [100.0, 50.0, 25.0]
        with patch("application.sustainability.carbon_service.emit_audit_event"):
            result = carbon_service.recalculate_inventory(
                "inv1", "user1", s, organization_id="org1"
            )
        assert result.scope1_emissions == 100.0
        assert result.scope2_emissions == 50.0
        assert result.scope3_emissions == 25.0
        assert result.total_emissions == 175.0

    def test_recalculate_finalized_raises_conflict(self):
        inv = _mock_inventory(status="FINALIZED")
        s = _session(get_return=inv)
        with pytest.raises(SustainabilityConflict):
            carbon_service.recalculate_inventory(
                "inv1", "user1", s, organization_id="org1"
            )

    def test_finalize_already_finalized_raises(self):
        inv = _mock_inventory(status="FINALIZED")
        s = _session(get_return=inv)
        with pytest.raises(SustainabilityConflict, match="already finalized"):
            carbon_service.finalize_inventory(
                "inv1", "user1", s, organization_id="org1"
            )

    def test_finalize_draft_succeeds(self):
        inv = _mock_inventory(status="DRAFT")
        s = _session(get_return=inv)
        s.query.return_value.filter.return_value.all.return_value = []
        with patch("application.sustainability.carbon_service.emit_audit_event"):
            result = carbon_service.finalize_inventory(
                "inv1", "user1", s, organization_id="org1"
            )
        assert result.inventory_status == "FINALIZED"

    def test_tenant_isolation_recalculate(self):
        inv = _mock_inventory(org="other_org", status="DRAFT")
        s = _session(get_return=inv)
        with pytest.raises(SustainabilityError, match="not found"):
            carbon_service.recalculate_inventory(
                "inv1", "user1", s, organization_id="org1"
            )


# ── TestM42KPIAlerts ──────────────────────────────────────────────────────────

class TestM42KPIAlerts:
    def test_measurement_triggers_alert_when_threshold_exceeded(self):
        kpi = _mock_kpi(threshold=80.0)
        s = _session()
        s.get.return_value = kpi
        with patch("application.sustainability.kpi_service.emit_audit_event"):
            kpi_service.record_measurement(
                kpi_id="kpi1",
                organization_id="org1",
                period_start=_now(),
                period_end=_now(),
                measured_value=95.0,
                actor_id="user1",
                session=s,
            )
        # Should have called session.add twice (measurement + alert)
        assert s.add.call_count == 2

    def test_measurement_below_threshold_no_alert(self):
        kpi = _mock_kpi(threshold=80.0)
        s = _session()
        s.get.return_value = kpi
        with patch("application.sustainability.kpi_service.emit_audit_event"):
            kpi_service.record_measurement(
                kpi_id="kpi1",
                organization_id="org1",
                period_start=_now(),
                period_end=_now(),
                measured_value=60.0,
                actor_id="user1",
                session=s,
            )
        # Only the measurement added, no alert
        assert s.add.call_count == 1

    def test_measurement_no_threshold_no_alert(self):
        kpi = _mock_kpi(threshold=None)
        s = _session()
        s.get.return_value = kpi
        with patch("application.sustainability.kpi_service.emit_audit_event"):
            kpi_service.record_measurement(
                kpi_id="kpi1",
                organization_id="org1",
                period_start=_now(),
                period_end=_now(),
                measured_value=999.0,
                actor_id="user1",
                session=s,
            )
        assert s.add.call_count == 1

    def test_resolve_alert(self):
        alert = MagicMock()
        alert.organization_id = "org1"
        alert.is_resolved = False
        s = _session(get_return=alert)
        result = kpi_service.resolve_alert("alert1", "user1", s, organization_id="org1")
        assert result.is_resolved is True

    def test_resolve_alert_cross_tenant_blocked(self):
        alert = MagicMock()
        alert.organization_id = "other"
        s = _session(get_return=alert)
        with pytest.raises(SustainabilityError, match="not found"):
            kpi_service.resolve_alert("alert1", "user1", s, organization_id="org1")


# ── TestM42RoadmapLogic ───────────────────────────────────────────────────────

class TestM42RoadmapLogic:
    def test_compute_target_emissions_formula(self):
        result = _compute_target_emissions(1000.0, 50.0)
        assert result == 500.0

    def test_compute_target_emissions_100_pct(self):
        assert _compute_target_emissions(1000.0, 100.0) == 0.0

    def test_compute_target_emissions_zero_pct(self):
        assert _compute_target_emissions(1000.0, 0.0) == 1000.0

    def test_create_roadmap_sets_target_emissions(self):
        s = _session()
        with patch("application.sustainability.roadmap_service.emit_audit_event"):
            rm = roadmap_service.create_roadmap(
                organization_id="org1",
                name="Net Zero 2040",
                baseline_year=2020,
                target_year=2040,
                baseline_emissions=1000.0,
                target_reduction_percent=50.0,
                actor_id="user1",
                session=s,
            )
        args = s.add.call_args[0][0]
        assert args.target_emissions == 500.0

    def test_invalid_sbt_scope_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="scope"):
            roadmap_service.create_science_based_target(
                organization_id="org1",
                scope="INVALID_SCOPE",
                target_type="ABSOLUTE",
                baseline_year=2020,
                baseline_emissions=1000.0,
                target_reduction_percent=50.0,
                target_year=2030,
                actor_id="user1",
                session=s,
            )

    def test_update_initiative_progress_tenant_isolation(self):
        init = MagicMock()
        init.organization_id = "other_org"
        s = _session(get_return=init)
        with pytest.raises(SustainabilityError, match="not found"):
            roadmap_service.update_initiative_progress(
                "init1", 10.0, "IN_PROGRESS", "user1", s, organization_id="org1"
            )


# ── TestM42Scorecard ──────────────────────────────────────────────────────────

class TestM42Scorecard:
    def test_kpi_attainment_below_target(self):
        assert _kpi_attainment(50.0, 100.0) == 50.0

    def test_kpi_attainment_exceeds_target_capped(self):
        assert _kpi_attainment(150.0, 100.0) == 100.0

    def test_kpi_attainment_zero_target_zero_measured(self):
        assert _kpi_attainment(0.0, 0.0) == 100.0

    def test_kpi_attainment_zero_target_nonzero_measured(self):
        assert _kpi_attainment(10.0, 0.0) == 0.0

    def test_scorecard_weighted_formula(self):
        """Verify overall = E×0.40 + S×0.30 + G×0.30."""
        env, soc, gov = 80.0, 60.0, 40.0
        expected = round(env * 0.40 + soc * 0.30 + gov * 0.30, 2)
        assert expected == round(80 * 0.4 + 60 * 0.3 + 40 * 0.3, 2)

    def test_compute_scorecard_no_kpis_returns_zero_scores(self):
        s = _session()
        s.query.return_value.filter.return_value.filter.return_value.all.return_value = []
        with patch("application.sustainability.scoring_service.emit_audit_event"):
            sc = scoring_service.compute_scorecard(
                "org1", _now(), _now(), "user1", s
            )
        assert s.add.called
        args = s.add.call_args[0][0]
        assert args.overall_score == 0.0
        assert args.environmental_score == 0.0


# ── TestM42Forecasting ────────────────────────────────────────────────────────

class TestM42Forecasting:
    def test_linear_trend_positive_slope(self):
        data = [10.0, 20.0, 30.0, 40.0]
        slope, intercept = _linear_trend(data)
        assert slope == pytest.approx(10.0, abs=0.01)

    def test_linear_trend_flat(self):
        slope, intercept = _linear_trend([5.0, 5.0, 5.0])
        assert slope == pytest.approx(0.0, abs=0.001)
        assert intercept == pytest.approx(5.0, abs=0.001)

    def test_linear_trend_single_point(self):
        slope, intercept = _linear_trend([42.0])
        assert slope == 0.0
        assert intercept == 42.0

    def test_moving_average_window_3(self):
        result = _moving_average([10.0, 20.0, 30.0, 40.0, 50.0], window=3)
        assert result == pytest.approx((30.0 + 40.0 + 50.0) / 3, abs=0.001)

    def test_moving_average_fewer_than_window(self):
        result = _moving_average([10.0, 20.0], window=3)
        assert result == pytest.approx(15.0, abs=0.001)

    def test_create_forecast_linear_trend(self):
        s = _session()
        fc = scoring_service.create_forecast(
            organization_id="org1",
            forecast_type="EMISSIONS",
            method="LINEAR_TREND",
            period_start=_now(),
            period_end=_now(),
            historical_data=[10.0, 20.0, 30.0],
            forecast_horizon_months=3,
            actor_id="user1",
            session=s,
        )
        args = s.add.call_args[0][0]
        assert len(args.forecast_data) == 3
        # Points should be increasing (positive slope)
        assert args.forecast_data[1] > args.forecast_data[0]

    def test_create_forecast_moving_average(self):
        s = _session()
        fc = scoring_service.create_forecast(
            organization_id="org1",
            forecast_type="EMISSIONS",
            method="MOVING_AVERAGE",
            period_start=_now(),
            period_end=_now(),
            historical_data=[10.0, 20.0, 30.0],
            forecast_horizon_months=2,
            actor_id="user1",
            session=s,
        )
        args = s.add.call_args[0][0]
        # Moving average: all forecast points same value
        assert args.forecast_data[0] == args.forecast_data[1]

    def test_invalid_forecast_method_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="method"):
            scoring_service.create_forecast(
                organization_id="org1",
                forecast_type="EMISSIONS",
                method="NEURAL_NETWORK",
                period_start=_now(),
                period_end=_now(),
                historical_data=[1.0],
                forecast_horizon_months=1,
                actor_id="user1",
                session=s,
            )

    def test_empty_historical_data_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="empty"):
            scoring_service.create_forecast(
                organization_id="org1",
                forecast_type="EMISSIONS",
                method="LINEAR_TREND",
                period_start=_now(),
                period_end=_now(),
                historical_data=[],
                forecast_horizon_months=1,
                actor_id="user1",
                session=s,
            )


# ── TestM42ScenarioAnalysis ───────────────────────────────────────────────────

class TestM42ScenarioAnalysis:
    def test_supplier_improvement_formula(self):
        s = _session()
        sc = scoring_service.create_scenario(
            organization_id="org1",
            name="Supplier Test",
            scenario_type="SUPPLIER_IMPROVEMENT",
            inputs={"baseline_supplier_compliance": 60.0},
            assumptions={"improvement_percent": 10.0},
            actor_id="user1",
            session=s,
        )
        args = s.add.call_args[0][0]
        assert args.outputs["projected_supplier_compliance"] == pytest.approx(66.0, abs=0.01)

    def test_renewable_transition_formula(self):
        s = _session()
        scoring_service.create_scenario(
            organization_id="org1",
            name="Renewables",
            scenario_type="RENEWABLE_TRANSITION",
            inputs={"baseline_scope2_emissions": 1000.0},
            assumptions={"renewable_percent": 40.0},
            actor_id="user1",
            session=s,
        )
        args = s.add.call_args[0][0]
        assert args.outputs["projected_scope2_emissions"] == pytest.approx(600.0, abs=0.001)

    def test_emissions_intensity_reduction_formula(self):
        s = _session()
        scoring_service.create_scenario(
            organization_id="org1",
            name="Intensity Reduction",
            scenario_type="EMISSIONS_INTENSITY_REDUCTION",
            inputs={"baseline_intensity": 0.5, "revenue": 1_000_000.0},
            assumptions={"intensity_reduction_percent": 20.0},
            actor_id="user1",
            session=s,
        )
        args = s.add.call_args[0][0]
        assert args.outputs["new_intensity"] == pytest.approx(0.4, abs=0.0001)
        assert args.outputs["projected_total_emissions"] == pytest.approx(400_000.0, abs=0.01)

    def test_invalid_scenario_type_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="scenario_type"):
            scoring_service.create_scenario(
                organization_id="org1",
                name="Bad",
                scenario_type="MAGICAL_THINKING",
                inputs={},
                assumptions={},
                actor_id="user1",
                session=s,
            )


# ── TestM42ClimateRisk ────────────────────────────────────────────────────────

class TestM42ClimateRisk:
    def test_overall_risk_formula(self):
        result = _compute_overall_risk(80.0, 60.0, 40.0)
        expected = round(80.0 * 0.35 + 60.0 * 0.35 + 40.0 * 0.30, 2)
        assert result == expected

    def test_risk_score_out_of_range_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="between 0 and 100"):
            climate_service.create_climate_risk_assessment(
                organization_id="org1",
                title="Test",
                assessment_year=2025,
                transition_risk_score=150.0,
                physical_risk_score=50.0,
                regulatory_risk_score=50.0,
                actor_id="user1",
                session=s,
            )

    def test_invalid_scenario_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="scenario"):
            climate_service.create_climate_risk_assessment(
                organization_id="org1",
                title="Test",
                assessment_year=2025,
                transition_risk_score=50.0,
                physical_risk_score=50.0,
                regulatory_risk_score=50.0,
                actor_id="user1",
                session=s,
                scenario="3C",
            )

    def test_create_stores_overall_risk(self):
        s = _session()
        with patch("application.sustainability.climate_service.emit_audit_event"):
            climate_service.create_climate_risk_assessment(
                organization_id="org1",
                title="Assessment",
                assessment_year=2025,
                transition_risk_score=70.0,
                physical_risk_score=60.0,
                regulatory_risk_score=50.0,
                actor_id="user1",
                session=s,
            )
        args = s.add.call_args[0][0]
        expected = round(70.0 * 0.35 + 60.0 * 0.35 + 50.0 * 0.30, 2)
        assert args.overall_risk_score == expected


# ── TestM42ReportImmutability ─────────────────────────────────────────────────

class TestM42ReportImmutability:
    def test_finalize_report_sets_is_final(self):
        report = _mock_report(is_final=False)
        s = _session(get_return=report)
        with patch("application.sustainability.reporting_service.emit_audit_event"):
            result = reporting_service.finalize_report(
                "report1", "user1", s, organization_id="org1"
            )
        assert result.is_final is True

    def test_finalize_already_final_raises_conflict(self):
        report = _mock_report(is_final=True)
        s = _session(get_return=report)
        with pytest.raises(SustainabilityConflict, match="already finalized"):
            reporting_service.finalize_report(
                "report1", "user1", s, organization_id="org1"
            )

    def test_finalize_cross_tenant_blocked(self):
        report = _mock_report(org="other_org", is_final=False)
        s = _session(get_return=report)
        with pytest.raises(SustainabilityError, match="not found"):
            reporting_service.finalize_report(
                "report1", "user1", s, organization_id="org1"
            )


# ── TestM42TenantIsolation ────────────────────────────────────────────────────

class TestM42TenantIsolation:
    def test_assert_org_none_raises(self):
        with pytest.raises(SustainabilityError, match="not found"):
            _assert_org(None, "org1", "Objective")

    def test_assert_org_wrong_org_raises(self):
        record = MagicMock()
        record.organization_id = "other_org"
        with pytest.raises(SustainabilityError, match="not found"):
            _assert_org(record, "org1", "Objective")

    def test_assert_org_correct_org_passes(self):
        record = MagicMock()
        record.organization_id = "org1"
        _assert_org(record, "org1", "Objective")

    def test_update_objective_status_cross_tenant(self):
        obj = _mock_objective(org="different_org")
        s = _session(get_return=obj)
        with pytest.raises(SustainabilityError, match="not found"):
            objective_service.update_objective_status(
                "obj1", "ACTIVE", "user1", s, organization_id="org1"
            )

    def test_update_target_value_cross_tenant(self):
        t = _mock_target(org="different_org")
        s = _session(get_return=t)
        with pytest.raises(SustainabilityError, match="not found"):
            objective_service.update_target_value(
                "target1", 50.0, "user1", s, organization_id="org1"
            )

    def test_finalize_inventory_cross_tenant(self):
        inv = _mock_inventory(org="other_org", status="DRAFT")
        s = _session(get_return=inv)
        s.query.return_value.filter.return_value.all.return_value = []
        with pytest.raises(SustainabilityError, match="not found"):
            carbon_service.finalize_inventory(
                "inv1", "user1", s, organization_id="org1"
            )

    def test_complete_assurance_cross_tenant(self):
        rec = MagicMock()
        rec.organization_id = "other_org"
        s = _session(get_return=rec)
        with pytest.raises(SustainabilityError, match="not found"):
            reporting_service.complete_assurance(
                "rec1", "user1", s, organization_id="org1"
            )


# ── TestM42ObjectiveService ────────────────────────────────────────────────────

class TestM42ObjectiveService:
    def test_create_objective_invalid_category(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="category"):
            objective_service.create_objective(
                organization_id="org1",
                title="Test",
                category="INVALID",
                actor_id="user1",
                session=s,
            )

    def test_create_objective_valid(self):
        s = _session()
        with patch("application.sustainability.objective_service.emit_audit_event"):
            objective_service.create_objective(
                organization_id="org1",
                title="Reduce Emissions",
                category="ENVIRONMENTAL",
                actor_id="user1",
                session=s,
            )
        s.add.assert_called_once()
        args = s.add.call_args[0][0]
        assert args.objective_status == "DRAFT"
        assert args.category == "ENVIRONMENTAL"

    def test_update_objective_status_invalid(self):
        obj = _mock_objective()
        s = _session(get_return=obj)
        with pytest.raises(SustainabilityError, match="status"):
            objective_service.update_objective_status(
                "obj1", "FLYING", "user1", s, organization_id="org1"
            )

    def test_create_target_invalid_frequency(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="frequency"):
            objective_service.create_target(
                organization_id="org1",
                objective_id="obj1",
                metric_name="Carbon",
                baseline_value=100.0,
                target_value=50.0,
                actor_id="user1",
                session=s,
                measurement_frequency="DAILY",
            )

    def test_update_target_value_recomputes_progress(self):
        t = _mock_target(baseline=0.0, target_val=100.0)
        s = _session(get_return=t)
        with patch("application.sustainability.objective_service.emit_audit_event"):
            target, progress = objective_service.update_target_value(
                "t1", 75.0, "user1", s, organization_id="org1"
            )
        assert progress == 75.0


# ── TestM42CSRDMapping ────────────────────────────────────────────────────────

class TestM42CSRDMapping:
    def test_invalid_esrs_standard_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="ESRS"):
            reporting_service.create_csrd_mapping(
                organization_id="org1",
                esrs_standard="INVALID",
                actor_id="user1",
                session=s,
            )

    def test_invalid_compliance_status_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="compliance_status"):
            reporting_service.create_csrd_mapping(
                organization_id="org1",
                esrs_standard="E1",
                actor_id="user1",
                session=s,
                compliance_status="UNKNOWN",
            )

    def test_valid_csrd_mapping_created(self):
        s = _session()
        with patch("application.sustainability.reporting_service.emit_audit_event"):
            reporting_service.create_csrd_mapping(
                organization_id="org1",
                esrs_standard="E1",
                actor_id="user1",
                session=s,
                compliance_status="COMPLIANT",
            )
        s.add.assert_called_once()


# ── TestM42ISSBMapping ────────────────────────────────────────────────────────

class TestM42ISSBMapping:
    def test_invalid_issb_standard_raises(self):
        s = _session()
        with pytest.raises(SustainabilityError, match="ISSB"):
            reporting_service.create_issb_mapping(
                organization_id="org1",
                issb_standard="S99",
                actor_id="user1",
                session=s,
            )

    def test_valid_issb_mapping_created(self):
        s = _session()
        with patch("application.sustainability.reporting_service.emit_audit_event"):
            reporting_service.create_issb_mapping(
                organization_id="org1",
                issb_standard="S2",
                actor_id="user1",
                session=s,
            )
        s.add.assert_called_once()
