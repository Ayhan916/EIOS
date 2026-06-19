"""M33.1 — Deterministic Retrieval Ordering Tests.

Verifies that every retriever uses a stable secondary sort on `.id ASC`
to guarantee page-stable, reproducible results when primary sort values tie.
"""

from __future__ import annotations

import inspect

import application.copilot.retrieval.compliance_retriever as compliance_mod
import application.copilot.retrieval.disclosure_retriever as disclosure_mod
import application.copilot.retrieval.due_diligence_retriever as due_diligence_mod
import application.copilot.retrieval.executive_retriever as executive_mod
import application.copilot.retrieval.supplier_retriever as supplier_mod


class TestSupplierRetrieverOrdering:
    def test_has_primary_sort_by_risk_score(self):
        source = inspect.getsource(supplier_mod)
        assert "risk_score.desc()" in source

    def test_has_secondary_sort_by_id(self):
        source = inspect.getsource(supplier_mod)
        assert "SupplierScoreModel.id.asc()" in source


class TestComplianceRetrieverOrdering:
    def test_has_primary_sort_by_severity(self):
        source = inspect.getsource(compliance_mod)
        assert "severity.desc()" in source

    def test_has_secondary_sort_by_id(self):
        source = inspect.getsource(compliance_mod)
        assert "ComplianceGapModel.id.asc()" in source


class TestDisclosureRetrieverOrdering:
    def test_has_primary_sort_by_coverage_score(self):
        source = inspect.getsource(disclosure_mod)
        assert "coverage_score.asc()" in source

    def test_has_secondary_sort_by_id(self):
        source = inspect.getsource(disclosure_mod)
        assert "DisclosureResponseModel.id.asc()" in source


class TestDueDiligenceRetrieverOrdering:
    def test_reports_have_secondary_sort_by_id(self):
        source = inspect.getsource(due_diligence_mod)
        assert "DueDiligenceReportModel.id.asc()" in source

    def test_overdue_actions_have_secondary_sort_by_id(self):
        source = inspect.getsource(due_diligence_mod)
        assert "RecommendationModel.id.asc()" in source

    def test_reports_primary_sort_is_generated_at_desc(self):
        source = inspect.getsource(due_diligence_mod)
        assert "generated_at.desc()" in source

    def test_overdue_primary_sort_is_due_date_asc(self):
        source = inspect.getsource(due_diligence_mod)
        assert "due_date.asc()" in source


class TestExecutiveRetrieverOrdering:
    def test_top_findings_have_secondary_sort_by_id(self):
        source = inspect.getsource(executive_mod)
        assert "FindingModel.id.asc()" in source

    def test_top_findings_primary_sort_is_created_at_desc(self):
        source = inspect.getsource(executive_mod)
        assert "created_at.desc()" in source
