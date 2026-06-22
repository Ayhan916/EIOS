"""M44 — Digital Twin, Strategic Planning & Scenario Intelligence Tests.

10 test classes:
  TestM44Migration           (8 tests)  — table PKs, FKs, org columns, is_final
  TestM44DigitalTwin         (5 tests)  — create twin, snapshot, tenant isolation
  TestM44Scenarios           (6 tests)  — create scenario, assumption, execute
  TestM44StressTests         (9 tests)  — climate, supplier, financial calculations
  TestM44Forecasts           (8 tests)  — linear trend, WMA, scenario projection
  TestM44Pathways            (5 tests)  — pathway milestones, net zero
  TestM44BoardSimulation     (4 tests)  — board simulation, scenario comparison
  TestM44Rollup              (3 tests)  — rollup aggregation, cross-org isolation
  TestM44Reporting           (6 tests)  — report generation, snapshot capture, immutability
  TestM44Observability       (5 tests)  — counter wiring
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

# ── ensure M44 models are registered ──────────────────────────────────────────

from infrastructure.persistence.models.strategy import (  # noqa: F401
    EnterpriseDigitalTwinModel,
    DigitalTwinSnapshotModel,
    StrategicPlanModel,
    StrategicObjectiveModel,
    StrategyScenarioModel,
    ScenarioAssumptionModel,
    ScenarioExecutionModel,
    ClimateStressTestModel,
    SupplierShockScenarioModel,
    FinancialStressTestModel,
    TransitionPathwayModel,
    NetZeroPathwayRecord,
    StrategicRiskProjectionModel,
    PortfolioOptimizationModel,
    InvestmentScenarioModel,
    ForecastMethodologyRecordModel,
    ForecastModelRecord,
    ForecastResultModel,
    BoardSimulationModel,
    StrategicForecastSummaryModel,
    StrategicScenarioReportModel,
)
from infrastructure.persistence.models.base import Base


def _now():
    return datetime.now(timezone.utc)


def _uid():
    return str(uuid.uuid4())


def _session():
    """Return a mock SQLAlchemy session."""
    s = MagicMock()
    s.get.return_value = None
    return s


def _make_model(cls, **kwargs):
    """Instantiate a model without touching the DB."""
    defaults = dict(
        id=_uid(),
        organization_id="org-test",
        created_by="actor",
        updated_by="actor",
        created_at=_now(),
        updated_at=_now(),
    )
    defaults.update(kwargs)
    return cls(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1: Migration integrity
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44Migration:
    """Validate table structure from ORM metadata."""

    def _table(self, name):
        return Base.metadata.tables[name]

    def test_all_21_tables_exist(self):
        m44_tables = [
            "enterprise_digital_twins", "digital_twin_snapshots",
            "strategic_plans", "strategic_objectives",
            "strategy_scenarios", "scenario_assumptions", "scenario_executions",
            "climate_stress_tests", "supplier_shock_scenarios", "financial_stress_tests",
            "transition_pathways", "net_zero_pathways",
            "strategic_risk_projections",
            "portfolio_optimizations", "investment_scenarios",
            "forecast_methodology_records", "forecast_models", "forecast_results",
            "board_simulations", "strategic_forecast_summaries",
            "strategic_scenario_reports",
        ]
        for name in m44_tables:
            assert name in Base.metadata.tables, f"Missing table: {name}"

    def test_all_tables_have_pk_id(self):
        for name in [
            "enterprise_digital_twins", "strategy_scenarios",
            "forecast_models", "board_simulations",
        ]:
            t = self._table(name)
            assert "id" in t.c, f"{name} missing id column"
            assert t.c["id"].primary_key

    def test_all_tables_have_organization_id(self):
        for name in [
            "enterprise_digital_twins", "digital_twin_snapshots",
            "strategic_plans", "strategy_scenarios",
            "climate_stress_tests", "forecast_results",
        ]:
            t = self._table(name)
            assert "organization_id" in t.c, f"{name} missing organization_id"

    def test_digital_twin_snapshot_fk(self):
        t = self._table("digital_twin_snapshots")
        assert "twin_id" in t.c
        fks = {fk.column.table.name for fk in t.c["twin_id"].foreign_keys}
        assert "enterprise_digital_twins" in fks

    def test_strategic_objective_fk(self):
        t = self._table("strategic_objectives")
        assert "plan_id" in t.c
        fks = {fk.column.table.name for fk in t.c["plan_id"].foreign_keys}
        assert "strategic_plans" in fks

    def test_scenario_assumption_fk(self):
        t = self._table("scenario_assumptions")
        fks = {fk.column.table.name for fk in t.c["scenario_id"].foreign_keys}
        assert "strategy_scenarios" in fks

    def test_forecast_result_fk(self):
        t = self._table("forecast_results")
        fks = {fk.column.table.name for fk in t.c["forecast_model_id"].foreign_keys}
        assert "forecast_models" in fks

    def test_is_final_on_output_tables(self):
        for name in [
            "digital_twin_snapshots", "scenario_executions",
            "climate_stress_tests", "forecast_results",
            "board_simulations", "strategic_scenario_reports",
        ]:
            t = self._table(name)
            assert "is_final" in t.c, f"{name} missing is_final"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: Digital Twin
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44DigitalTwin:
    def test_create_digital_twin_sets_fields(self):
        from application.strategy import digital_twin_service

        session = _session()
        with patch("application.strategy.digital_twin_service.emit_audit_event"):
            twin = digital_twin_service.create_digital_twin(
                "org-1", "EIOS Enterprise Twin", "actor-1", session,
                emissions_baseline_tco2e=50_000.0,
                supplier_count=150,
                kpi_count=42,
            )
        assert twin.organization_id == "org-1"
        assert twin.name == "EIOS Enterprise Twin"
        assert twin.emissions_baseline_tco2e == 50_000.0
        assert twin.supplier_count == 150
        assert twin.kpi_count == 42
        assert twin.is_active is True
        assert twin.is_final is False

    def test_create_snapshot_invalid_type_raises(self):
        from application.strategy import digital_twin_service
        from application.strategy.digital_twin_service import StrategyError

        session = _session()
        twin = _make_model(EnterpriseDigitalTwinModel, name="T")
        session.get.return_value = twin
        with pytest.raises(StrategyError, match="Invalid snapshot_type"):
            digital_twin_service.create_snapshot(
                "org-1", twin.id, "WEEKLY", "2024-W01", "actor-1", session
            )

    def test_create_snapshot_valid(self):
        from application.strategy import digital_twin_service

        session = _session()
        twin = _make_model(EnterpriseDigitalTwinModel, name="T", organization_id="org-1")
        session.get.return_value = twin
        with patch("application.strategy.digital_twin_service.emit_audit_event"):
            snap = digital_twin_service.create_snapshot(
                "org-1", twin.id, "QUARTERLY", "2024-Q1", "actor-1", session,
                sustainability_state={"esg_score": 72.5},
            )
        assert snap.twin_id == twin.id
        assert snap.snapshot_type == "QUARTERLY"
        assert snap.snapshot_period == "2024-Q1"
        assert snap.sustainability_state == {"esg_score": 72.5}
        assert snap.is_final is False

    def test_create_snapshot_wrong_org_raises(self):
        from application.strategy import digital_twin_service
        from application.strategy.digital_twin_service import StrategyError

        session = _session()
        twin = _make_model(EnterpriseDigitalTwinModel, name="T", organization_id="org-A")
        session.get.return_value = twin
        with pytest.raises(StrategyError, match="not found"):
            digital_twin_service.create_snapshot(
                "org-B", twin.id, "MONTHLY", "2024-01", "actor-1", session
            )

    def test_create_twin_increments_counter(self):
        from application.strategy import digital_twin_service
        from application.strategy.metrics import strategy_counters

        session = _session()
        before = strategy_counters.digital_twins_total
        with patch("application.strategy.digital_twin_service.emit_audit_event"):
            digital_twin_service.create_digital_twin("org-1", "Twin X", "a", session)
        assert strategy_counters.digital_twins_total == before + 1


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: Scenarios
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44Scenarios:
    def test_create_scenario_valid(self):
        from application.strategy import scenario_service

        session = _session()
        with patch("application.strategy.scenario_service.emit_audit_event"):
            sc = scenario_service.create_scenario(
                "org-1", "2030 Carbon Price", "CLIMATE", "actor-1", session,
                time_horizon_years=7,
            )
        assert sc.name == "2030 Carbon Price"
        assert sc.scenario_type == "CLIMATE"
        assert sc.scenario_status == "Draft"
        assert sc.time_horizon_years == 7

    def test_create_scenario_invalid_type_raises(self):
        from application.strategy import scenario_service
        from application.strategy.digital_twin_service import StrategyError

        session = _session()
        with pytest.raises(StrategyError, match="Invalid scenario_type"):
            scenario_service.create_scenario("org-1", "X", "UNKNOWN", "a", session)

    def test_create_assumption_attaches_to_scenario(self):
        from application.strategy import scenario_service

        session = _session()
        sc = _make_model(StrategyScenarioModel, name="S", scenario_type="CLIMATE",
                         scenario_status="Draft", time_horizon_years=5,
                         created_by_user="a", is_template=False)
        session.get.return_value = sc
        assumption = scenario_service.create_assumption(
            "org-test", sc.id, "carbon_price_usd_per_tco2e", "Carbon Price",
            120.0, "actor-1", session,
            unit="USD/tCO2e",
            source="IEA 2030 NZE",
        )
        assert assumption.scenario_id == sc.id
        assert assumption.value == 120.0
        assert assumption.source == "IEA 2030 NZE"

    def test_execute_scenario_produces_projections(self):
        from application.strategy import scenario_service

        session = _session()
        sc = _make_model(StrategyScenarioModel, name="S", scenario_type="CLIMATE",
                         scenario_status="Draft", time_horizon_years=5,
                         created_by_user="a", is_template=False)
        session.get.return_value = sc
        session.query.return_value.filter.return_value.all.return_value = []
        with patch("application.strategy.scenario_service.emit_audit_event"):
            execution = scenario_service.execute_scenario(
                "org-test", sc.id, "actor-1", session,
                baseline_override={"emissions_tco2e": 10_000.0, "revenue": 1_000_000.0},
            )
        assert execution.execution_status == "Completed"
        assert execution.projected_kpis is not None
        assert execution.projected_emissions is not None
        assert execution.projected_financial is not None

    def test_execute_scenario_applies_carbon_price_assumption(self):
        from application.strategy import scenario_service

        session = _session()
        sc = _make_model(StrategyScenarioModel, name="S", scenario_type="FINANCIAL",
                         scenario_status="Draft", time_horizon_years=3,
                         created_by_user="a", is_template=False)
        session.get.return_value = sc
        assumption = _make_model(
            ScenarioAssumptionModel,
            scenario_id=sc.id,
            assumption_key="carbon_price_usd_per_tco2e",
            assumption_label="Carbon Price",
            value=150.0,
        )
        session.query.return_value.filter.return_value.all.return_value = [assumption]
        with patch("application.strategy.scenario_service.emit_audit_event"):
            execution = scenario_service.execute_scenario(
                "org-test", sc.id, "actor-1", session,
                baseline_override={"emissions_tco2e": 1000.0, "revenue": 500_000.0},
            )
        assert execution.projected_financial["carbon_price_usd_per_tco2e"] == 150.0

    def test_execute_scenario_wrong_org_raises(self):
        from application.strategy import scenario_service
        from application.strategy.digital_twin_service import StrategyError

        session = _session()
        sc = _make_model(StrategyScenarioModel, name="S", scenario_type="CLIMATE",
                         scenario_status="Draft", time_horizon_years=5,
                         organization_id="org-A", created_by_user="a", is_template=False)
        session.get.return_value = sc
        with pytest.raises(StrategyError, match="not found"):
            scenario_service.execute_scenario("org-B", sc.id, "a", session)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4: Stress Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44StressTests:
    """Validate deterministic stress test calculation formulas."""

    def _climate(self, stress_type, **kwargs):
        from application.strategy.stress_test_service import _compute_climate_impacts
        return _compute_climate_impacts(
            stress_type,
            kwargs.get("carbon_price_shock_pct", 0.0),
            kwargs.get("physical_risk_multiplier", 0.0),
            kwargs.get("regulatory_intensity_score", 0.0),
            kwargs.get("transition_cost_pct", 0.0),
        )

    def test_carbon_price_shock_risk_impact(self):
        risk, em, fin = self._climate("CARBON_PRICE", carbon_price_shock_pct=50.0)
        # risk = 50 * 0.20 = 10.0
        assert risk["total_risk_increase_pct"] == pytest.approx(10.0)

    def test_carbon_price_shock_emissions_decrease(self):
        _, em, _ = self._climate("CARBON_PRICE", carbon_price_shock_pct=50.0)
        # em_change = -50 * 0.08 = -4.0
        assert em["emissions_change_pct"] == pytest.approx(-4.0)

    def test_transition_shock_formula(self):
        risk, em, fin = self._climate("TRANSITION_SHOCK",
                                      carbon_price_shock_pct=20.0,
                                      transition_cost_pct=10.0)
        # risk = 20*0.15 + 10*0.10 = 3+1 = 4
        assert risk["total_risk_increase_pct"] == pytest.approx(4.0)
        # fin_cost = 10 * 0.20 = 2.0
        assert fin["financial_cost_pct"] == pytest.approx(2.0)

    def test_physical_risk_formula(self):
        risk, em, fin = self._climate("PHYSICAL_RISK", physical_risk_multiplier=2.0)
        # risk = 2 * 15 = 30
        assert risk["total_risk_increase_pct"] == pytest.approx(30.0)
        # fin = 2 * 8 = 16
        assert fin["financial_cost_pct"] == pytest.approx(16.0)

    def test_regulatory_shock_formula(self):
        risk, em, fin = self._climate("REGULATORY", regulatory_intensity_score=3.0)
        # risk = 3 * 10 = 30
        assert risk["total_risk_increase_pct"] == pytest.approx(30.0)

    def test_supplier_shock_linear_propagation(self):
        from application.strategy.stress_test_service import _compute_supplier_impacts
        sc, fin, esg = _compute_supplier_impacts(0.6, "LINEAR")
        # disruption = 0.6 * 100 = 60
        assert sc["supply_disruption_pct"] == pytest.approx(60.0)
        # fin = 0.6 * 15 = 9
        assert fin["financial_impact_pct"] == pytest.approx(9.0)

    def test_supplier_shock_network_amplification(self):
        from application.strategy.stress_test_service import _compute_supplier_impacts
        _, fin_lin, _ = _compute_supplier_impacts(0.5, "LINEAR")
        _, fin_net, _ = _compute_supplier_impacts(0.5, "NETWORK")
        # Network = linear * 1.5
        assert fin_net["financial_impact_pct"] == pytest.approx(fin_lin["financial_impact_pct"] * 1.5)

    def test_financial_stress_financing_cost(self):
        from application.strategy.stress_test_service import _compute_financial_stress_impacts
        fin, esg = _compute_financial_stress_impacts("FINANCING_COST", 200.0, 0.0, 0.0, 0)
        # cost = 200 / 100 = 2.0%
        assert fin["cost_increase_pct"] == pytest.approx(2.0)
        assert fin["ebitda_impact_pct"] == pytest.approx(-2.0)

    def test_financial_stress_carbon_tax(self):
        from application.strategy.stress_test_service import _compute_financial_stress_impacts
        fin, _ = _compute_financial_stress_impacts("CARBON_TAX", 0.0, 0.0, 30.0, 0)
        # cost = 30 * 0.5 = 15.0%
        assert fin["cost_increase_pct"] == pytest.approx(15.0)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5: Forecasts
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44Forecasts:
    """Validate deterministic forecast algorithms."""

    def test_linear_trend_projection(self):
        from application.strategy.forecast_service import _linear_trend
        # f(3) = 100 + 5 * 3 = 115
        assert _linear_trend(100.0, 5.0, 3) == pytest.approx(115.0)

    def test_linear_trend_zero_slope(self):
        from application.strategy.forecast_service import _linear_trend
        assert _linear_trend(200.0, 0.0, 10) == pytest.approx(200.0)

    def test_weighted_moving_average(self):
        from application.strategy.forecast_service import _weighted_moving_average
        # WMA([100, 110, 120], [1, 2, 3]) = (100*1 + 110*2 + 120*3) / 6 = 680/6 ≈ 113.33
        result = _weighted_moving_average([100.0, 110.0, 120.0], [1.0, 2.0, 3.0])
        assert result == pytest.approx(113.333, rel=1e-3)

    def test_weighted_moving_average_zero_weights_raises(self):
        from application.strategy.forecast_service import _weighted_moving_average
        from application.strategy.digital_twin_service import StrategyError
        with pytest.raises(StrategyError, match="non-zero"):
            _weighted_moving_average([100.0], [0.0])

    def test_scenario_projection_compound(self):
        from application.strategy.forecast_service import _scenario_projection
        # baseline=100, +5% for 3 years = 100 * 1.05^3 ≈ 115.7625
        result = _scenario_projection(100.0, 5.0, 3)
        assert result == pytest.approx(115.7625, rel=1e-4)

    def test_scenario_projection_decline(self):
        from application.strategy.forecast_service import _scenario_projection
        # baseline=1000, -10% for 2 years = 1000 * 0.9^2 = 810
        result = _scenario_projection(1000.0, -10.0, 2)
        assert result == pytest.approx(810.0)

    def test_create_forecast_model(self):
        from application.strategy import forecast_service

        session = _session()
        with patch("application.strategy.forecast_service.emit_audit_event"):
            model = forecast_service.create_forecast_model(
                "org-1", "Emissions Linear", "LINEAR_TREND", "actor-1", session,
                parameters={"slope": -500.0},
            )
        assert model.methodology == "LINEAR_TREND"
        assert model.parameters == {"slope": -500.0}

    def test_run_forecast_linear_trend(self):
        from application.strategy import forecast_service

        session = _session()
        fm = _make_model(
            ForecastModelRecord,
            model_name="LT",
            methodology="LINEAR_TREND",
            parameters={"slope": -1000.0},
            model_version="1.0.0",
            is_approved=False,
            approved_by=None,
            methodology_record_id=None,
        )
        session.get.return_value = fm
        with patch("application.strategy.forecast_service.emit_audit_event"):
            result = forecast_service.run_forecast(
                "org-test", fm.id, "EMISSIONS", "scope_1_tco2e",
                2030, 50_000.0, "actor-1", session,
            )
        assert result.forecast_type == "EMISSIONS"
        assert result.forecast_value is not None
        # slope=-1000, years = 2030 - current_year (≥1), forecast must be < baseline
        assert result.forecast_value < 50_000.0


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6: Pathways
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44Pathways:
    def test_create_pathway_computes_reduction_pct(self):
        from application.strategy import pathway_service

        session = _session()
        with patch("application.strategy.pathway_service.emit_audit_event"):
            pathway = pathway_service.create_pathway(
                "org-1", "Net Zero 2050", "ACCELERATED", 2050, "actor-1", session,
                baseline_emissions_tco2e=100_000.0,
                target_emissions_tco2e=0.0,
            )
        assert pathway.reduction_pct == pytest.approx(100.0)

    def test_create_pathway_generates_milestones(self):
        from application.strategy import pathway_service

        session = _session()
        with patch("application.strategy.pathway_service.emit_audit_event"):
            pathway = pathway_service.create_pathway(
                "org-1", "Conservative 2040", "CONSERVATIVE", 2040, "actor-1", session,
                baseline_emissions_tco2e=10_000.0,
                target_emissions_tco2e=2_000.0,
            )
        ms = (pathway.milestones or {}).get("milestones", [])
        assert len(ms) == 5
        # first milestone emissions must be between baseline and target
        assert 2_000.0 < ms[0]["emissions_tco2e"] < 10_000.0
        # milestones should be decreasing
        vals = [m["emissions_tco2e"] for m in ms]
        assert vals == sorted(vals, reverse=True)

    def test_create_pathway_invalid_type_raises(self):
        from application.strategy import pathway_service
        from application.strategy.digital_twin_service import StrategyError

        session = _session()
        with pytest.raises(StrategyError, match="Invalid pathway_type"):
            pathway_service.create_pathway("org-1", "X", "UNKNOWN", 2040, "a", session)

    def test_create_net_zero_pathway(self):
        from application.strategy import pathway_service

        session = _session()
        pathway = _make_model(
            TransitionPathwayModel,
            pathway_name="P", pathway_type="EXPECTED",
            target_year=2050, is_primary=True, is_final=False,
        )
        session.get.return_value = pathway
        with patch("application.strategy.pathway_service.emit_audit_event"):
            nz = pathway_service.create_net_zero_pathway(
                "org-test", pathway.id, 2048, "actor-1", session,
                interim_targets=[{"year": 2035, "reduction_pct": 50}],
                methodology="SBTi_1.5C",
            )
        assert nz.net_zero_year == 2048
        assert nz.methodology == "SBTi_1.5C"
        targets = (nz.interim_targets or {}).get("targets", [])
        assert len(targets) == 1

    def test_net_zero_pathway_wrong_org_raises(self):
        from application.strategy import pathway_service
        from application.strategy.digital_twin_service import StrategyError

        session = _session()
        pathway = _make_model(
            TransitionPathwayModel, organization_id="org-A",
            pathway_name="P", pathway_type="EXPECTED",
            target_year=2050, is_primary=False, is_final=False,
        )
        session.get.return_value = pathway
        with pytest.raises(StrategyError, match="not found"):
            pathway_service.create_net_zero_pathway("org-B", pathway.id, 2050, "a", session)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 7: Board Simulation
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44BoardSimulation:
    def test_create_board_simulation_no_executions(self):
        from application.strategy import board_simulation_service

        session = _session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        with patch("application.strategy.board_simulation_service.emit_audit_event"):
            sim = board_simulation_service.create_board_simulation(
                "org-1", "2030 Strategic Choices", "actor-1", session,
                scenario_a_id="sc-A",
                scenario_b_id="sc-B",
            )
        assert sim.simulation_name == "2030 Strategic Choices"
        assert sim.scenario_a_id == "sc-A"
        assert sim.scenario_a_results == {"scenario_id": "sc-A", "status": "no_execution"}
        assert sim.comparison_dimensions == {"dimensions": ["risk", "esg_score", "emissions", "value_creation", "financial_outcomes"]}

    def test_create_board_simulation_with_execution(self):
        from application.strategy import board_simulation_service

        session = _session()
        exec_rec = _make_model(
            ScenarioExecutionModel,
            scenario_id="sc-A",
            twin_id=None,
            execution_status="Completed",
            executed_at=_now(),
            projected_kpis={"revenue": 2_000_000},
            projected_risks={"risk_score": 3.5},
            projected_emissions={"emissions_tco2e": 8_000},
            projected_financial={"carbon_cost": 400_000},
            execution_metadata={},
            is_final=False,
        )
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = exec_rec
        with patch("application.strategy.board_simulation_service.emit_audit_event"):
            sim = board_simulation_service.create_board_simulation(
                "org-1", "Exec Compare", "actor-1", session,
                scenario_a_id="sc-A",
            )
        assert sim.scenario_a_results["projected_kpis"] == {"revenue": 2_000_000}

    def test_board_simulation_increments_counter(self):
        from application.strategy import board_simulation_service
        from application.strategy.metrics import strategy_counters

        session = _session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        before = strategy_counters.board_simulations_total
        with patch("application.strategy.board_simulation_service.emit_audit_event"):
            board_simulation_service.create_board_simulation("org-1", "X", "a", session)
        assert strategy_counters.board_simulations_total == before + 1

    def test_list_board_simulations(self):
        from application.strategy import board_simulation_service

        session = _session()
        sim = _make_model(
            BoardSimulationModel,
            simulation_name="Sim",
            scenario_a_id=None, scenario_b_id=None, scenario_c_id=None,
            comparison_dimensions={}, scenario_a_results={},
            scenario_b_results={}, scenario_c_results={},
            recommendation=None, simulated_by="a", is_final=False,
        )
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [sim]
        result = board_simulation_service.list_board_simulations("org-1", session)
        assert result == [sim]


# ═══════════════════════════════════════════════════════════════════════════════
# Section 8: Rollup
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44Rollup:
    def test_rollup_returns_correct_keys(self):
        from application.strategy import rollup_service

        session = _session()
        session.query.return_value.filter.return_value.scalar.return_value = 5
        # 9 original + 7 new M44.1 aggregate queries (avg values + template/methodology/comparison counts)
        session.query.return_value.filter.return_value.scalar.side_effect = [
            3, 7, 12, 2, 4, 8, 1, 5, 0, None, None, None, 0, 0, 0, 0
        ]
        result = rollup_service.strategy_rollup("org-1", session)
        assert "digital_twins" in result
        assert "scenarios" in result
        assert "scenario_executions" in result
        assert "total_stress_tests" in result
        assert "forecasts" in result
        assert "board_simulations" in result
        assert result["organization_id"] == "org-1"

    def test_rollup_cross_org_isolation(self):
        from application.strategy import rollup_service

        session_a = _session()
        session_b = _session()
        session_a.query.return_value.filter.return_value.scalar.return_value = 10
        session_b.query.return_value.filter.return_value.scalar.return_value = 0
        result_a = rollup_service.strategy_rollup("org-A", session_a)
        result_b = rollup_service.strategy_rollup("org-B", session_b)
        assert result_a["organization_id"] == "org-A"
        assert result_b["organization_id"] == "org-B"

    def test_rollup_total_stress_tests_is_sum(self):
        from application.strategy import rollup_service

        session = _session()
        call_idx = [0]
        def side_effect(*args, **kwargs):
            vals = [0, 0, 0, 3, 5, 0, 0, 0, 0]  # climate=3, financial=5
            v = vals[call_idx[0] % len(vals)]
            call_idx[0] += 1
            return v
        session.query.return_value.filter.return_value.scalar.side_effect = side_effect
        result = rollup_service.strategy_rollup("org-1", session)
        assert result["total_stress_tests"] == result["climate_stress_tests"] + result["financial_stress_tests"]


# ═══════════════════════════════════════════════════════════════════════════════
# Section 9: Reporting
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44Reporting:
    def test_generate_report_captures_snapshots(self):
        from application.strategy import reporting_service

        session = _session()
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        with patch("application.strategy.reporting_service.emit_audit_event"):
            report = reporting_service.generate_strategic_report(
                "org-1", "Annual Strategy 2025", "2025", "actor-1", session,
                included_scenario_ids=["sc-1", "sc-2"],
            )
        assert report.report_title == "Annual Strategy 2025"
        assert report.report_period == "2025"
        assert report.is_final is False
        assert report.included_scenarios == {"scenario_ids": ["sc-1", "sc-2"]}
        assert "assumptions" in report.assumptions_snapshot
        assert "forecasts" in report.forecasts_snapshot
        assert "climate_stress_tests" in report.stress_tests_snapshot
        assert "pathways" in report.pathway_outcomes

    def test_finalize_report_sets_is_final(self):
        from application.strategy import reporting_service

        session = _session()
        report = _make_model(
            StrategicScenarioReportModel,
            report_title="Rep", report_period="2025",
            included_scenarios={}, assumptions_snapshot={},
            forecasts_snapshot={}, stress_tests_snapshot={},
            pathway_outcomes={}, board_comparison=None,
            report_methodology="det", is_final=False,
            finalized_at=None, finalized_by=None,
        )
        session.get.return_value = report
        with patch("application.strategy.reporting_service.emit_audit_event"):
            result = reporting_service.finalize_report("org-test", report.id, "actor-1", session)
        assert result.is_final is True
        assert result.finalized_by == "actor-1"
        assert result.finalized_at is not None

    def test_finalize_already_final_raises(self):
        from application.strategy import reporting_service
        from application.strategy.digital_twin_service import StrategyError

        session = _session()
        report = _make_model(
            StrategicScenarioReportModel,
            report_title="R", report_period="2025",
            included_scenarios={}, assumptions_snapshot={},
            forecasts_snapshot={}, stress_tests_snapshot={},
            pathway_outcomes={}, board_comparison=None,
            report_methodology="det", is_final=True,
            finalized_at=_now(), finalized_by="actor-1",
        )
        session.get.return_value = report
        with pytest.raises(StrategyError, match="already finalized"):
            reporting_service.finalize_report("org-test", report.id, "actor-2", session)

    def test_report_not_found_raises(self):
        from application.strategy import reporting_service
        from application.strategy.digital_twin_service import StrategyError

        session = _session()
        session.get.return_value = None
        with pytest.raises(StrategyError, match="not found"):
            reporting_service.finalize_report("org-1", "nonexistent", "a", session)

    def test_generate_forecast_summary_aggregates(self):
        from application.strategy import reporting_service

        session = _session()
        r1 = _make_model(
            ForecastResultModel,
            forecast_model_id="m1", forecast_type="EMISSIONS",
            target_metric="scope_1", forecast_year=2030,
            baseline_value=10_000.0, forecast_value=7_000.0,
            lower_bound=6_000.0, upper_bound=8_000.0,
            confidence_level=0.85, scenario_id=None, is_final=False,
        )
        r2 = _make_model(
            ForecastResultModel,
            forecast_model_id="m1", forecast_type="EMISSIONS",
            target_metric="scope_2", forecast_year=2030,
            baseline_value=5_000.0, forecast_value=3_000.0,
            lower_bound=2_500.0, upper_bound=3_500.0,
            confidence_level=0.80, scenario_id=None, is_final=False,
        )
        session.query.return_value.filter.return_value.all.return_value = [r1, r2]
        summary = reporting_service.generate_forecast_summary("org-1", "2025-Q4", "actor-1", session)
        assert summary.summary_period == "2025-Q4"
        # avg EMISSIONS = (7000 + 3000) / 2 = 5000
        assert summary.forecast_emissions_tco2e == pytest.approx(5000.0)

    def test_report_increments_counter(self):
        from application.strategy import reporting_service
        from application.strategy.metrics import strategy_counters

        session = _session()
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        before = strategy_counters.strategic_reports_total
        with patch("application.strategy.reporting_service.emit_audit_event"):
            reporting_service.generate_strategic_report("org-1", "R", "2025", "a", session)
        assert strategy_counters.strategic_reports_total == before + 1


# ═══════════════════════════════════════════════════════════════════════════════
# Section 10: Observability
# ═══════════════════════════════════════════════════════════════════════════════

class TestM44Observability:
    def test_create_scenario_increments_counter(self):
        from application.strategy import scenario_service
        from application.strategy.metrics import strategy_counters

        session = _session()
        before = strategy_counters.scenarios_total
        with patch("application.strategy.scenario_service.emit_audit_event"):
            scenario_service.create_scenario("org-1", "S", "CLIMATE", "a", session)
        assert strategy_counters.scenarios_total == before + 1

    def test_execute_scenario_increments_counter(self):
        from application.strategy import scenario_service
        from application.strategy.metrics import strategy_counters

        session = _session()
        sc = _make_model(StrategyScenarioModel, name="S", scenario_type="CLIMATE",
                         scenario_status="Draft", time_horizon_years=5,
                         created_by_user="a", is_template=False)
        session.get.return_value = sc
        session.query.return_value.filter.return_value.all.return_value = []
        before = strategy_counters.scenario_executions_total
        with patch("application.strategy.scenario_service.emit_audit_event"):
            scenario_service.execute_scenario("org-test", sc.id, "a", session)
        assert strategy_counters.scenario_executions_total == before + 1

    def test_create_climate_stress_test_increments_counter(self):
        from application.strategy import stress_test_service
        from application.strategy.metrics import strategy_counters

        session = _session()
        before = strategy_counters.climate_stress_tests_total
        with patch("application.strategy.stress_test_service.emit_audit_event"):
            stress_test_service.create_climate_stress_test(
                "org-1", "T", "CARBON_PRICE", "a", session,
                carbon_price_shock_pct=30.0,
            )
        assert strategy_counters.climate_stress_tests_total == before + 1

    def test_run_forecast_increments_counter(self):
        from application.strategy import forecast_service
        from application.strategy.metrics import strategy_counters

        session = _session()
        fm = _make_model(
            ForecastModelRecord,
            model_name="M", methodology="SCENARIO_PROJECTION",
            parameters={"annual_change_pct": -5.0},
            model_version="1.0.0", is_approved=False,
            approved_by=None, methodology_record_id=None,
        )
        session.get.return_value = fm
        before = strategy_counters.forecasts_total
        with patch("application.strategy.forecast_service.emit_audit_event"):
            forecast_service.run_forecast(
                "org-test", fm.id, "EMISSIONS", "scope_1", 2030, 10_000.0, "a", session
            )
        assert strategy_counters.forecasts_total == before + 1

    def test_metrics_to_prometheus_lines(self):
        from application.strategy.metrics import strategy_counters
        lines = strategy_counters.to_prometheus_lines("test")
        assert any("eios_digital_twins_total" in l for l in lines)
        assert any("eios_scenario_executions_total" in l for l in lines)
        assert any("eios_forecasts_total" in l for l in lines)
        assert any("eios_board_simulations_total" in l for l in lines)
