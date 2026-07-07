"""Unit tests for M32.1 CSDDD Due Diligence Report Engine."""

from __future__ import annotations

from application.due_diligence.csddd_engine import build_csddd_report


def _supplier(id: str = "s1", country: str = "Germany", tier: str = "Tier 1") -> dict:
    return {
        "id": id,
        "name": f"Supplier {id}",
        "tier": tier,
        "country": country,
        "industry": "Manufacturing",
        "status": "Active",
    }


def _score(
    supplier_id: str, risk_band: str = "Low", trend: str = "Stable", risk_score: float = 10.0
) -> tuple[str, dict]:
    return supplier_id, {
        "esg_score": 80.0,
        "risk_score": risk_score,
        "risk_band": risk_band,
        "trend": trend,
    }


def _finding(id: str, severity: str = "High", category: str = "Environmental") -> dict:
    return {
        "id": id,
        "title": f"Finding {id}",
        "severity": severity,
        "category": category,
        "supplier_id": "s1",
    }


def _gap(
    id: str, severity: str = "Critical", is_resolved: bool = False, supplier_id: str = "s1"
) -> dict:
    return {
        "id": id,
        "severity": severity,
        "is_resolved": is_resolved,
        "supplier_id": supplier_id,
        "gap_type": "missing_evidence",
    }


def _base_args(**kwargs) -> dict:
    args = {
        "organization_id": "org-1",
        "suppliers": [],
        "supplier_scores": {},
        "findings": [],
        "risks": [],
        "recommendations": [],
        "compliance_gaps": [],
        "evidence_items": [],
    }
    args.update(kwargs)
    return args


class TestCsdddEngineStructure:
    def test_empty_inputs_returns_valid_structure(self):
        result = build_csddd_report(**_base_args())
        assert "meta" in result
        assert "supply_chain" in result
        assert "severe_impacts" in result
        assert "risk_assessment" in result
        assert "supplier_risk_trends" in result
        assert "remediation_progress" in result
        assert "governance_oversight" in result
        assert "supplier_readiness" in result
        assert "critical_gaps" in result
        assert "explainability" in result

    def test_meta_fields(self):
        result = build_csddd_report(**_base_args(organization_id="org-test"))
        assert result["meta"]["framework"] == "CSDDD"
        assert result["meta"]["framework_version"] == "2024/1760"
        assert result["meta"]["organization_id"] == "org-test"

    def test_explainability_count(self):
        result = build_csddd_report(**_base_args())
        assert len(result["explainability"]) >= 5


class TestCsdddSupplyChain:
    def test_tier_counts(self):
        suppliers = [
            _supplier("s1", tier="Tier 1"),
            _supplier("s2", tier="Tier 2"),
            _supplier("s3", tier="Tier 1"),
        ]
        result = build_csddd_report(**_base_args(suppliers=suppliers))
        assert result["supply_chain"]["total_suppliers"] == 3
        assert result["supply_chain"]["by_tier"]["Tier 1"] == 2

    def test_high_risk_country_detection(self):
        suppliers = [_supplier("s1", country="China"), _supplier("s2", country="Germany")]
        result = build_csddd_report(**_base_args(suppliers=suppliers))
        assert result["supply_chain"]["high_risk_country_count"] == 1
        assert "China" in result["supply_chain"]["high_risk_countries"]


class TestCsdddSevereImpacts:
    def test_severe_impact_identified(self):
        findings = [_finding("f1", "Critical", "human rights")]
        result = build_csddd_report(**_base_args(findings=findings))
        assert result["severe_impacts"]["total"] >= 1

    def test_non_severe_low_finding_excluded(self):
        findings = [_finding("f1", "Low", "human rights")]
        result = build_csddd_report(**_base_args(findings=findings))
        assert result["severe_impacts"]["total"] == 0

    def test_hr_vs_env_severe_classification(self):
        findings = [
            _finding("f1", "Critical", "human rights"),
            _finding("f2", "High", "environmental"),
        ]
        result = build_csddd_report(**_base_args(findings=findings))
        assert result["severe_impacts"]["human_rights"] >= 1
        assert result["severe_impacts"]["environmental"] >= 1


class TestCsdddRiskAssessment:
    def test_open_gaps_count_as_residual(self):
        gaps = [_gap("g1", is_resolved=False), _gap("g2", is_resolved=False)]
        result = build_csddd_report(**_base_args(compliance_gaps=gaps))
        assert result["risk_assessment"]["residual_risks"] == 2

    def test_resolved_gaps_count_as_mitigated(self):
        gaps = [_gap("g1", is_resolved=True), _gap("g2", is_resolved=False)]
        result = build_csddd_report(**_base_args(compliance_gaps=gaps))
        assert result["risk_assessment"]["mitigated_risks"] == 1

    def test_critical_gaps_listed(self):
        gaps = [_gap("g1", "Critical"), _gap("g2", "Medium")]
        result = build_csddd_report(**_base_args(compliance_gaps=gaps))
        assert result["risk_assessment"]["critical_gaps"] == 1
        assert len(result["critical_gaps"]) == 1


class TestCsdddSupplierTrends:
    def test_trend_counts(self):
        suppliers = [_supplier("s1"), _supplier("s2"), _supplier("s3")]
        scores = dict(
            [
                _score("s1", trend="Improving"),
                _score("s2", trend="Deteriorating"),
                _score("s3", trend="Stable"),
            ]
        )
        result = build_csddd_report(**_base_args(suppliers=suppliers, supplier_scores=scores))
        assert result["supplier_risk_trends"]["improving"] == 1
        assert result["supplier_risk_trends"]["deteriorating"] == 1
        assert result["supplier_risk_trends"]["stable"] == 1

    def test_supplier_without_score_counted_as_no_data(self):
        suppliers = [_supplier("s1")]
        result = build_csddd_report(**_base_args(suppliers=suppliers))
        assert result["supplier_risk_trends"]["no_data"] == 1


class TestCsdddSupplierReadiness:
    def test_ready_vs_not_ready(self):
        suppliers = [_supplier("s1"), _supplier("s2"), _supplier("s3")]
        scores = dict(
            [
                _score("s1", "Low"),
                _score("s2", "Moderate"),
                _score("s3", "Critical"),
            ]
        )
        result = build_csddd_report(**_base_args(suppliers=suppliers, supplier_scores=scores))
        assert result["supplier_readiness"]["ready"] == 2
        assert result["supplier_readiness"]["not_ready"] == 1
