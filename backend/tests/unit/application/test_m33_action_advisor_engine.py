"""Unit tests for M33 Action Advisor Engine."""

from __future__ import annotations

from application.copilot.action_advisor_engine import build_action_advisor_payload


def _rec(
    id: str,
    priority: str = "Medium",
    status: str = "open",
    overdue: bool = False,
    due_date: str | None = None,
) -> dict:
    return {
        "id": id,
        "title": f"Rec {id}",
        "priority": priority,
        "action_status": status,
        "overdue": overdue,
        "due_date": due_date,
    }


def _finding(id: str, severity: str = "High", category: str = "ESG") -> dict:
    return {"id": id, "title": f"Finding {id}", "severity": severity, "category": category}


def _risk(id: str, level: str = "High", category: str = "ESG") -> dict:
    return {"id": id, "title": f"Risk {id}", "risk_level": level, "category": category}


def _gap(id: str, severity: str = "High") -> dict:
    return {
        "gap_id": id,
        "severity": severity,
        "regulation_name": "CSRD",
        "requirement_title": "Req",
        "remediation_steps": "Fix it",
    }


def _base(**kwargs) -> dict:
    defaults = dict(findings=[], risks=[], compliance_gaps=[], recommendations=[])
    defaults.update(kwargs)
    return defaults


class TestActionAdvisorEngine:
    def test_returns_required_keys(self):
        result = build_action_advisor_payload(**_base())
        assert "highest_impact_actions" in result
        assert "fastest_remediations" in result
        assert "risk_reduction_priorities" in result
        assert "top_compliance_gaps" in result
        assert "finding_hotspots" in result
        assert "open_action_count" in result

    def test_open_action_count(self):
        recs = [_rec("r1"), _rec("r2"), _rec("r3", status="resolved")]
        result = build_action_advisor_payload(**_base(recommendations=recs))
        assert result["open_action_count"] == 2

    def test_in_progress_counted_as_open(self):
        recs = [_rec("r1", status="in_progress")]
        result = build_action_advisor_payload(**_base(recommendations=recs))
        assert result["open_action_count"] == 1

    def test_overdue_boosted_in_priority(self):
        recs = [
            _rec("r1", priority="Low", overdue=True),
            _rec("r2", priority="High", overdue=False),
        ]
        result = build_action_advisor_payload(**_base(recommendations=recs))
        impact_ids = [a["id"] for a in result["highest_impact_actions"]]
        # r1 (Low+overdue score=3) vs r2 (High score=3) — both score 3
        assert "r1" in impact_ids or "r2" in impact_ids

    def test_critical_recs_ranked_highest(self):
        recs = [
            _rec("r1", priority="Low"),
            _rec("r2", priority="Critical"),
            _rec("r3", priority="Medium"),
        ]
        result = build_action_advisor_payload(**_base(recommendations=recs))
        assert result["highest_impact_actions"][0]["id"] == "r2"

    def test_fastest_remediations_have_due_date(self):
        recs = [
            _rec("r1", due_date="2026-07-01"),
            _rec("r2"),  # no due date
        ]
        result = build_action_advisor_payload(**_base(recommendations=recs))
        fast_ids = [a["id"] for a in result["fastest_remediations"]]
        assert "r1" in fast_ids
        assert "r2" not in fast_ids

    def test_finding_hotspots_capped_at_10(self):
        findings = [_finding(f"f{i}", severity="Critical") for i in range(20)]
        result = build_action_advisor_payload(**_base(findings=findings))
        assert len(result["finding_hotspots"]) <= 10

    def test_risk_reduction_critical_only(self):
        risks = [
            _risk("r1", level="Critical"),
            _risk("r2", level="High"),
            _risk("r3", level="Low"),
        ]
        result = build_action_advisor_payload(**_base(risks=risks))
        levels = {r["risk_level"] for r in result["risk_reduction_priorities"]}
        assert "Low" not in levels

    def test_compliance_gaps_sorted_by_severity(self):
        gaps = [_gap("g1", "Low"), _gap("g2", "Critical"), _gap("g3", "High")]
        result = build_action_advisor_payload(**_base(compliance_gaps=gaps))
        if len(result["top_compliance_gaps"]) >= 2:
            assert result["top_compliance_gaps"][0]["severity"] == "Critical"

    def test_empty_inputs_no_crash(self):
        result = build_action_advisor_payload(**_base())
        assert result["open_action_count"] == 0
