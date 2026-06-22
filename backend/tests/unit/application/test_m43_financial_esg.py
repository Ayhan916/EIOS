"""M43 Financial ESG — unit tests.

Tests cover:
1. Carbon economics (cost formula, risk composite)
2. Taxonomy (alignment %, eligible %, status lock)
3. Green revenue (green %, capex/opex validation)
4. Rollup (org_id lookup, aggregation, empty org)
5. Valuation (total = sum of 3 components)
6. Finance linkage (covenant evaluation)
7. Report immutability (finalize once, conflict on re-finalize)
8. Tenant isolation (_assert_org raises for cross-org)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)


def _session():
    return MagicMock()


# ── 1. Carbon Economics ───────────────────────────────────────────────────────

class TestCarbonEconomics:
    def test_compute_carbon_cost_formula(self):
        from application.financial_esg.carbon_cost_service import _compute_carbon_cost
        result = _compute_carbon_cost(
            total_emissions=1000.0,
            internal_carbon_price=50.0,
            regulatory_carbon_price=75.0,
            avoided_emissions=100.0,
        )
        assert result["total_carbon_cost"] == 1000.0 * 50.0
        assert result["regulatory_exposure"] == 1000.0 * 75.0
        assert result["avoided_cost"] == 100.0 * 50.0

    def test_compute_carbon_cost_zero_avoided(self):
        from application.financial_esg.carbon_cost_service import _compute_carbon_cost
        result = _compute_carbon_cost(
            total_emissions=500.0,
            internal_carbon_price=30.0,
            regulatory_carbon_price=40.0,
            avoided_emissions=0.0,
        )
        assert result["avoided_cost"] == 0.0
        assert result["total_carbon_cost"] == 15_000.0

    def test_compute_carbon_cost_formula_stored(self):
        from application.financial_esg.carbon_cost_service import _compute_carbon_cost
        result = _compute_carbon_cost(100.0, 50.0, 60.0, 10.0)
        assert "formula" in result
        assert isinstance(result["formula"], dict)

    def test_risk_composite_formula(self):
        from application.financial_esg.risk_service import _compute_risk
        result = _compute_risk(
            supplier_risk=80.0,
            climate_risk=60.0,
            compliance_risk=40.0,
            operational_risk=20.0,
            exposure_base=1_000_000.0,
        )
        expected = 80 * 0.30 + 60 * 0.30 + 40 * 0.20 + 20 * 0.20
        assert abs(result["composite_risk_score"] - expected) < 0.01

    def test_risk_composite_validates_range(self):
        from application.financial_esg.risk_service import _compute_risk
        from application.financial_esg.kpi_service import FinancialESGError
        with pytest.raises(FinancialESGError):
            _compute_risk(150.0, 60.0, 40.0, 20.0, 1_000_000.0)

    def test_risk_expected_loss_formula(self):
        from application.financial_esg.risk_service import _compute_risk
        result = _compute_risk(50.0, 50.0, 50.0, 50.0, 1_000_000.0)
        composite = 50.0
        expected_loss = round(1_000_000.0 * (composite / 100.0), 6) * (composite / 100.0)
        assert abs(result["expected_loss"] - expected_loss) < 0.01


# ── 2. Taxonomy ───────────────────────────────────────────────────────────────

class TestTaxonomy:
    def test_compute_percent_basic(self):
        from application.financial_esg.taxonomy_service import _compute_percent
        assert _compute_percent(200.0, 1000.0) == 20.0

    def test_compute_percent_zero_denominator(self):
        from application.financial_esg.taxonomy_service import _compute_percent
        assert _compute_percent(100.0, 0.0) == 0.0

    def test_taxonomy_status_lock_on_verified(self):
        from application.financial_esg.taxonomy_service import update_assessment_status
        from application.financial_esg.kpi_service import FinancialESGError
        from infrastructure.persistence.models.financial_esg import TaxonomyAlignmentAssessmentModel

        mock_rec = MagicMock(spec=TaxonomyAlignmentAssessmentModel)
        mock_rec.organization_id = "org-1"
        mock_rec.assessment_status = "VERIFIED"

        session = _session()
        session.get.return_value = mock_rec

        with pytest.raises(FinancialESGError, match="Verified"):
            update_assessment_status("id-1", "DRAFT", "user-1", session, organization_id="org-1")

    def test_taxonomy_aligned_activities_sum(self):
        from application.financial_esg.taxonomy_service import _compute_percent
        aligned_activities = {"solar": 300.0, "wind": 200.0}
        total_revenue = 1000.0
        total_aligned = sum(aligned_activities.values())
        pct = _compute_percent(total_aligned, total_revenue)
        assert pct == 50.0


# ── 3. Green Revenue ─────────────────────────────────────────────────────────

class TestGreenRevenue:
    def test_green_revenue_percent_formula(self):
        from application.financial_esg.revenue_service import create_green_revenue
        from infrastructure.persistence.models.financial_esg import GreenRevenueRecordModel

        session = _session()
        captured = {}

        def _add(record):
            captured["rec"] = record

        session.add.side_effect = _add
        session.flush.return_value = None
        session.get.return_value = None

        with patch("application.financial_esg.revenue_service.emit_audit_event"):
            with patch("application.financial_esg.revenue_service.financial_esg_counters"):
                create_green_revenue(
                    "org-1", "Solar Revenue", 200.0, 1000.0, "2024-Q1", "user-1", session
                )

        assert "rec" in captured
        assert captured["rec"].green_revenue_percent == 20.0

    def test_green_capex_alignment_validation(self):
        from application.financial_esg.revenue_service import create_green_capex
        from application.financial_esg.kpi_service import FinancialESGError
        with pytest.raises(FinancialESGError, match="alignment_percent"):
            create_green_capex("org-1", "proj", 100.0, 150.0, "2024", "user-1", _session())

    def test_green_opex_alignment_validation(self):
        from application.financial_esg.revenue_service import create_green_opex
        from application.financial_esg.kpi_service import FinancialESGError
        with pytest.raises(FinancialESGError, match="alignment_percent"):
            create_green_opex("org-1", "desc", 100.0, -5.0, "2024", "user-1", _session())


# ── 4. Rollup ────────────────────────────────────────────────────────────────

class TestRollup:
    def test_rollup_empty_org_list(self):
        from application.financial_esg.rollup_service import (
            _carbon_rollup, _green_revenue_rollup, _taxonomy_rollup,
            _finance_rollup, _value_creation_rollup,
        )
        s = _session()
        assert _carbon_rollup([], s).model_count == 0
        assert _green_revenue_rollup([], s).record_count == 0
        assert _taxonomy_rollup([], s).assessment_count == 0
        assert _finance_rollup([], s).instrument_count == 0
        assert _value_creation_rollup([], s).initiative_count == 0

    def test_rollup_invalid_entity_type(self):
        from application.financial_esg.rollup_service import compute_financial_rollup
        from application.financial_esg.kpi_service import FinancialESGError
        with pytest.raises(FinancialESGError, match="entity_type"):
            compute_financial_rollup("invalid_type", "entity-1", "actor-1", _session())

    def test_rollup_org_lookup_by_enterprise(self):
        from application.financial_esg.rollup_service import _org_ids_for_entity
        from infrastructure.persistence.models.organization import OrganizationModel

        session = _session()
        mock_rows = [MagicMock(id="org-1"), MagicMock(id="org-2")]
        session.query.return_value.filter.return_value.all.return_value = mock_rows

        ids = _org_ids_for_entity("enterprise", "ent-999", session)
        assert ids == ["org-1", "org-2"]

    def test_rollup_carbon_aggregates(self):
        from application.financial_esg.rollup_service import _carbon_rollup

        session = _session()
        mock_row = MagicMock()
        mock_row.cost = 50_000.0
        mock_row.reg = 75_000.0
        mock_row.avoided = 5_000.0
        mock_row.cnt = 3
        session.query.return_value.filter.return_value.one.return_value = mock_row

        result = _carbon_rollup(["org-1", "org-2"], session)
        assert result.total_carbon_cost == 50_000.0
        assert result.model_count == 3


# ── 5. Valuation ─────────────────────────────────────────────────────────────

class TestValuation:
    def test_valuation_total_is_sum(self):
        from application.financial_esg.value_service import create_sustainability_valuation

        session = _session()
        captured = {}

        def _add(record):
            captured["rec"] = record

        session.add.side_effect = _add
        session.flush.return_value = None

        with patch("application.financial_esg.value_service.emit_audit_event"):
            create_sustainability_valuation(
                "org-1", "2024 Valuation", 2024,
                risk_reduction_value=100_000.0,
                carbon_reduction_value=200_000.0,
                operational_efficiency_value=50_000.0,
                actor_id="user-1",
                session=session,
            )

        assert captured["rec"].total_sustainability_value == 350_000.0

    def test_climate_finance_roi_formula(self):
        from application.financial_esg.value_service import _compute_roi
        roi = _compute_roi(realized=150.0, investment=100.0)
        assert roi == 50.0

    def test_climate_finance_roi_zero_investment(self):
        from application.financial_esg.value_service import _compute_roi
        assert _compute_roi(realized=100.0, investment=0.0) is None

    def test_climate_finance_roi_negative(self):
        from application.financial_esg.value_service import _compute_roi
        roi = _compute_roi(realized=50.0, investment=100.0)
        assert roi == -50.0


# ── 6. Finance Linkage ───────────────────────────────────────────────────────

class TestFinanceLinkage:
    def test_covenant_compliant_below(self):
        from application.financial_esg.finance_service import _evaluate_covenant
        status = _evaluate_covenant(
            threshold_value=50.0,
            threshold_direction="BELOW",
            current_value=40.0,
        )
        assert status == "COMPLIANT"

    def test_covenant_at_risk_below(self):
        from application.financial_esg.finance_service import _evaluate_covenant
        status = _evaluate_covenant(
            threshold_value=50.0,
            threshold_direction="BELOW",
            current_value=60.0,
        )
        assert status == "AT_RISK"

    def test_covenant_compliant_above(self):
        from application.financial_esg.finance_service import _evaluate_covenant
        status = _evaluate_covenant(
            threshold_value=50.0,
            threshold_direction="ABOVE",
            current_value=60.0,
        )
        assert status == "COMPLIANT"

    def test_covenant_at_risk_above(self):
        from application.financial_esg.finance_service import _evaluate_covenant
        status = _evaluate_covenant(
            threshold_value=50.0,
            threshold_direction="ABOVE",
            current_value=40.0,
        )
        assert status == "AT_RISK"

    def test_covenant_no_threshold_returns_monitoring(self):
        from application.financial_esg.finance_service import _evaluate_covenant
        status = _evaluate_covenant(
            threshold_value=None,
            threshold_direction="BELOW",
            current_value=100.0,
        )
        assert status == "MONITORING"


# ── 7. Report Immutability ────────────────────────────────────────────────────

class TestReportImmutability:
    def test_finalize_report_sets_is_final(self):
        from application.financial_esg.reporting_service import finalize_financial_esg_report
        from infrastructure.persistence.models.financial_esg import FinancialESGReportModel

        mock_report = MagicMock(spec=FinancialESGReportModel)
        mock_report.organization_id = "org-1"
        mock_report.is_final = False

        session = _session()
        session.get.return_value = mock_report

        with patch("application.financial_esg.reporting_service.emit_audit_event"):
            with patch("application.financial_esg.reporting_service.financial_esg_counters"):
                finalize_financial_esg_report("rep-1", "user-1", session, organization_id="org-1")

        assert mock_report.is_final is True
        assert mock_report.overall_status == "FINAL"

    def test_finalize_report_conflict_on_already_final(self):
        from application.financial_esg.reporting_service import finalize_financial_esg_report
        from application.financial_esg.kpi_service import FinancialESGConflict
        from infrastructure.persistence.models.financial_esg import FinancialESGReportModel

        mock_report = MagicMock(spec=FinancialESGReportModel)
        mock_report.organization_id = "org-1"
        mock_report.is_final = True

        session = _session()
        session.get.return_value = mock_report

        with pytest.raises(FinancialESGConflict, match="already finalized"):
            finalize_financial_esg_report("rep-1", "user-1", session, organization_id="org-1")

    def test_finalize_disclosure_package_conflict(self):
        from application.financial_esg.readiness_service import finalize_disclosure_package
        from application.financial_esg.kpi_service import FinancialESGConflict
        from infrastructure.persistence.models.financial_esg import InvestorDisclosurePackageModel

        mock_pkg = MagicMock(spec=InvestorDisclosurePackageModel)
        mock_pkg.organization_id = "org-1"
        mock_pkg.is_final = True

        session = _session()
        session.get.return_value = mock_pkg

        with pytest.raises(FinancialESGConflict, match="already finalized"):
            finalize_disclosure_package("pkg-1", "user-1", session, organization_id="org-1")


# ── 8. Tenant Isolation ───────────────────────────────────────────────────────

class TestTenantIsolation:
    def test_assert_org_raises_for_wrong_org(self):
        from application.financial_esg.kpi_service import _assert_org, FinancialESGError

        mock_record = MagicMock()
        mock_record.organization_id = "org-A"

        with pytest.raises(FinancialESGError, match="not found"):
            _assert_org(mock_record, "org-B", "KPI")

    def test_assert_org_passes_for_correct_org(self):
        from application.financial_esg.kpi_service import _assert_org

        mock_record = MagicMock()
        mock_record.organization_id = "org-A"

        _assert_org(mock_record, "org-A", "KPI")  # should not raise

    def test_assert_org_raises_for_none_record(self):
        from application.financial_esg.kpi_service import _assert_org, FinancialESGError

        with pytest.raises(FinancialESGError, match="not found"):
            _assert_org(None, "org-A", "KPI")

    def test_covenant_monitor_asserts_org(self):
        from application.financial_esg.finance_service import monitor_covenant
        from application.financial_esg.kpi_service import FinancialESGError
        from infrastructure.persistence.models.financial_esg import FinanceLinkedKPIModel

        mock_rec = MagicMock(spec=FinanceLinkedKPIModel)
        mock_rec.organization_id = "org-CORRECT"

        session = _session()
        session.get.return_value = mock_rec

        with pytest.raises(FinancialESGError):
            monitor_covenant("kpi-1", 42.0, "user-1", session, organization_id="org-WRONG")
