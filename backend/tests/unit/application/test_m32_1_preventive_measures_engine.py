"""Unit tests for M32.1 Preventive Measures Register Engine."""

from __future__ import annotations

import pytest

from application.due_diligence.preventive_measures_engine import (
    build_preventive_measures_report,
    _classify_control,
    _assign_effectiveness,
)


def _control(
    id: str,
    title: str = "Control",
    control_type: str = "Preventive",
    effectiveness: float | None = 0.8,
) -> dict:
    return {
        "id": id,
        "title": title,
        "description": "",
        "control_type": control_type,
        "effectiveness": effectiveness,
        "status": "Active",
    }


def _base_args(**kwargs) -> dict:
    base = {"organization_id": "org-1", "controls": []}
    base.update(kwargs)
    return base


class TestPreventiveMeasuresStructure:
    def test_empty_returns_valid_structure(self):
        result = build_preventive_measures_report(**_base_args())
        assert "meta" in result
        assert "summary" in result
        assert "by_category" in result

    def test_summary_fields(self):
        result = build_preventive_measures_report(**_base_args())
        s = result["summary"]
        assert "total_controls" in s
        assert "preventive" in s
        assert "detective" in s
        assert "corrective" in s
        assert "by_effectiveness" in s


class TestControlTypeBreakdown:
    def test_preventive_counted(self):
        controls = [_control("c1", control_type="Preventive")]
        result = build_preventive_measures_report(**_base_args(controls=controls))
        assert result["summary"]["preventive"] == 1

    def test_detective_counted(self):
        controls = [_control("c1", control_type="Detective")]
        result = build_preventive_measures_report(**_base_args(controls=controls))
        assert result["summary"]["detective"] == 1

    def test_corrective_counted(self):
        controls = [_control("c1", control_type="Corrective")]
        result = build_preventive_measures_report(**_base_args(controls=controls))
        assert result["summary"]["corrective"] == 1

    def test_total_includes_all_types(self):
        controls = [
            _control("c1", control_type="Preventive"),
            _control("c2", control_type="Detective"),
            _control("c3", control_type="Corrective"),
        ]
        result = build_preventive_measures_report(**_base_args(controls=controls))
        assert result["summary"]["total_controls"] == 3


class TestControlCategoryClassification:
    def test_policy_classified(self):
        assert _classify_control({"title": "Human Rights Policy", "description": ""}) == "policy"

    def test_supplier_control_classified(self):
        assert _classify_control({"title": "Supplier Due Diligence Process", "description": ""}) == "supplier_control"

    def test_training_classified(self):
        assert _classify_control({"title": "Employee Training Program", "description": ""}) == "training"

    def test_monitoring_classified(self):
        assert _classify_control({"title": "ESG KPI Monitoring", "description": ""}) == "monitoring"

    def test_audit_classified(self):
        assert _classify_control({"title": "Annual Site Audit", "description": ""}) == "audit"

    def test_certification_classified(self):
        assert _classify_control({"title": "ISO 14001 Certification", "description": ""}) == "certification"

    def test_unclassified_returns_other(self):
        assert _classify_control({"title": "General measure XYZ", "description": ""}) == "other"


class TestEffectivenessAssignment:
    def test_high_effectiveness_is_effective(self):
        assert _assign_effectiveness({"effectiveness": 0.9}) == "Effective"

    def test_threshold_075_is_effective(self):
        assert _assign_effectiveness({"effectiveness": 0.75}) == "Effective"

    def test_moderate_effectiveness_is_partially(self):
        assert _assign_effectiveness({"effectiveness": 0.6}) == "Partially Effective"

    def test_threshold_040_is_partially(self):
        assert _assign_effectiveness({"effectiveness": 0.4}) == "Partially Effective"

    def test_low_effectiveness_is_ineffective(self):
        assert _assign_effectiveness({"effectiveness": 0.2}) == "Ineffective"

    def test_none_effectiveness_is_unknown(self):
        assert _assign_effectiveness({"effectiveness": None}) == "Unknown"


class TestByCategoryOutput:
    def test_category_summaries_present(self):
        controls = [
            _control("c1", "Annual Audit of Suppliers"),
            _control("c2", "HR Policy document"),
        ]
        result = build_preventive_measures_report(**_base_args(controls=controls))
        categories = {c["category"] for c in result["by_category"]}
        assert "audit" in categories or "policy" in categories

    def test_items_in_category(self):
        controls = [_control("c1", "Code of Conduct Policy")]
        result = build_preventive_measures_report(**_base_args(controls=controls))
        policy_cat = next((c for c in result["by_category"] if c["category"] == "policy"), None)
        assert policy_cat is not None
        assert len(policy_cat["items"]) == 1
        assert policy_cat["items"][0]["id"] == "c1"

    def test_effectiveness_breakdown_in_category(self):
        controls = [
            _control("c1", "Supplier audit", effectiveness=0.9),
            _control("c2", "Supplier inspection", effectiveness=0.1),
        ]
        result = build_preventive_measures_report(**_base_args(controls=controls))
        cat = next((c for c in result["by_category"] if c["category"] == "audit"), None)
        if cat:
            eff = cat["by_effectiveness"]
            assert "Effective" in eff or "Ineffective" in eff
