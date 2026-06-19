"""Unit tests for M32.1 domain entity and PDF renderer."""

from __future__ import annotations

import pytest

from domain.due_diligence_report import DueDiligenceReport
from domain.enums import EntityStatus, DueDiligenceReportType, PreventiveMeasureEffectiveness
from infrastructure.reporting.due_diligence_pdf_renderer import render_due_diligence_report


# ── DueDiligenceReport entity ─────────────────────────────────────────────────


class TestDueDiligenceReportEntity:
    def test_required_fields(self):
        rpt = DueDiligenceReport(
            organization_id="org-1",
            report_type="lksgg_annual",
            status=EntityStatus.ACTIVE,
        )
        assert rpt.organization_id == "org-1"
        assert rpt.report_type == "lksgg_annual"

    def test_default_fields(self):
        rpt = DueDiligenceReport(
            organization_id="org-1",
            report_type="csddd",
            status=EntityStatus.ACTIVE,
        )
        assert rpt.framework == ""
        assert rpt.framework_version == ""
        assert rpt.generated_by == ""
        assert rpt.report_hash == ""
        assert isinstance(rpt.report_data, dict)

    def test_unique_ids(self):
        r1 = DueDiligenceReport(organization_id="o", report_type="csddd", status=EntityStatus.ACTIVE)
        r2 = DueDiligenceReport(organization_id="o", report_type="lksgg_annual", status=EntityStatus.ACTIVE)
        assert r1.id != r2.id

    def test_report_data_stored(self):
        data = {"meta": {"framework": "LkSG"}, "supplier_inventory": {"total": 5}}
        rpt = DueDiligenceReport(
            organization_id="org-1",
            report_type="lksgg_annual",
            report_data=data,
            status=EntityStatus.ACTIVE,
        )
        assert rpt.report_data["meta"]["framework"] == "LkSG"
        assert rpt.report_data["supplier_inventory"]["total"] == 5

    def test_version_is_int_not_conflicted(self):
        rpt = DueDiligenceReport(organization_id="o", report_type="csddd", status=EntityStatus.ACTIVE)
        assert isinstance(rpt.version, int)


# ── DueDiligenceReportType enum ───────────────────────────────────────────────


class TestDueDiligenceReportTypeEnum:
    def test_all_types_present(self):
        values = {t.value for t in DueDiligenceReportType}
        assert "lksgg_annual" in values
        assert "csddd" in values
        assert "human_rights" in values
        assert "environmental" in values
        assert "preventive_measures" in values
        assert "remediation" in values


class TestPreventiveMeasureEffectivenessEnum:
    def test_all_values_present(self):
        values = {e.value for e in PreventiveMeasureEffectiveness}
        assert "Effective" in values
        assert "Partially Effective" in values
        assert "Ineffective" in values
        assert "Unknown" in values


# ── PDF Renderer ──────────────────────────────────────────────────────────────


_LKSGG_SNAPSHOT = {
    "meta": {
        "framework": "LkSG",
        "framework_version": "2023",
        "report_type": "lksgg_annual",
        "organization_id": "org-1",
        "reporting_year": 2025,
        "generated_at": "2026-06-19T10:00:00+00:00",
    },
    "supplier_inventory": {"total": 10, "by_tier": {"Tier 1": 5, "Tier 2": 5}, "active": 10},
    "risk_classification": {"Critical": 1, "High": 2, "Moderate": 4, "Low": 3},
    "human_rights": {"total_findings": 5, "critical_findings": 1, "high_findings": 2, "suppliers_impacted": 3},
    "environmental": {"total_findings": 3, "critical_findings": 0, "high_findings": 1, "suppliers_impacted": 2},
    "remediation": {"open": 4, "in_progress": 2, "resolved": 6, "overdue": 1, "total": 12, "closure_rate": 0.5},
    "critical_suppliers": [
        {"supplier_id": "s1", "supplier_name": "Critical Corp", "country": "CN", "tier": "Tier 1", "risk_band": "Critical", "esg_score": 20.0, "risk_score": 95.0, "trend": "Deteriorating", "critical_findings": 3, "high_findings": 5, "open_actions": 4, "overdue_actions": 2},
    ],
    "explainability": [
        {"factor": "supplier_inventory", "value": 10, "description": "10 suppliers assessed across 2 tiers"},
        {"factor": "critical_risk_suppliers", "value": 1, "description": "1 suppliers in Critical risk band"},
    ],
}


class TestDueDiligencePDFRenderer:
    def test_renders_to_bytes(self):
        pdf_bytes = render_due_diligence_report(
            org_name="Test Organisation GmbH",
            report=_LKSGG_SNAPSHOT,
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_output_is_pdf(self):
        pdf_bytes = render_due_diligence_report(
            org_name="Test Organisation",
            report=_LKSGG_SNAPSHOT,
        )
        assert pdf_bytes[:4] == b"%PDF"

    def test_empty_snapshot_renders(self):
        snapshot = {
            "meta": {
                "framework": "CSDDD",
                "framework_version": "2024/1760",
                "report_type": "csddd",
                "organization_id": "org-1",
            }
        }
        pdf_bytes = render_due_diligence_report(org_name="Org", report=snapshot)
        assert pdf_bytes[:4] == b"%PDF"

    def test_minimal_pdf_size(self):
        pdf_bytes = render_due_diligence_report(
            org_name="Test Org",
            report=_LKSGG_SNAPSHOT,
        )
        assert len(pdf_bytes) > 2000

    def test_different_snapshots_produce_different_pdfs(self):
        snapshot_v2 = {**_LKSGG_SNAPSHOT, "remediation": {"open": 0, "resolved": 12, "total": 12, "closure_rate": 1.0}}
        pdf1 = render_due_diligence_report(org_name="Org", report=_LKSGG_SNAPSHOT)
        pdf2 = render_due_diligence_report(org_name="Org", report=snapshot_v2)
        assert pdf1 != pdf2

    def test_remediation_report_renders(self):
        rem_snapshot = {
            "meta": {
                "framework": "OECD Guidelines",
                "report_type": "remediation",
                "organization_id": "org-1",
            },
            "summary": {"total": 5, "open": 2, "completed": 3, "overdue": 1, "closure_rate": 0.6},
            "remediation": {"open": 2, "completed": 3, "resolved": 3, "overdue": 1, "total": 5, "closure_rate": 0.6},
        }
        pdf_bytes = render_due_diligence_report(org_name="Org", report=rem_snapshot)
        assert pdf_bytes[:4] == b"%PDF"
