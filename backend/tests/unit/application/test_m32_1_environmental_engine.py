"""Unit tests for M32.1 Environmental Risk Report Engine."""

from __future__ import annotations

import pytest

from application.due_diligence.environmental_engine import (
    build_environmental_report,
    _classify_finding,
    _TOPIC_KEYWORDS,
)


def _finding(id: str, title: str = "", category: str = "", severity: str = "High") -> dict:
    return {"id": id, "title": title, "category": category, "severity": severity, "supplier_id": "s1", "description": ""}


def _control(id: str, title: str = "Env control", effectiveness: float | None = 0.8) -> dict:
    return {"id": id, "title": title, "control_type": "Preventive", "effectiveness": effectiveness, "status": "Active", "description": ""}


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


class TestEnvironmentalEngineStructure:
    def test_empty_returns_valid_structure(self):
        result = build_environmental_report(**_base_args())
        assert "meta" in result
        assert "summary" in result
        assert "by_topic" in result
        assert "mitigation" in result
        assert "remediation" in result

    def test_by_topic_covers_all_env_topics(self):
        result = build_environmental_report(**_base_args())
        topic_names = {t["topic"] for t in result["by_topic"]}
        for topic in _TOPIC_KEYWORDS:
            assert topic in topic_names


class TestEnvironmentalClassification:
    def test_emissions_classified(self):
        finding = _finding("f1", title="CO2 emissions exceed limit", category="emissions")
        topics = _classify_finding(finding)
        assert "emissions" in topics

    def test_pollution_classified(self):
        finding = _finding("f1", title="Chemical contamination found")
        topics = _classify_finding(finding)
        assert "pollution" in topics

    def test_waste_classified(self):
        finding = _finding("f1", title="Improper waste disposal")
        topics = _classify_finding(finding)
        assert "waste" in topics

    def test_biodiversity_classified(self):
        finding = _finding("f1", title="Deforestation in sourcing region")
        topics = _classify_finding(finding)
        assert "biodiversity" in topics

    def test_water_classified(self):
        finding = _finding("f1", title="Water discharge exceeds limits", category="water")
        topics = _classify_finding(finding)
        assert "water" in topics

    def test_climate_classified(self):
        finding = _finding("f1", title="Climate risk assessment required")
        topics = _classify_finding(finding)
        assert "climate" in topics

    def test_non_env_returns_other(self):
        finding = _finding("f1", title="Workforce discrimination")
        topics = _classify_finding(finding)
        assert "other" in topics


class TestEnvironmentalSummary:
    def test_total_env_findings(self):
        findings = [
            _finding("f1", title="Carbon emissions"),
            _finding("f2", title="Water pollution"),
            _finding("f3", title="child labour"),  # HR, not env
        ]
        result = build_environmental_report(**_base_args(findings=findings))
        assert result["summary"]["total_env_findings"] >= 2

    def test_unresolved_risks_counted(self):
        risks = [
            {"id": "r1", "title": "emissions risk", "risk_level": "Critical", "category": "emissions", "supplier_id": "s1"},
            {"id": "r2", "title": "flood risk", "risk_level": "High", "category": "climate", "supplier_id": "s1"},
            {"id": "r3", "title": "low risk", "risk_level": "Low", "category": "water", "supplier_id": "s1"},
        ]
        result = build_environmental_report(**_base_args(risks=risks))
        assert result["summary"]["unresolved_risks"] >= 2


class TestEnvironmentalMitigation:
    def test_effective_controls_counted(self):
        controls = [
            _control("c1", title="Carbon emission monitoring", effectiveness=0.9),
            _control("c2", title="Water treatment program", effectiveness=0.5),
            _control("c3", title="Climate adaptation plan", effectiveness=0.3),
        ]
        result = build_environmental_report(**_base_args(controls=controls))
        assert result["mitigation"]["effective"] >= 1
        assert result["mitigation"]["partially_effective"] >= 1

    def test_unknown_effectiveness_controls(self):
        controls = [_control("c1", title="Carbon policy", effectiveness=None)]
        result = build_environmental_report(**_base_args(controls=controls))
        assert result["mitigation"]["unknown"] >= 1
