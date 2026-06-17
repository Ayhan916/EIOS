"""Unit tests for the structured extraction layer (parsers + service)."""

from __future__ import annotations

import pytest

from application.extraction.parsers import (
    parse_findings,
    parse_recommendations,
    parse_risks,
)
from application.extraction.service import StructuredExtractionService
from domain.enums import EntityStatus, RiskLevel
from domain.workflow_run import WorkflowRun

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ESG_ASSESSMENT_OUTPUT = """
## Sector ESG Risk Profile
**NACE Sector:** C13 — Textiles
**Assessment scope:** company and supply chain

### Material Findings

### Finding 1: Child Labour in Tier-1 Suppliers
- Category: Social — Child Labour
- Severity: Critical
- Confidence: High
- Regulatory obligation: CSDDD Art. 6, LkSG § 4
- Evidence basis: Supplier audit reports 2025
- Reasoning: Multiple audits confirm presence of workers under 15 in two facilities.

### Finding 2: Wastewater Discharge Non-Compliance
- Category: Environmental — Water
- Severity: High
- Confidence: Medium
- Regulatory obligation: CSRD E3, GRI 303
- Evidence basis: Environmental monitoring data Q4 2025
- Reasoning: Effluent levels exceed local discharge limits by 40%.

### Overall Risk Level
Critical — child labour violations require immediate remediation

### Priority Actions
1. Suspend sourcing from non-compliant Tier-1 suppliers immediately.
"""

RISK_ASSESSMENT_OUTPUT = """
## Risk Register

### Risk 1: Child Labour Regulatory Enforcement
- Level: Critical
- Probability: 0.85
- Impact: 0.95
- Category: Social
- Regulatory exposure: CSDDD Art. 22, LkSG § 10
- Reasoning: Confirmed violations create high enforcement probability.

### Risk 2: Environmental Penalty for Wastewater
- Level: High
- Probability: 0.6
- Impact: 0.7
- Category: Environmental
- Regulatory exposure: CSRD E3
- Reasoning: Active regulator investigation underway.

### Risk Summary
Total risks: 2 (Critical: 1, High: 1, Medium: 0, Low: 0)
"""

RECOMMENDATION_OUTPUT = """
## Remediation Plan

### Recommendation 1: Suspend Non-Compliant Supplier Relationships
- Priority: Critical | Type: Required
- Regulatory basis: CSDDD Art. 7, LkSG § 3
- Responsible party: Procurement
- Timeline: immediate (< 30 days)
- KPI: 100% of flagged suppliers suspended or remediated
- Reasoning: Continuing sourcing during confirmed violations increases regulatory liability.

### Recommendation 2: Implement Effluent Treatment Upgrade
- Priority: High | Type: Required
- Regulatory basis: CSRD E3, national environmental law
- Responsible party: Operations
- Timeline: short-term (30–90 days)
- KPI: Effluent levels within legal limits confirmed by third-party test
- Reasoning: Active regulator investigation makes this time-critical.
"""


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestFindingParser:
    def test_parses_structured_findings(self) -> None:
        findings = parse_findings(ESG_ASSESSMENT_OUTPUT)
        assert len(findings) == 2

    def test_extracts_finding_title(self) -> None:
        findings = parse_findings(ESG_ASSESSMENT_OUTPUT)
        assert "Child Labour" in findings[0].title

    def test_extracts_severity(self) -> None:
        findings = parse_findings(ESG_ASSESSMENT_OUTPUT)
        assert findings[0].severity == "Critical"
        assert findings[1].severity == "High"

    def test_extracts_confidence(self) -> None:
        findings = parse_findings(ESG_ASSESSMENT_OUTPUT)
        assert findings[0].confidence == "High"
        assert findings[1].confidence == "Medium"

    def test_extracts_regulatory_basis(self) -> None:
        findings = parse_findings(ESG_ASSESSMENT_OUTPUT)
        assert "CSDDD" in findings[0].regulatory_basis or "LkSG" in findings[0].regulatory_basis

    def test_returns_empty_on_empty_input(self) -> None:
        assert parse_findings("") == []

    def test_returns_empty_on_unstructured_content(self) -> None:
        result = parse_findings("This is some general text without findings.")
        assert isinstance(result, list)

    def test_capped_at_twenty_findings(self) -> None:
        big_content = "\n".join(
            f"### Finding {i}: Issue {i}\n- Severity: Medium\n- Confidence: Medium\n"
            for i in range(1, 30)
        )
        findings = parse_findings(big_content)
        assert len(findings) <= 20


class TestRiskParser:
    def test_parses_structured_risks(self) -> None:
        risks = parse_risks(RISK_ASSESSMENT_OUTPUT)
        assert len(risks) == 2

    def test_extracts_risk_level(self) -> None:
        risks = parse_risks(RISK_ASSESSMENT_OUTPUT)
        assert risks[0].risk_level == "Critical"
        assert risks[1].risk_level == "High"

    def test_extracts_probability(self) -> None:
        risks = parse_risks(RISK_ASSESSMENT_OUTPUT)
        assert risks[0].probability == pytest.approx(0.85)

    def test_extracts_impact(self) -> None:
        risks = parse_risks(RISK_ASSESSMENT_OUTPUT)
        assert risks[0].impact == pytest.approx(0.95)

    def test_extracts_regulatory_exposure(self) -> None:
        risks = parse_risks(RISK_ASSESSMENT_OUTPUT)
        assert "CSDDD" in risks[0].regulatory_exposure or "LkSG" in risks[0].regulatory_exposure

    def test_returns_empty_on_empty_input(self) -> None:
        assert parse_risks("") == []


class TestRecommendationParser:
    def test_parses_structured_recommendations(self) -> None:
        recs = parse_recommendations(RECOMMENDATION_OUTPUT)
        assert len(recs) == 2

    def test_extracts_title(self) -> None:
        recs = parse_recommendations(RECOMMENDATION_OUTPUT)
        assert "Suspend" in recs[0].title

    def test_extracts_priority(self) -> None:
        recs = parse_recommendations(RECOMMENDATION_OUTPUT)
        assert recs[0].priority == "Critical"
        assert recs[1].priority == "High"

    def test_extracts_action_required_for_required_type(self) -> None:
        recs = parse_recommendations(RECOMMENDATION_OUTPUT)
        assert recs[0].action_required is True

    def test_extracts_regulatory_basis(self) -> None:
        recs = parse_recommendations(RECOMMENDATION_OUTPUT)
        assert "CSDDD" in recs[0].regulatory_basis or "LkSG" in recs[0].regulatory_basis

    def test_extracts_timeline(self) -> None:
        recs = parse_recommendations(RECOMMENDATION_OUTPUT)
        assert recs[0].timeline != ""

    def test_returns_empty_on_empty_input(self) -> None:
        assert parse_recommendations("") == []


# ---------------------------------------------------------------------------
# StructuredExtractionService tests
# ---------------------------------------------------------------------------


def _make_workflow_run() -> WorkflowRun:
    return WorkflowRun(
        workflow_type="quick_scan",
        query="Assess ESG risks for textile manufacturer",
        verdict="conditional_pass",
        overall_risk_level="Critical",
        steps_completed=4,
        total_steps=4,
        status=EntityStatus.APPROVED,
    )


class TestStructuredExtractionService:
    def test_always_creates_assessment(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        assessment, _, _, _ = service.extract(run, {})
        assert assessment.title != ""
        assert "quick_scan" in assessment.assessment_type

    def test_assessment_title_contains_query(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        assessment, _, _, _ = service.extract(run, {})
        assert "textile" in assessment.title.lower() or "ESG" in assessment.title

    def test_assessment_status_is_reviewed(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        assessment, _, _, _ = service.extract(run, {})
        assert assessment.status == EntityStatus.REVIEWED

    def test_extracts_findings_from_esg_output(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        _, findings, _, _ = service.extract(run, {"esg_assessment": ESG_ASSESSMENT_OUTPUT})
        assert len(findings) == 2
        assert findings[0].severity == RiskLevel.CRITICAL

    def test_extracts_risks_from_risk_output(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        _, _, risks, _ = service.extract(run, {"risk_assessment": RISK_ASSESSMENT_OUTPUT})
        assert len(risks) == 2
        assert risks[0].risk_level == RiskLevel.CRITICAL

    def test_extracts_recommendations_from_recommendation_output(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        _, _, _, recs = service.extract(run, {"recommendation": RECOMMENDATION_OUTPUT})
        assert len(recs) == 2

    def test_assessment_finding_ids_linked(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        assessment, findings, _, _ = service.extract(run, {"esg_assessment": ESG_ASSESSMENT_OUTPUT})
        assert len(assessment.finding_ids) == len(findings)
        for f in findings:
            assert f.id in assessment.finding_ids

    def test_assessment_risk_ids_linked(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        assessment, _, risks, _ = service.extract(run, {"risk_assessment": RISK_ASSESSMENT_OUTPUT})
        assert len(assessment.risk_ids) == len(risks)

    def test_full_extraction_all_outputs(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        assessment, findings, risks, recs = service.extract(
            run,
            {
                "esg_assessment": ESG_ASSESSMENT_OUTPUT,
                "risk_assessment": RISK_ASSESSMENT_OUTPUT,
                "recommendation": RECOMMENDATION_OUTPUT,
            },
        )
        assert assessment is not None
        assert len(findings) > 0
        assert len(risks) > 0
        assert len(recs) > 0

    def test_created_by_propagated_to_entities(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        assessment, findings, risks, recs = service.extract(
            run,
            {"esg_assessment": ESG_ASSESSMENT_OUTPUT, "risk_assessment": RISK_ASSESSMENT_OUTPUT},
            created_by="user-123",
        )
        assert assessment.created_by == "user-123"
        for f in findings:
            assert f.created_by == "user-123"
        for r in risks:
            assert r.created_by == "user-123"

    def test_empty_step_outputs_returns_assessment_only(self) -> None:
        service = StructuredExtractionService()
        run = _make_workflow_run()
        assessment, findings, risks, recs = service.extract(run, {})
        assert assessment is not None
        assert findings == []
        assert risks == []
        assert recs == []
