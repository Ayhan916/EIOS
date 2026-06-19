"""Unit tests for M32.1 Remediation Tracking Engine."""

from __future__ import annotations

import pytest

from application.due_diligence.remediation_engine import build_remediation_report


def _rec(
    id: str,
    status: str = "open",
    priority: str = "Medium",
    overdue: bool = False,
    supplier_id: str | None = "s1",
    resolution_days: int | None = None,
) -> dict:
    return {
        "id": id,
        "title": f"Rec {id}",
        "action_status": status,
        "priority": priority,
        "overdue": overdue,
        "supplier_id": supplier_id,
        "resolution_days": resolution_days,
        "due_date": None,
    }


def _base_args(**kwargs) -> dict:
    base = {"organization_id": "org-1", "recommendations": []}
    base.update(kwargs)
    return base


class TestRemediationEngineStructure:
    def test_empty_returns_valid_structure(self):
        result = build_remediation_report(**_base_args())
        assert "meta" in result
        assert "summary" in result
        assert "by_priority" in result
        assert "by_supplier" in result
        assert "top_overdue" in result

    def test_meta_fields(self):
        result = build_remediation_report(**_base_args(organization_id="org-test"))
        assert result["meta"]["organization_id"] == "org-test"
        assert result["meta"]["report_type"] == "remediation"


class TestRemediationCounts:
    def test_open_counted(self):
        recs = [_rec("r1", "open"), _rec("r2", "open")]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["open"] == 2

    def test_in_progress_counted(self):
        recs = [_rec("r1", "in_progress")]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["in_progress"] == 1

    def test_completed_includes_resolved_and_verified(self):
        recs = [_rec("r1", "resolved"), _rec("r2", "verified")]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["completed"] == 2

    def test_overdue_counted(self):
        recs = [
            _rec("r1", "open", overdue=True),
            _rec("r2", "in_progress", overdue=True),
            _rec("r3", "open", overdue=False),
        ]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["overdue"] == 2

    def test_resolved_not_counted_as_overdue(self):
        recs = [_rec("r1", "resolved", overdue=True)]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["overdue"] == 0


class TestRemediationClosureRate:
    def test_full_closure(self):
        recs = [_rec("r1", "resolved"), _rec("r2", "verified")]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["closure_rate"] == pytest.approx(1.0)

    def test_partial_closure(self):
        recs = [_rec("r1", "resolved"), _rec("r2", "open")]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["closure_rate"] == pytest.approx(0.5)

    def test_zero_closure_with_no_recs(self):
        result = build_remediation_report(**_base_args())
        assert result["summary"]["closure_rate"] == 0.0


class TestRemediationAvgResolutionDays:
    def test_avg_resolution_days_computed(self):
        recs = [
            _rec("r1", "resolved", resolution_days=10),
            _rec("r2", "resolved", resolution_days=20),
        ]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["avg_resolution_days"] == pytest.approx(15.0)

    def test_no_resolved_items_returns_none(self):
        recs = [_rec("r1", "open")]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["summary"]["avg_resolution_days"] is None


class TestRemediationByPriority:
    def test_priority_breakdown(self):
        recs = [
            _rec("r1", "open", "Critical"),
            _rec("r2", "open", "High"),
            _rec("r3", "resolved", "Medium"),
        ]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["by_priority"]["Critical"]["open"] == 1
        assert result["by_priority"]["High"]["open"] == 1
        assert result["by_priority"]["Medium"]["completed"] == 1

    def test_overdue_in_priority(self):
        recs = [_rec("r1", "open", "Critical", overdue=True)]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert result["by_priority"]["Critical"]["overdue"] == 1


class TestRemediationTopOverdue:
    def test_top_overdue_sorted_by_priority(self):
        recs = [
            _rec("r1", "open", "Low", overdue=True),
            _rec("r2", "open", "Critical", overdue=True),
            _rec("r3", "open", "High", overdue=True),
        ]
        result = build_remediation_report(**_base_args(recommendations=recs))
        top = result["top_overdue"]
        assert top[0]["priority"] == "Critical"
        assert top[1]["priority"] == "High"

    def test_top_overdue_capped_at_10(self):
        recs = [_rec(f"r{i}", "open", overdue=True) for i in range(20)]
        result = build_remediation_report(**_base_args(recommendations=recs))
        assert len(result["top_overdue"]) <= 10
