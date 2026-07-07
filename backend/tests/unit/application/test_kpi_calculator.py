"""Unit tests for M29 KPI Calculator.

All functions are pure; no database or I/O involved.
"""

import pytest

from application.executive.kpi_calculator import (
    KPISnapshot,
    compute_action_effectiveness,
    compute_governance_metrics,
    compute_kpi_trends,
    compute_portfolio_summary,
)

# ── compute_portfolio_summary ─────────────────────────────────────────────────


def _scores(*bands_trends) -> list[dict]:
    """Helper: list of score dicts. Accepts (band, trend, esg, risk) or (band,) tuples."""
    results = []
    for item in bands_trends:
        if isinstance(item, tuple):
            band = item[0]
            trend = item[1] if len(item) > 1 else "Stable"
            esg = item[2] if len(item) > 2 else 60.0
            risk = item[3] if len(item) > 3 else 40.0
        else:
            band, trend, esg, risk = item, "Stable", 60.0, 40.0
        results.append({"risk_band": band, "trend": trend, "esg_score": esg, "risk_score": risk})
    return results


def _summary(**kwargs):
    defaults = dict(
        total_suppliers=10,
        scores=[],
        open_actions=0,
        overdue_actions=0,
        total_actions=0,
        assessments_awaiting_review=0,
        assessments_approved=0,
        critical_findings_total=0,
    )
    defaults.update(kwargs)
    return compute_portfolio_summary(**defaults)


class TestComputePortfolioSummary:
    def test_empty_scores(self):
        s = _summary()
        assert s.scored_suppliers == 0
        assert s.avg_esg_score is None
        assert s.avg_risk_score is None
        assert s.risk_distribution == {"Low": 0, "Moderate": 0, "High": 0, "Critical": 0}

    def test_band_distribution(self):
        scores = _scores(
            ("Low", "Stable"),
            ("Low", "Stable"),
            ("Moderate", "Stable"),
            ("High", "Stable"),
            ("Critical", "Stable"),
        )
        s = _summary(scores=scores, total_suppliers=5)
        assert s.low_risk_suppliers == 2
        assert s.moderate_risk_suppliers == 1
        assert s.high_risk_suppliers == 1
        assert s.critical_risk_suppliers == 1
        assert s.scored_suppliers == 5

    def test_trend_counts(self):
        scores = _scores(
            ("Low", "Improving"),
            ("Low", "Improving"),
            ("High", "Deteriorating"),
            ("Moderate", "Stable"),
        )
        s = _summary(scores=scores)
        assert s.improving_suppliers == 2
        assert s.deteriorating_suppliers == 1

    def test_avg_esg_and_risk_rounded(self):
        scores = [
            {"risk_band": "Low", "trend": "Stable", "esg_score": 70.0, "risk_score": 30.0},
            {"risk_band": "Low", "trend": "Stable", "esg_score": 80.0, "risk_score": 50.0},
        ]
        s = _summary(scores=scores)
        assert s.avg_esg_score == 75.0
        assert s.avg_risk_score == 40.0

    def test_resolution_rate_zero_actions(self):
        s = _summary(open_actions=0, total_actions=0)
        assert s.resolution_rate is None

    def test_resolution_rate_computed(self):
        s = _summary(open_actions=3, total_actions=10)
        # closed = 10 - 3 = 7; rate = 0.7
        assert s.resolution_rate == pytest.approx(0.7, abs=0.001)

    def test_all_actions_open(self):
        s = _summary(open_actions=5, total_actions=5)
        assert s.resolution_rate == 0.0

    def test_passes_through_governance_fields(self):
        s = _summary(
            assessments_awaiting_review=3,
            assessments_approved=7,
            critical_findings_total=2,
        )
        assert s.assessments_awaiting_review == 3
        assert s.assessments_approved == 7
        assert s.critical_findings_total == 2

    def test_total_suppliers_not_bounded_by_scores(self):
        # total_suppliers can exceed scored_suppliers (unscored suppliers)
        s = _summary(total_suppliers=20, scores=_scores("Low"))
        assert s.total_suppliers == 20
        assert s.scored_suppliers == 1


# ── compute_kpi_trends ────────────────────────────────────────────────────────


def _row(month, avg_esg=70.0, avg_risk=40.0, count=5, **dist_kwargs):
    dist = {"Low": 2, "Moderate": 2, "High": 1, "Critical": 0}
    dist.update(dist_kwargs)
    return {"month": month, "avg_esg": avg_esg, "avg_risk": avg_risk, "count": count, "dist": dist}


class TestComputeKpiTrends:
    def test_empty_rows(self):
        r = compute_kpi_trends([], period_days=30)
        assert r.data_points == []
        assert r.esg_delta is None
        assert r.risk_delta is None

    def test_single_row_no_delta(self):
        r = compute_kpi_trends([_row("2026-01")], period_days=30)
        assert len(r.data_points) == 1
        assert r.esg_delta is None
        assert r.risk_delta is None

    def test_two_rows_delta_computed(self):
        rows = [
            _row("2026-01", avg_esg=60.0, avg_risk=50.0),
            _row("2026-02", avg_esg=70.0, avg_risk=40.0),
        ]
        r = compute_kpi_trends(rows, period_days=90)
        assert r.esg_delta == pytest.approx(10.0)
        assert r.risk_delta == pytest.approx(-10.0)

    def test_rows_sorted_by_month(self):
        rows = [_row("2026-03"), _row("2026-01"), _row("2026-02")]
        r = compute_kpi_trends(rows, period_days=90)
        months = [p.month for p in r.data_points]
        assert months == ["2026-01", "2026-02", "2026-03"]

    def test_period_days_passed_through(self):
        r = compute_kpi_trends([], period_days=365)
        assert r.period_days == 365

    def test_data_point_fields_correct(self):
        row = _row("2026-05", avg_esg=75.5, avg_risk=35.0, count=8, High=2, Critical=1)
        r = compute_kpi_trends([row], period_days=30)
        p = r.data_points[0]
        assert p.month == "2026-05"
        assert p.avg_esg_score == 75.5
        assert p.avg_risk_score == 35.0
        assert p.supplier_count == 8
        assert p.high_risk_count == 2
        assert p.critical_risk_count == 1

    def test_none_esg_in_row_no_delta(self):
        rows = [
            {"month": "2026-01", "avg_esg": None, "avg_risk": 40.0, "count": 3, "dist": {}},
            {"month": "2026-02", "avg_esg": 70.0, "avg_risk": 35.0, "count": 3, "dist": {}},
        ]
        r = compute_kpi_trends(rows, period_days=60)
        assert r.esg_delta is None
        assert r.risk_delta == pytest.approx(-5.0)

    def test_current_snapshot_passed_through(self):
        snap = KPISnapshot(total_suppliers=5, scored_suppliers=5)
        r = compute_kpi_trends([], period_days=30, current_snapshot=snap)
        assert r.current_snapshot is snap

    def test_delta_rounded_to_one_decimal(self):
        rows = [_row("2026-01", avg_esg=66.666), _row("2026-02", avg_esg=70.001)]
        r = compute_kpi_trends(rows, period_days=30)
        # 70.001 - 66.666 = 3.335 → rounds to 3.3 or 3.4 (one decimal)
        assert abs(r.esg_delta - round(70.001 - 66.666, 1)) < 0.01


# ── compute_action_effectiveness ──────────────────────────────────────────────


class TestComputeActionEffectiveness:
    def test_resolution_rate_computed(self):
        r = compute_action_effectiveness(
            opened_this_period=7,
            closed_this_period=3,
            total_open=4,
            total_overdue=1,
            avg_resolution_days=5.0,
        )
        # 3 / (7 + 3) = 0.3
        assert r["resolution_rate"] == pytest.approx(0.3, abs=0.001)
        assert r["avg_resolution_days"] == 5.0

    def test_zero_period_actions_resolution_none(self):
        r = compute_action_effectiveness(0, 0, 5, 2, None)
        assert r["resolution_rate"] is None

    def test_all_closed_rate_one(self):
        r = compute_action_effectiveness(0, 10, 0, 0, None)
        assert r["resolution_rate"] == pytest.approx(1.0)

    def test_all_fields_present(self):
        r = compute_action_effectiveness(1, 2, 3, 4, 6.5)
        assert set(r.keys()) == {
            "opened_this_period",
            "closed_this_period",
            "total_open",
            "total_overdue",
            "resolution_rate",
            "avg_resolution_days",
        }


# ── compute_governance_metrics ────────────────────────────────────────────────


class TestComputeGovernanceMetrics:
    def test_rates_computed(self):
        r = compute_governance_metrics(
            total_decisions=10,
            approved=6,
            rejected=2,
            changes_requested=2,
            avg_review_days=3.5,
        )
        assert r["approval_rate"] == pytest.approx(0.6, abs=0.001)
        assert r["rejection_rate"] == pytest.approx(0.2, abs=0.001)
        assert r["changes_requested_rate"] == pytest.approx(0.2, abs=0.001)
        assert r["avg_review_days"] == 3.5

    def test_zero_decisions_rates_none(self):
        r = compute_governance_metrics(0, 0, 0, 0, None)
        assert r["approval_rate"] is None
        assert r["rejection_rate"] is None
        assert r["changes_requested_rate"] is None

    def test_all_approved(self):
        r = compute_governance_metrics(5, 5, 0, 0, None)
        assert r["approval_rate"] == pytest.approx(1.0)
        assert r["rejection_rate"] == pytest.approx(0.0)

    def test_all_fields_present(self):
        r = compute_governance_metrics(1, 1, 0, 0, None)
        assert set(r.keys()) == {
            "total_review_decisions",
            "approved",
            "rejected",
            "changes_requested",
            "approval_rate",
            "rejection_rate",
            "changes_requested_rate",
            "avg_review_days",
        }

    def test_passes_through_counts(self):
        r = compute_governance_metrics(
            total_decisions=7, approved=4, rejected=2, changes_requested=1, avg_review_days=None
        )
        assert r["total_review_decisions"] == 7
        assert r["approved"] == 4
        assert r["rejected"] == 2
        assert r["changes_requested"] == 1
