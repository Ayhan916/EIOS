"""M33.2 — Contradiction Detection Engine Tests.

All detection is pure-function, pre-LLM, cross-retriever.
No DB, no LLM, no I/O.
"""

from __future__ import annotations

from application.copilot.contradiction_detector import (
    ContradictionRecord,
    contradictions_to_dicts,
    detect_contradictions,
    format_contradictions_for_prompt,
)
from application.copilot.retrieval.base import RetrievalResult
from domain.enums import ContradictionType


def _supplier_result(suppliers: list[dict]) -> RetrievalResult:
    return RetrievalResult(
        retriever="supplier_retriever",
        provenance="Supplier Intelligence",
        data=suppliers,
        source_ids=[s["supplier_id"] for s in suppliers],
        citation_type="Supplier",
    )


def _compliance_result(gaps: list[dict]) -> RetrievalResult:
    return RetrievalResult(
        retriever="compliance_retriever",
        provenance="Compliance Intelligence",
        data=gaps,
        source_ids=[g["gap_id"] for g in gaps],
        citation_type="ComplianceGap",
    )


def _disclosure_result(disclosures: list[dict]) -> RetrievalResult:
    return RetrievalResult(
        retriever="disclosure_retriever",
        provenance="Disclosure Intelligence",
        data=disclosures,
        source_ids=[d["response_id"] for d in disclosures],
        citation_type="Disclosure",
    )


def _executive_result(data: dict) -> RetrievalResult:
    return RetrievalResult(
        retriever="executive_retriever",
        provenance="Executive Intelligence",
        data=[data],
        source_ids=[],
        citation_type="ExecutiveSummary",
    )


class TestNoContradictions:
    def test_empty_results_produces_no_contradictions(self):
        assert detect_contradictions([]) == []

    def test_high_risk_band_with_critical_gap_no_contradiction(self):
        sup = _supplier_result([{"supplier_id": "s1", "risk_band": "High", "critical_findings": []}])
        gap = _compliance_result([{"gap_id": "g1", "severity": "Critical"}])
        result = detect_contradictions([sup, gap])
        types = {c.contradiction_type for c in result}
        assert ContradictionType.RISK_VS_COMPLIANCE not in types

    def test_fresh_disclosure_no_completeness_contradiction(self):
        disc = _disclosure_result([{"response_id": "d1", "disclosure_status": "Approved", "coverage_score": 0.9}])
        assert detect_contradictions([disc]) == []


class TestRiskVsCompliance:
    def test_low_risk_band_with_critical_gap_triggers(self):
        sup = _supplier_result([{"supplier_id": "s1", "risk_band": "Low", "critical_findings": []}])
        gap = _compliance_result([{"gap_id": "g1", "severity": "Critical"}])
        result = detect_contradictions([sup, gap])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.RISK_VS_COMPLIANCE in types

    def test_moderate_risk_band_with_critical_gap_triggers(self):
        sup = _supplier_result([{"supplier_id": "s1", "risk_band": "Moderate", "critical_findings": []}])
        gap = _compliance_result([{"gap_id": "g1", "severity": "Critical"}])
        result = detect_contradictions([sup, gap])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.RISK_VS_COMPLIANCE in types

    def test_no_critical_gap_no_risk_compliance_contradiction(self):
        sup = _supplier_result([{"supplier_id": "s1", "risk_band": "Low", "critical_findings": []}])
        gap = _compliance_result([{"gap_id": "g1", "severity": "Medium"}])
        result = detect_contradictions([sup, gap])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.RISK_VS_COMPLIANCE not in types

    def test_contradiction_description_mentions_counts(self):
        sup = _supplier_result([{"supplier_id": "s1", "risk_band": "Low", "critical_findings": []}])
        gap = _compliance_result([{"gap_id": "g1", "severity": "Critical"}])
        result = detect_contradictions([sup, gap])
        rvc = next(c for c in result if c.contradiction_type == ContradictionType.RISK_VS_COMPLIANCE)
        assert "1 supplier(s)" in rvc.description
        assert "1 Critical compliance gap(s)" in rvc.description


class TestDisclosureCompleteness:
    def test_approved_low_coverage_triggers(self):
        disc = _disclosure_result([{"response_id": "d1", "disclosure_status": "Approved", "coverage_score": 0.10}])
        result = detect_contradictions([disc])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.DISCLOSURE_COMPLETENESS in types

    def test_published_low_coverage_triggers(self):
        disc = _disclosure_result([{"response_id": "d1", "disclosure_status": "Published", "coverage_score": 0.20}])
        result = detect_contradictions([disc])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.DISCLOSURE_COMPLETENESS in types

    def test_draft_low_coverage_does_not_trigger(self):
        disc = _disclosure_result([{"response_id": "d1", "disclosure_status": "Draft", "coverage_score": 0.10}])
        result = detect_contradictions([disc])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.DISCLOSURE_COMPLETENESS not in types

    def test_approved_30pct_exact_boundary_does_not_trigger(self):
        disc = _disclosure_result([{"response_id": "d1", "disclosure_status": "Approved", "coverage_score": 0.30}])
        result = detect_contradictions([disc])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.DISCLOSURE_COMPLETENESS not in types


class TestFindingWithoutAction:
    def test_critical_findings_no_open_recs_triggers(self):
        exec_data = {"critical_findings": 3, "open_recommendations": 0}
        result = detect_contradictions([_executive_result(exec_data)])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.FINDING_WITHOUT_ACTION in types

    def test_critical_findings_with_open_recs_no_trigger(self):
        exec_data = {"critical_findings": 3, "open_recommendations": 2}
        result = detect_contradictions([_executive_result(exec_data)])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.FINDING_WITHOUT_ACTION not in types

    def test_severity_is_critical(self):
        exec_data = {"critical_findings": 2, "open_recommendations": 0}
        result = detect_contradictions([_executive_result(exec_data)])
        fwa = next(c for c in result if c.contradiction_type == ContradictionType.FINDING_WITHOUT_ACTION)
        assert fwa.severity == "critical"


class TestSupplierScoreVsFindings:
    def test_high_esg_with_critical_findings_triggers(self):
        sup = _supplier_result([{
            "supplier_id": "s1",
            "supplier_name": "Acme Corp",
            "risk_band": "Low",
            "esg_score": 85,
            "critical_findings": ["f1"],
        }])
        result = detect_contradictions([sup])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.SUPPLIER_SCORE_VS_FINDINGS in types

    def test_low_esg_no_trigger(self):
        sup = _supplier_result([{
            "supplier_id": "s1",
            "risk_band": "High",
            "esg_score": 50,
            "critical_findings": ["f1"],
        }])
        result = detect_contradictions([sup])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.SUPPLIER_SCORE_VS_FINDINGS not in types

    def test_exactly_80_esg_no_trigger(self):
        sup = _supplier_result([{
            "supplier_id": "s1",
            "risk_band": "Low",
            "esg_score": 80,
            "critical_findings": ["f1"],
        }])
        result = detect_contradictions([sup])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.SUPPLIER_SCORE_VS_FINDINGS not in types

    def test_high_esg_no_critical_findings_no_trigger(self):
        sup = _supplier_result([{
            "supplier_id": "s1",
            "risk_band": "Low",
            "esg_score": 90,
            "critical_findings": [],
        }])
        result = detect_contradictions([sup])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.SUPPLIER_SCORE_VS_FINDINGS not in types


class TestExecutiveSummaryMismatch:
    def test_exec_0_critical_but_supplier_has_findings_triggers(self):
        exec_data = {"critical_findings": 0, "open_recommendations": 1}
        sup = _supplier_result([{
            "supplier_id": "s1",
            "risk_band": "High",
            "esg_score": 60,
            "critical_findings": ["f1"],
        }])
        result = detect_contradictions([sup, _executive_result(exec_data)])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.EXECUTIVE_SUMMARY_MISMATCH in types

    def test_exec_nonzero_critical_no_mismatch(self):
        exec_data = {"critical_findings": 1, "open_recommendations": 1}
        sup = _supplier_result([{
            "supplier_id": "s1",
            "risk_band": "High",
            "esg_score": 60,
            "critical_findings": ["f1"],
        }])
        result = detect_contradictions([sup, _executive_result(exec_data)])
        types = [c.contradiction_type for c in result]
        assert ContradictionType.EXECUTIVE_SUMMARY_MISMATCH not in types


class TestHelperFunctions:
    def test_format_contradictions_empty_returns_empty_string(self):
        assert format_contradictions_for_prompt([]) == ""

    def test_format_contradictions_lists_all_types(self):
        contradictions = [
            ContradictionRecord(
                contradiction_type=ContradictionType.RISK_VS_COMPLIANCE,
                description="Risk vs compliance mismatch",
            ),
            ContradictionRecord(
                contradiction_type=ContradictionType.DISCLOSURE_COMPLETENESS,
                description="Disclosure completeness issue",
            ),
        ]
        output = format_contradictions_for_prompt(contradictions)
        # Verify both descriptions appear (type repr is format-dependent on Python version)
        assert "Risk vs compliance mismatch" in output
        assert "Disclosure completeness issue" in output
        assert "1." in output
        assert "2." in output

    def test_contradictions_to_dicts_serializable(self):
        rec = ContradictionRecord(
            contradiction_type=ContradictionType.FINDING_WITHOUT_ACTION,
            description="Critical with no remediation",
            involved_objects=[{"type": "Finding", "id": "f1"}],
            severity="critical",
        )
        result = contradictions_to_dicts([rec])
        assert len(result) == 1
        d = result[0]
        assert d["contradiction_type"] == ContradictionType.FINDING_WITHOUT_ACTION
        assert d["severity"] == "critical"
        assert d["involved_objects"] == [{"type": "Finding", "id": "f1"}]
        assert "detected_at" in d

    def test_contradictions_to_dicts_empty_list(self):
        assert contradictions_to_dicts([]) == []
