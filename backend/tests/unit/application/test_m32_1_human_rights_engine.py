"""Unit tests for M32.1 Human Rights Report Engine."""

from __future__ import annotations

from application.due_diligence.human_rights_engine import (
    _TOPIC_KEYWORDS,
    _classify_finding,
    build_human_rights_report,
)


def _finding(id: str, title: str = "", category: str = "", severity: str = "High") -> dict:
    return {
        "id": id,
        "title": title,
        "category": category,
        "severity": severity,
        "supplier_id": "s1",
        "description": "",
    }


def _base_args(**kwargs) -> dict:
    base = {
        "organization_id": "org-1",
        "findings": [],
        "risks": [],
        "recommendations": [],
        "evidence_items": [],
        "controls": [],
    }
    base.update(kwargs)
    return base


class TestHumanRightsEngineStructure:
    def test_empty_returns_valid_structure(self):
        result = build_human_rights_report(**_base_args())
        assert "meta" in result
        assert "summary" in result
        assert "by_topic" in result
        assert "remediation" in result

    def test_by_topic_covers_all_topics(self):
        result = build_human_rights_report(**_base_args())
        topic_names = {t["topic"] for t in result["by_topic"]}
        for topic in _TOPIC_KEYWORDS:
            assert topic in topic_names

    def test_topic_has_required_fields(self):
        result = build_human_rights_report(**_base_args())
        for t in result["by_topic"]:
            assert "topic" in t
            assert "display_name" in t
            assert "finding_count" in t
            assert "critical_findings" in t
            assert "suppliers_impacted" in t


class TestHumanRightsClassification:
    def test_child_labour_classified(self):
        finding = _finding("f1", title="Child labour in textile supplier")
        topics = _classify_finding(finding)
        assert "child_labour" in topics

    def test_forced_labour_classified(self):
        finding = _finding("f1", title="Forced labor conditions identified")
        topics = _classify_finding(finding)
        assert "forced_labour" in topics

    def test_health_safety_classified(self):
        finding = _finding("f1", title="Safety equipment not provided", category="health")
        topics = _classify_finding(finding)
        assert "health_safety" in topics

    def test_living_wage_classified(self):
        finding = _finding("f1", title="Below minimum wage compensation")
        topics = _classify_finding(finding)
        assert "living_wage" in topics

    def test_freedom_of_association_classified(self):
        finding = _finding("f1", title="Union busting activities")
        topics = _classify_finding(finding)
        assert "freedom_of_association" in topics

    def test_working_conditions_classified(self):
        finding = _finding("f1", title="Excessive overtime hours", category="working conditions")
        topics = _classify_finding(finding)
        assert "working_conditions" in topics

    def test_no_match_returns_other(self):
        finding = _finding("f1", title="IT system vulnerability")
        topics = _classify_finding(finding)
        assert "other" in topics

    def test_multi_topic_finding(self):
        finding = _finding("f1", title="Child labour health and safety risk")
        topics = _classify_finding(finding)
        assert len(topics) >= 2
        assert "child_labour" in topics
        assert "health_safety" in topics


class TestHumanRightsSummary:
    def test_total_hr_findings_counted(self):
        findings = [
            _finding("f1", title="Child labour issue"),
            _finding("f2", title="Health and safety violation"),
            _finding("f3", title="IT infrastructure gap"),  # not HR
        ]
        result = build_human_rights_report(**_base_args(findings=findings))
        # f1 and f2 are HR topics
        assert result["summary"]["total_hr_findings"] >= 2

    def test_suppliers_impacted(self):
        findings = [
            {
                "id": "f1",
                "title": "child labour",
                "category": "",
                "severity": "High",
                "supplier_id": "s1",
                "description": "",
            },
            {
                "id": "f2",
                "title": "health hazard",
                "category": "",
                "severity": "High",
                "supplier_id": "s2",
                "description": "",
            },
        ]
        result = build_human_rights_report(**_base_args(findings=findings))
        assert result["summary"]["suppliers_impacted"] >= 2


class TestHumanRightsRemediation:
    def test_remediation_counts(self):
        recs = [
            {
                "id": "r1",
                "title": "Fix",
                "action_status": "open",
                "supplier_id": "s1",
                "priority": "High",
                "overdue": False,
            },
            {
                "id": "r2",
                "title": "Fix",
                "action_status": "resolved",
                "supplier_id": "s1",
                "priority": "Medium",
                "overdue": False,
            },
            {
                "id": "r3",
                "title": "Fix",
                "action_status": "in_progress",
                "supplier_id": "s1",
                "priority": "Low",
                "overdue": True,
            },
        ]
        result = build_human_rights_report(**_base_args(recommendations=recs))
        assert result["remediation"]["open"] == 1
        assert result["remediation"]["resolved"] == 1
        assert result["remediation"]["overdue"] == 1
