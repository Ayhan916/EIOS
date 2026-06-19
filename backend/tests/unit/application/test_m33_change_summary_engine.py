"""Unit tests for M33 Change Summary Engine."""

from __future__ import annotations

import pytest

from application.copilot.change_summary_engine import build_change_summary


def _state(**kwargs) -> dict:
    base = {
        "critical_findings": 0,
        "critical_risks": 0,
        "open_recommendations": 0,
        "supplier_critical_count": 0,
        "compliance_gap_count": 0,
        "overdue_action_count": 0,
        "disclosure_weak_count": 0,
        "risk_distribution": {},
    }
    base.update(kwargs)
    return base


class TestChangeSummaryEngine:
    def test_no_changes_returns_stable(self):
        result = build_change_summary(_state(), _state())
        assert result["overall_severity"] == "stable"
        assert result["total_changes"] == 0
        assert result["changes"] == []

    def test_critical_finding_increase_is_critical(self):
        result = build_change_summary(
            _state(critical_findings=10),
            _state(critical_findings=0),
        )
        assert result["overall_severity"] == "critical"
        assert any(c["metric"] == "critical_findings" for c in result["changes"])

    def test_decrease_is_improvement(self):
        result = build_change_summary(
            _state(open_recommendations=3),
            _state(open_recommendations=8),
        )
        assert len(result["improvements"]) == 1
        assert result["improvements"][0]["metric"] == "open_recommendations"

    def test_small_increase_is_warning(self):
        result = build_change_summary(
            _state(critical_risks=2),
            _state(critical_risks=0),
        )
        changes = [c for c in result["changes"] if c["metric"] == "critical_risks"]
        assert changes[0]["severity"] == "warning"

    def test_large_increase_is_critical(self):
        result = build_change_summary(
            _state(overdue_action_count=10),
            _state(overdue_action_count=0),
        )
        changes = [c for c in result["changes"] if c["metric"] == "overdue_action_count"]
        assert changes[0]["severity"] == "critical"

    def test_risk_distribution_changes_detected(self):
        result = build_change_summary(
            _state(risk_distribution={"Critical": 5, "High": 3}),
            _state(risk_distribution={"Critical": 2, "High": 3}),
        )
        assert "Critical" in result["risk_distribution_changes"]
        assert result["risk_distribution_changes"]["Critical"] == 3

    def test_new_concerns_populated(self):
        result = build_change_summary(
            _state(compliance_gap_count=7),
            _state(compliance_gap_count=0),
        )
        assert len(result["new_concerns"]) >= 1

    def test_delta_signed(self):
        result = build_change_summary(
            _state(critical_findings=3),
            _state(critical_findings=5),
        )
        changes = [c for c in result["changes"] if c["metric"] == "critical_findings"]
        assert changes[0]["delta"] == -2
        assert changes[0]["direction"] == "decreased"

    def test_empty_states_no_crash(self):
        result = build_change_summary({}, {})
        assert "overall_severity" in result
