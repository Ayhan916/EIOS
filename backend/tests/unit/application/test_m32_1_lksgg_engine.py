"""Unit tests for M32.1 LkSG Annual Report Engine."""

from __future__ import annotations

import pytest

from application.due_diligence.lksgg_engine import (
    build_lksgg_report,
    _is_hr,
    _is_env,
)


def _supplier(id: str = "s1", tier: str = "Tier 1", country: str = "Germany") -> dict:
    return {"id": id, "name": f"Supplier {id}", "tier": tier, "country": country, "industry": "Manufacturing", "status": "Active"}


def _score(supplier_id: str = "s1", risk_band: str = "Low", risk_score: float = 10.0, esg_score: float = 80.0) -> tuple[str, dict]:
    return supplier_id, {"esg_score": esg_score, "risk_score": risk_score, "risk_band": risk_band, "trend": "Stable"}


def _finding(id: str = "f1", severity: str = "High", category: str = "Environmental", supplier_id: str = "s1") -> dict:
    return {"id": id, "title": f"Finding {id}", "severity": severity, "category": category, "supplier_id": supplier_id}


def _rec(id: str = "r1", status: str = "open", priority: str = "High", overdue: bool = False) -> dict:
    return {"id": id, "title": f"Rec {id}", "action_status": status, "priority": priority, "supplier_id": "s1", "overdue": overdue}


def _base_args(**kwargs) -> dict:
    args = {
        "organization_id": "org-1",
        "reporting_year": 2025,
        "suppliers": [],
        "supplier_scores": {},
        "findings": [],
        "risks": [],
        "recommendations": [],
        "compliance_gaps": [],
        "controls": [],
        "evidence_items": [],
    }
    args.update(kwargs)
    return args


class TestLksggEngineStructure:
    def test_empty_inputs_returns_valid_structure(self):
        result = build_lksgg_report(**_base_args())
        assert "meta" in result
        assert "supplier_inventory" in result
        assert "risk_classification" in result
        assert "human_rights" in result
        assert "environmental" in result
        assert "remediation" in result
        assert "explainability" in result

    def test_meta_fields(self):
        result = build_lksgg_report(**_base_args(organization_id="org-abc", reporting_year=2024))
        assert result["meta"]["framework"] == "LkSG"
        assert result["meta"]["framework_version"] == "2023"
        assert result["meta"]["organization_id"] == "org-abc"
        assert result["meta"]["reporting_year"] == 2024

    def test_explainability_always_present(self):
        result = build_lksgg_report(**_base_args())
        assert isinstance(result["explainability"], list)
        assert len(result["explainability"]) > 0
        for item in result["explainability"]:
            assert "factor" in item
            assert "description" in item


class TestLksggSupplierInventory:
    def test_supplier_count(self):
        suppliers = [_supplier("s1", "Tier 1"), _supplier("s2", "Tier 2"), _supplier("s3", "Tier 1")]
        result = build_lksgg_report(**_base_args(suppliers=suppliers))
        assert result["supplier_inventory"]["total"] == 3
        assert result["supplier_inventory"]["by_tier"]["Tier 1"] == 2
        assert result["supplier_inventory"]["by_tier"]["Tier 2"] == 1

    def test_empty_suppliers(self):
        result = build_lksgg_report(**_base_args())
        assert result["supplier_inventory"]["total"] == 0
        assert result["supplier_inventory"]["active"] == 0


class TestLksggRiskClassification:
    def test_risk_band_counts(self):
        suppliers = [_supplier("s1"), _supplier("s2"), _supplier("s3")]
        scores = dict([
            _score("s1", "Critical", 90.0),
            _score("s2", "High", 70.0),
            _score("s3", "Low", 5.0),
        ])
        result = build_lksgg_report(**_base_args(suppliers=suppliers, supplier_scores=scores))
        assert result["risk_classification"]["Critical"] == 1
        assert result["risk_classification"]["High"] == 1
        assert result["risk_classification"]["Low"] == 1

    def test_supplier_without_score_defaults_to_low(self):
        suppliers = [_supplier("s1")]
        result = build_lksgg_report(**_base_args(suppliers=suppliers, supplier_scores={}))
        assert result["risk_classification"]["Low"] == 1


class TestLksggCriticalSuppliers:
    def test_critical_and_high_included(self):
        suppliers = [_supplier("s1"), _supplier("s2"), _supplier("s3")]
        scores = dict([
            _score("s1", "Critical", 95.0),
            _score("s2", "High", 70.0),
            _score("s3", "Low", 5.0),
        ])
        result = build_lksgg_report(**_base_args(suppliers=suppliers, supplier_scores=scores))
        ids = {s["supplier_id"] for s in result["critical_suppliers"]}
        assert "s1" in ids
        assert "s2" in ids
        assert "s3" not in ids

    def test_sorted_by_risk_score_desc(self):
        suppliers = [_supplier("s1"), _supplier("s2")]
        scores = dict([_score("s1", "Critical", 95.0), _score("s2", "Critical", 80.0)])
        result = build_lksgg_report(**_base_args(suppliers=suppliers, supplier_scores=scores))
        assert result["critical_suppliers"][0]["risk_score"] >= result["critical_suppliers"][1]["risk_score"]


class TestLksggHumanRightsClassification:
    def test_hr_findings_counted(self):
        findings = [
            _finding("f1", "High", "labour"),
            _finding("f2", "Critical", "health"),
            _finding("f3", "Medium", "Environmental"),
        ]
        result = build_lksgg_report(**_base_args(findings=findings))
        assert result["human_rights"]["total_findings"] >= 2

    def test_env_findings_counted(self):
        findings = [
            _finding("f1", "High", "emissions"),
            _finding("f2", "Critical", "pollution"),
            _finding("f3", "Medium", "workforce"),
        ]
        result = build_lksgg_report(**_base_args(findings=findings))
        assert result["environmental"]["total_findings"] >= 2


class TestLksggRemediation:
    def test_open_and_resolved_counts(self):
        recs = [
            _rec("r1", "open"),
            _rec("r2", "in_progress"),
            _rec("r3", "resolved"),
            _rec("r4", "verified"),
        ]
        result = build_lksgg_report(**_base_args(recommendations=recs))
        assert result["remediation"]["open"] == 1
        assert result["remediation"]["in_progress"] == 1
        assert result["remediation"]["resolved"] == 2
        assert result["remediation"]["total"] == 4

    def test_overdue_counted(self):
        recs = [_rec("r1", "open", overdue=True), _rec("r2", "open", overdue=False)]
        result = build_lksgg_report(**_base_args(recommendations=recs))
        assert result["remediation"]["overdue"] == 1

    def test_closure_rate(self):
        recs = [_rec("r1", "resolved"), _rec("r2", "open")]
        result = build_lksgg_report(**_base_args(recommendations=recs))
        assert result["remediation"]["closure_rate"] == pytest.approx(0.5)

    def test_empty_recommendations_closure_rate_zero(self):
        result = build_lksgg_report(**_base_args())
        assert result["remediation"]["closure_rate"] == 0.0


class TestIsHrAndIsEnv:
    def test_hr_category_detected(self):
        assert _is_hr({"title": "Child Labour Risk", "category": "social"})

    def test_env_category_detected(self):
        assert _is_env({"title": "CO2 emissions", "category": "environmental"})

    def test_non_hr_not_detected(self):
        assert not _is_hr({"title": "IT Security", "category": "technology"})

    def test_non_env_not_detected(self):
        assert not _is_env({"title": "Discrimination claim", "category": "social"})
