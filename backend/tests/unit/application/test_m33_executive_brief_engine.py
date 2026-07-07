"""Unit tests for M33 Executive Brief Engine."""

from __future__ import annotations

from application.copilot.executive_brief_engine import build_executive_brief_payload


def _base(**kwargs) -> dict:
    defaults = dict(
        risk_distribution={},
        critical_findings=[],
        open_recommendations=0,
        compliance_gaps=[],
        weak_disclosures=[],
        overdue_actions=[],
        critical_suppliers=[],
    )
    defaults.update(kwargs)
    return defaults


class TestExecutiveBriefEngine:
    def test_returns_required_keys(self):
        result = build_executive_brief_payload(**_base())
        assert "supplier_overview" in result
        assert "key_risks" in result
        assert "compliance_concerns" in result
        assert "reporting_blockers" in result
        assert "recommended_actions" in result
        assert "open_recommendations_total" in result

    def test_supplier_overview_totals(self):
        dist = {"Critical": 2, "High": 5, "Moderate": 3, "Low": 10}
        result = build_executive_brief_payload(**_base(risk_distribution=dist))
        assert result["supplier_overview"]["total"] == 20
        assert result["supplier_overview"]["critical"] == 2
        assert result["supplier_overview"]["high"] == 5

    def test_critical_supplier_names_included(self):
        suppliers = [
            {"supplier_name": "BadCorp", "risk_band": "Critical"},
            {"supplier_name": "HighCorp", "risk_band": "High"},
        ]
        result = build_executive_brief_payload(**_base(critical_suppliers=suppliers))
        names = result["supplier_overview"]["critical_supplier_names"]
        assert "BadCorp" in names
        assert "HighCorp" in names

    def test_key_risks_capped_at_5(self):
        findings = [
            {"id": f"f{i}", "title": f"F{i}", "severity": "Critical", "category": "ESG"}
            for i in range(10)
        ]
        result = build_executive_brief_payload(**_base(critical_findings=findings))
        assert len(result["key_risks"]) <= 5

    def test_compliance_concerns_sorted_by_severity(self):
        gaps = [
            {
                "gap_id": "g1",
                "severity": "Low",
                "regulation_name": "R1",
                "requirement_title": "Req1",
                "remediation_steps": "",
            },
            {
                "gap_id": "g2",
                "severity": "Critical",
                "regulation_name": "R2",
                "requirement_title": "Req2",
                "remediation_steps": "",
            },
        ]
        result = build_executive_brief_payload(**_base(compliance_gaps=gaps))
        if len(result["compliance_concerns"]) >= 2:
            assert result["compliance_concerns"][0]["severity"] == "Critical"

    def test_reporting_blockers_only_weak(self):
        disclosures = [
            {
                "response_id": "d1",
                "is_weak": True,
                "disclosure_status": "Not Started",
                "requirement_title": "T1",
            },
            {
                "response_id": "d2",
                "is_weak": False,
                "disclosure_status": "Approved",
                "requirement_title": "T2",
            },
        ]
        result = build_executive_brief_payload(**_base(weak_disclosures=disclosures))
        blocker_ids = [b["response_id"] for b in result["reporting_blockers"]]
        assert "d1" in blocker_ids
        assert "d2" not in blocker_ids

    def test_recommended_actions_sorted_by_priority(self):
        actions = [
            {"id": "a1", "title": "Low task", "priority": "Low", "days_overdue": 0},
            {"id": "a2", "title": "Critical task", "priority": "Critical", "days_overdue": 5},
        ]
        result = build_executive_brief_payload(**_base(overdue_actions=actions))
        if len(result["recommended_actions"]) >= 2:
            assert result["recommended_actions"][0]["priority"] == "Critical"

    def test_open_recommendations_count(self):
        result = build_executive_brief_payload(**_base(open_recommendations=42))
        assert result["open_recommendations_total"] == 42
