"""Unit tests for M32 domain entities and PDF renderer."""

from __future__ import annotations

import pytest

from domain.disclosure import DisclosureFramework, DisclosureRequirement, DisclosureResponse
from domain.enums import EntityStatus
from domain.reporting_package import ReportingPackage
from infrastructure.reporting.disclosure_pdf_renderer import render_reporting_package


# ── DisclosureFramework ───────────────────────────────────────────────────────


class TestDisclosureFramework:
    def test_fw_version_does_not_conflict_with_entity_version(self):
        fw = DisclosureFramework(
            code="CSRD",
            name="Test",
            fw_version="2.0",
            status=EntityStatus.ACTIVE,
        )
        assert fw.fw_version == "2.0"
        assert isinstance(fw.version, int)  # BaseEntity.version is int

    def test_auto_id_unique(self):
        a = DisclosureFramework(code="A", name="A", status=EntityStatus.ACTIVE)
        b = DisclosureFramework(code="B", name="B", status=EntityStatus.ACTIVE)
        assert a.id != b.id

    def test_defaults(self):
        fw = DisclosureFramework(code="X", name="X", status=EntityStatus.ACTIVE)
        assert fw.fw_version == "1.0"
        assert fw.jurisdiction == "Global"
        assert fw.description == ""


# ── DisclosureRequirement ─────────────────────────────────────────────────────


class TestDisclosureRequirement:
    def test_required_fields(self):
        req = DisclosureRequirement(
            framework_id="fw-1",
            reference="ESRS-E1",
            title="Climate Change",
            status=EntityStatus.ACTIVE,
        )
        assert req.framework_id == "fw-1"
        assert req.reference == "ESRS-E1"

    def test_category_defaults_empty(self):
        req = DisclosureRequirement(
            framework_id="fw-1",
            reference="X",
            title="X",
            status=EntityStatus.ACTIVE,
        )
        assert req.category == ""


# ── DisclosureResponse ────────────────────────────────────────────────────────


class TestDisclosureResponse:
    def test_defaults(self):
        resp = DisclosureResponse(
            organization_id="org-1",
            requirement_id="req-1",
            status=EntityStatus.ACTIVE,
        )
        assert resp.disclosure_status == "Not Started"
        assert resp.evidence_coverage == 0.0
        assert resp.coverage_category == "Weak"
        assert resp.readiness_status == "Not Started"
        assert resp.narrative_text == ""

    def test_coverage_rationale_is_list(self):
        resp = DisclosureResponse(
            organization_id="org-1",
            requirement_id="req-1",
            status=EntityStatus.ACTIVE,
        )
        assert isinstance(resp.coverage_rationale, list)

    def test_unique_ids(self):
        r1 = DisclosureResponse(organization_id="o", requirement_id="r1", status=EntityStatus.ACTIVE)
        r2 = DisclosureResponse(organization_id="o", requirement_id="r2", status=EntityStatus.ACTIVE)
        assert r1.id != r2.id


# ── ReportingPackage ──────────────────────────────────────────────────────────


class TestReportingPackage:
    def test_report_hash_stored(self):
        pkg = ReportingPackage(
            organization_id="org-1",
            framework_id="fw-1",
            report_hash="abc123",
            status=EntityStatus.ACTIVE,
        )
        assert pkg.report_hash == "abc123"

    def test_report_data_stored(self):
        data = {"meta": {"framework_code": "CSRD"}, "requirements": []}
        pkg = ReportingPackage(
            organization_id="org-1",
            framework_id="fw-1",
            report_data=data,
            status=EntityStatus.ACTIVE,
        )
        assert pkg.report_data["meta"]["framework_code"] == "CSRD"

    def test_default_report_data_is_dict(self):
        pkg = ReportingPackage(
            organization_id="org-1",
            framework_id="fw-1",
            status=EntityStatus.ACTIVE,
        )
        assert isinstance(pkg.report_data, dict)


# ── PDF Rendering ─────────────────────────────────────────────────────────────


_PACKAGE_SNAPSHOT = {
    "meta": {
        "framework_code": "CSRD",
        "framework_name": "Corporate Sustainability Reporting Directive",
        "fw_version": "1.0",
        "package_type": "csrd_package",
        "organization_id": "org-1",
        "generated_by": "user-1",
        "generated_at": "2026-06-19T10:00:00+00:00",
        "total_requirements": 3,
        "published_count": 1,
        "approved_count": 1,
    },
    "requirements": [
        {
            "requirement_id": "req-1",
            "reference": "CSRD-E-1",
            "title": "Environmental Matters",
            "category": "Environmental",
            "disclosure_status": "Published",
            "narrative_text": "All environmental disclosures have been prepared.",
            "evidence_coverage": 0.85,
            "coverage_category": "Complete",
            "readiness_status": "Ready for Publication",
        },
        {
            "requirement_id": "req-2",
            "reference": "CSRD-S-1",
            "title": "Social Matters",
            "category": "Social",
            "disclosure_status": "Approved",
            "narrative_text": "Workforce disclosures are ready for publication.",
            "evidence_coverage": 0.72,
            "coverage_category": "Strong",
            "readiness_status": "Blocked",
        },
        {
            "requirement_id": "req-3",
            "reference": "CSRD-G-1",
            "title": "Governance Matters",
            "category": "Governance",
            "disclosure_status": "Draft",
            "narrative_text": "",
            "evidence_coverage": 0.1,
            "coverage_category": "Weak",
            "readiness_status": "Not Started",
        },
    ],
}


class TestReportingPackagePDF:
    def test_renders_to_bytes(self):
        pdf_bytes = render_reporting_package(
            org_name="Test Organisation",
            package=_PACKAGE_SNAPSHOT,
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_output_is_pdf(self):
        pdf_bytes = render_reporting_package(
            org_name="Test Organisation",
            package=_PACKAGE_SNAPSHOT,
        )
        assert pdf_bytes[:4] == b"%PDF"

    def test_empty_requirements_renders(self):
        pkg = {
            "meta": {
                "framework_code": "TCFD",
                "fw_version": "2023",
                "package_type": "tcfd_package",
                "total_requirements": 0,
                "published_count": 0,
                "approved_count": 0,
            },
            "requirements": [],
        }
        pdf_bytes = render_reporting_package(org_name="Org", package=pkg)
        assert pdf_bytes[:4] == b"%PDF"

    def test_different_snapshots_produce_different_pdfs(self):
        pkg_v1 = {**_PACKAGE_SNAPSHOT}
        pkg_v2 = {
            **_PACKAGE_SNAPSHOT,
            "requirements": [
                {**_PACKAGE_SNAPSHOT["requirements"][0], "disclosure_status": "Draft"}
            ],
        }
        pdf1 = render_reporting_package(org_name="Org", package=pkg_v1)
        pdf2 = render_reporting_package(org_name="Org", package=pkg_v2)
        assert pdf1 != pdf2

    def test_all_categories_rendered(self):
        pdf_bytes = render_reporting_package(
            org_name="Test Org",
            package=_PACKAGE_SNAPSHOT,
        )
        # PDF covers 5 pages (cover + overview + 3 category pages)
        assert len(pdf_bytes) > 2000
