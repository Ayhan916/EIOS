"""M42.1 — Completion tests: enterprise rollups, executive dashboard, program validation, metrics."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_session():
    return MagicMock()


# ── Section 1–4: Enterprise Rollups ──────────────────────────────────────────


class TestEnterpriseRollups:
    def test_org_ids_for_enterprise(self):
        from application.sustainability.rollup_service import _org_ids_for_entity

        session = _mock_session()
        session.query.return_value.filter.return_value.all.return_value = [
            SimpleNamespace(id="org-1"),
            SimpleNamespace(id="org-2"),
        ]
        result = _org_ids_for_entity("enterprise", "ent-123", session)
        assert result == ["org-1", "org-2"]

    def test_emissions_rollup_aggregates(self):
        from application.sustainability.rollup_service import _emissions_rollup

        session = _mock_session()
        row = SimpleNamespace(total=1000.0, s1=300.0, s2=400.0, s3=300.0, cnt=3)
        session.query.return_value.filter.return_value.one.return_value = row
        result = _emissions_rollup(["org-1", "org-2"], session)
        assert result.total_emissions == 1000.0
        assert result.scope1 == 300.0
        assert result.scope2 == 400.0
        assert result.scope3 == 300.0
        assert result.inventories_count == 3

    def test_emissions_rollup_empty_org_list(self):
        from application.sustainability.rollup_service import EmissionsRollup, _emissions_rollup

        session = _mock_session()
        result = _emissions_rollup([], session)
        assert isinstance(result, EmissionsRollup)
        assert result.total_emissions == 0.0
        session.query.assert_not_called()

    def test_compute_rollup_invalid_entity_type(self):
        import pytest

        from application.sustainability.objective_service import SustainabilityError
        from application.sustainability.rollup_service import compute_rollup

        session = _mock_session()
        with pytest.raises(SustainabilityError, match="Invalid entity_type"):
            compute_rollup("group", "id-1", "actor-1", session)

    def test_compute_rollup_emits_audit_event(self):
        from application.sustainability import rollup_service

        session = _mock_session()
        session.query.return_value.filter.return_value.all.return_value = []

        with patch("application.sustainability.rollup_service.emit_audit_event") as mock_emit:
            rollup_service.compute_rollup("enterprise", "ent-1", "actor-1", session)
            mock_emit.assert_called_once()
            call_kwargs = mock_emit.call_args.kwargs
            assert call_kwargs["event_type"] == "sustainability.rollup.computed"
            assert call_kwargs["actor_id"] == "actor-1"


class TestBusinessUnitRollups:
    def test_org_ids_for_business_unit(self):
        from application.sustainability.rollup_service import _org_ids_for_entity

        session = _mock_session()
        session.query.return_value.filter.return_value.all.return_value = [
            SimpleNamespace(id="org-bu-1"),
        ]
        result = _org_ids_for_entity("business_unit", "bu-42", session)
        assert result == ["org-bu-1"]

    def test_objectives_rollup_completion_percent(self):
        from application.sustainability.rollup_service import _objectives_rollup

        session = _mock_session()
        session.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            SimpleNamespace(objective_status="ACTIVE", cnt=6),
            SimpleNamespace(objective_status="COMPLETED", cnt=4),
        ]
        result = _objectives_rollup(["org-1"], session)
        assert result.total == 10
        assert result.completed == 4
        assert result.completion_percent == 40.0

    def test_objectives_rollup_empty_org_list(self):
        from application.sustainability.rollup_service import ObjectivesRollup, _objectives_rollup

        result = _objectives_rollup([], _mock_session())
        assert isinstance(result, ObjectivesRollup)
        assert result.total == 0


class TestRegionRollups:
    def test_org_ids_for_region(self):
        from application.sustainability.rollup_service import _org_ids_for_entity

        session = _mock_session()
        session.query.return_value.filter.return_value.all.return_value = [
            SimpleNamespace(id="org-r1"),
            SimpleNamespace(id="org-r2"),
            SimpleNamespace(id="org-r3"),
        ]
        result = _org_ids_for_entity("region", "region-apac", session)
        assert len(result) == 3

    def test_kpis_rollup_empty(self):
        from application.sustainability.rollup_service import KPIsRollup, _kpis_rollup

        result = _kpis_rollup([], _mock_session())
        assert isinstance(result, KPIsRollup)
        assert result.total == 0 and result.active == 0


class TestLegalEntityRollups:
    def test_org_ids_for_legal_entity(self):
        from application.sustainability.rollup_service import _org_ids_for_entity

        session = _mock_session()
        session.query.return_value.filter.return_value.all.return_value = []
        result = _org_ids_for_entity("legal_entity", "le-99", session)
        assert result == []

    def test_climate_rollup_returns_none_scores_when_empty(self):
        from application.sustainability.rollup_service import ClimateRiskRollup, _climate_rollup

        session = _mock_session()
        row = SimpleNamespace(avg_overall=None, avg_trans=None, avg_phys=None, avg_reg=None, cnt=0)
        session.query.return_value.filter.return_value.one.return_value = row
        result = _climate_rollup(["org-1"], session)
        assert isinstance(result, ClimateRiskRollup)
        assert result.avg_overall_risk is None


# ── Section 5: Executive Dashboard Integration ────────────────────────────────


class TestExecutiveDashboardIntegration:
    def test_executive_dashboard_has_sustainability_field(self):
        from interfaces.api.schemas.executive import ExecutiveDashboard

        fields = ExecutiveDashboard.model_fields
        assert "sustainability_summary" in fields
        assert fields["sustainability_summary"].default is None

    def test_sustainability_executive_summary_defaults(self):
        from interfaces.api.schemas.sustainability import SustainabilityExecutiveSummary

        s = SustainabilityExecutiveSummary()
        assert s.status == "ok"
        assert s.active_net_zero_roadmaps == 0
        assert s.open_kpi_alerts == 0
        assert s.total_emissions is None

    def test_sustainability_executive_summary_degraded(self):
        from interfaces.api.schemas.sustainability import SustainabilityExecutiveSummary

        s = SustainabilityExecutiveSummary(status="degraded", degraded_reason="DB error")
        assert s.status == "degraded"
        assert s.degraded_reason == "DB error"


# ── Section 6: ESG Program Validation ────────────────────────────────────────


class TestProgramValidation:
    def test_valid_program_passes(self):
        from application.sustainability.objective_service import validate_program_assignment

        session = _mock_session()
        prog = MagicMock()
        prog.organization_id = "org-1"
        session.get.return_value = prog
        with patch("application.sustainability.objective_service.emit_audit_event") as mock_emit:
            validate_program_assignment("prog-1", "org-1", "actor-1", session)
            mock_emit.assert_called_once()
            assert mock_emit.call_args.kwargs["event_type"] == "sustainability.program.linked"

    def test_cross_org_program_raises(self):
        import pytest

        from application.sustainability.objective_service import (
            SustainabilityError,
            validate_program_assignment,
        )

        session = _mock_session()
        prog = MagicMock()
        prog.organization_id = "org-OTHER"
        session.get.return_value = prog
        with pytest.raises(SustainabilityError, match="program_id must reference"):
            validate_program_assignment("prog-1", "org-1", "actor-1", session)

    def test_nonexistent_program_raises(self):
        import pytest

        from application.sustainability.objective_service import (
            SustainabilityError,
            validate_program_assignment,
        )

        session = _mock_session()
        session.get.return_value = None
        with pytest.raises(SustainabilityError, match="program_id must reference"):
            validate_program_assignment("ghost-id", "org-1", "actor-1", session)

    def test_create_objective_calls_validate_when_program_id_given(self):
        from application.sustainability import objective_service

        session = _mock_session()
        prog = MagicMock()
        prog.organization_id = "org-1"
        session.get.return_value = prog
        with patch("application.sustainability.objective_service.emit_audit_event"):
            with patch(
                "application.sustainability.objective_service.validate_program_assignment"
            ) as mock_vpa:
                objective_service.create_objective(
                    "org-1",
                    "Green Energy",
                    "ENVIRONMENTAL",
                    "actor-1",
                    session,
                    program_id="prog-1",
                )
                mock_vpa.assert_called_once_with("prog-1", "org-1", "actor-1", session)

    def test_create_objective_skips_validate_when_no_program_id(self):
        from application.sustainability import objective_service

        session = _mock_session()
        with patch("application.sustainability.objective_service.emit_audit_event"):
            with patch(
                "application.sustainability.objective_service.validate_program_assignment"
            ) as mock_vpa:
                objective_service.create_objective(
                    "org-1",
                    "Water Usage",
                    "ENVIRONMENTAL",
                    "actor-1",
                    session,
                )
                mock_vpa.assert_not_called()


# ── Section 7: Metrics Instrumentation ────────────────────────────────────────


class TestMetricsInstrumentation:
    def test_objective_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.sustainability_objectives_total
        sustainability_counters.record_objective_created()
        assert sustainability_counters.sustainability_objectives_total == before + 1

    def test_target_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.sustainability_targets_total
        sustainability_counters.record_target_created()
        assert sustainability_counters.sustainability_targets_total == before + 1

    def test_kpi_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.sustainability_kpis_total
        sustainability_counters.record_kpi_created()
        assert sustainability_counters.sustainability_kpis_total == before + 1

    def test_kpi_alert_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.sustainability_kpi_alerts_total
        sustainability_counters.record_kpi_alert()
        assert sustainability_counters.sustainability_kpi_alerts_total == before + 1

    def test_report_generated_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.sustainability_reports_total
        sustainability_counters.record_report_generated()
        assert sustainability_counters.sustainability_reports_total == before + 1

    def test_report_finalized_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.sustainability_reports_finalized_total
        sustainability_counters.record_report_finalized()
        assert sustainability_counters.sustainability_reports_finalized_total == before + 1

    def test_inventory_recalculated_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.carbon_inventory_recalculations_total
        sustainability_counters.record_inventory_recalculated()
        assert sustainability_counters.carbon_inventory_recalculations_total == before + 1

    def test_inventory_finalized_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.carbon_inventories_finalized_total
        sustainability_counters.record_inventory_finalized()
        assert sustainability_counters.carbon_inventories_finalized_total == before + 1

    def test_sbt_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.science_based_targets_total
        sustainability_counters.record_sbt_created()
        assert sustainability_counters.science_based_targets_total == before + 1

    def test_climate_risk_counter_increments(self):
        from application.sustainability.metrics import sustainability_counters

        before = sustainability_counters.climate_risk_assessments_total
        sustainability_counters.record_climate_risk_created()
        assert sustainability_counters.climate_risk_assessments_total == before + 1

    def test_measurement_recorded_is_callable(self):
        from application.sustainability.metrics import sustainability_counters

        sustainability_counters.record_measurement_recorded()  # no-op, must not raise

    def test_prometheus_lines_include_all_counters(self):
        from application.sustainability.metrics import sustainability_counters

        lines = "\n".join(sustainability_counters.to_prometheus_lines("test"))
        assert "eios_sustainability_objectives_total" in lines
        assert "eios_carbon_inventory_recalculations_total" in lines
        assert "eios_science_based_targets_total" in lines


# ── Section 8: Targets Page API Contract ──────────────────────────────────────


class TestTargetsPageApiContract:
    def test_list_all_targets_service_function_exists(self):
        from application.sustainability.objective_service import list_all_targets

        assert callable(list_all_targets)

    def test_list_all_targets_returns_tuples(self):
        from application.sustainability.objective_service import list_all_targets

        session = _mock_session()
        t = MagicMock()
        t.baseline_value = 100.0
        t.target_value = 200.0
        t.current_value = 150.0
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [
            t
        ]
        result = list_all_targets("org-1", session)
        assert len(result) == 1
        target, progress = result[0]
        assert target is t
        assert 0.0 <= progress <= 100.0

    def test_esg_target_response_has_progress_percent(self):
        from interfaces.api.schemas.sustainability import ESGTargetResponse

        fields = ESGTargetResponse.model_fields
        assert "progress_percent" in fields


# ── Section 9: SBT API Contract ───────────────────────────────────────────────


class TestScienceBasedTargetsApiContract:
    def test_list_science_based_targets_service_exists(self):
        from application.sustainability.roadmap_service import list_science_based_targets

        assert callable(list_science_based_targets)

    def test_sbt_response_schema_exists(self):
        from interfaces.api.schemas.sustainability import ScienceBasedTargetResponse

        fields = ScienceBasedTargetResponse.model_fields
        assert "sbt_status" in fields
        assert "target_reduction_percent" in fields
        assert "sbt_framework" in fields

    def test_rollup_summary_response_schema_exists(self):
        from interfaces.api.schemas.sustainability import RollupSummaryResponse

        fields = RollupSummaryResponse.model_fields
        for key in ("entity_type", "entity_id", "organization_ids", "emissions", "objectives"):
            assert key in fields, f"Missing field: {key}"
