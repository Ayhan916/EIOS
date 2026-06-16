"""Unit tests for M18 Report Service — snapshot builder and PDF renderer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.reporting.service import (
    _assessment_dict,
    _build_snapshot,
    _evidence_dict,
    _finding_dict,
    _rec_dict,
    _risk_dict,
)
from domain.assessment import Assessment
from domain.enums import ConfidenceLevel, EntityStatus, EvidenceType, RiskLevel
from domain.evidence import Evidence
from domain.finding import Finding
from domain.recommendation import Recommendation
from domain.risk import Risk
from domain.user import User
from infrastructure.reporting.pdf_renderer import render_report_pdf


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_user(**kwargs: Any) -> User:
    defaults: dict[str, Any] = dict(
        id="user-1",
        email="analyst@eios.io",
        display_name="Jane Analyst",
        role="analyst",
        is_active=True,
        organization_id="org-1",
    )
    return User(**{**defaults, **kwargs})


def _make_assessment(**kwargs: Any) -> Assessment:
    defaults: dict[str, Any] = dict(
        id="assess-1",
        title="Acme Corp ESG Assessment",
        description="Full ESG due diligence for Acme Corp.",
        assessment_type="ESG Due Diligence",
        scope="Global operations, 2024",
        methodology="EIOS Standard v1",
        confidence=ConfidenceLevel.HIGH,
        organization_id="org-1",
    )
    return Assessment(**{**defaults, **kwargs})


def _make_finding(**kwargs: Any) -> Finding:
    defaults: dict[str, Any] = dict(
        id="find-1",
        title="Child Labour Risk in Tier-2 Suppliers",
        description="Evidence of child labour practices identified in three tier-2 suppliers.",
        assessment_id="assess-1",
        category="Human Rights",
        severity=RiskLevel.CRITICAL,
        confidence=ConfidenceLevel.HIGH,
        reasoning="Cross-referencing supplier registry with NGO reports.",
        uncertainty="Third-party audit data unavailable for 2 suppliers.",
    )
    return Finding(**{**defaults, **kwargs})


def _make_risk(**kwargs: Any) -> Risk:
    defaults: dict[str, Any] = dict(
        id="risk-1",
        title="Regulatory Sanction Risk",
        description="Exposure to LkSG sanctions for non-disclosure.",
        assessment_id="assess-1",
        category="Regulatory",
        risk_level=RiskLevel.HIGH,
        probability=0.7,
        impact=0.9,
        confidence=ConfidenceLevel.MEDIUM,
    )
    return Risk(**{**defaults, **kwargs})


def _make_recommendation(**kwargs: Any) -> Recommendation:
    defaults: dict[str, Any] = dict(
        id="rec-1",
        title="Conduct Tier-2 Supplier Audit",
        description="Commission independent audit of tier-2 suppliers within 90 days.",
        assessment_id="assess-1",
        priority=RiskLevel.CRITICAL,
        confidence=ConfidenceLevel.HIGH,
        action_required=True,
    )
    return Recommendation(**{**defaults, **kwargs})


def _make_evidence(**kwargs: Any) -> Evidence:
    defaults: dict[str, Any] = dict(
        id="ev-1",
        title="NGO Report on Supply Chain Labour Conditions",
        description="Annual labour conditions report by XYZ NGO.",
        source="xyz-ngo.org",
        evidence_type=EvidenceType.REPORT,
        confidence=ConfidenceLevel.HIGH,
        organization_id="org-1",
    )
    return Evidence(**{**defaults, **kwargs})


# ── Snapshot serialisation ────────────────────────────────────────────────────

class TestSnapshotSerializers:
    def test_assessment_dict_fields(self) -> None:
        a = _make_assessment()
        d = _assessment_dict(a)
        assert d["id"] == "assess-1"
        assert d["title"] == "Acme Corp ESG Assessment"
        assert d["confidence"] == "High"
        assert d["status"] == "Draft"
        assert "organization_id" in d

    def test_finding_dict_fields(self) -> None:
        f = _make_finding()
        d = _finding_dict(f)
        assert d["id"] == "find-1"
        assert d["severity"] == "Critical"
        assert d["confidence"] == "High"
        assert d["reasoning"] is not None

    def test_finding_dict_none_reasoning(self) -> None:
        f = _make_finding(reasoning=None, uncertainty=None)
        d = _finding_dict(f)
        assert d["reasoning"] is None
        assert d["uncertainty"] is None

    def test_risk_dict_probability_impact(self) -> None:
        r = _make_risk()
        d = _risk_dict(r)
        assert d["probability"] == pytest.approx(0.7)
        assert d["impact"] == pytest.approx(0.9)
        assert d["risk_level"] == "High"

    def test_risk_dict_none_probability(self) -> None:
        r = _make_risk(probability=None, impact=None)
        d = _risk_dict(r)
        assert d["probability"] is None
        assert d["impact"] is None

    def test_rec_dict_action_required(self) -> None:
        rec = _make_recommendation()
        d = _rec_dict(rec)
        assert d["action_required"] is True
        assert d["priority"] == "Critical"
        assert d["due_date"] is None

    def test_rec_dict_due_date_serialized(self) -> None:
        due = datetime(2025, 12, 31, tzinfo=timezone.utc)
        rec = _make_recommendation(due_date=due)
        d = _rec_dict(rec)
        assert d["due_date"] == due.isoformat()

    def test_evidence_dict_fields(self) -> None:
        ev = _make_evidence()
        d = _evidence_dict(ev)
        assert d["id"] == "ev-1"
        assert d["evidence_type"] == "Report"
        assert d["confidence"] == "High"
        assert d["published_at"] is None


class TestBuildSnapshot:
    def test_snapshot_structure(self) -> None:
        user = _make_user()
        assessment = _make_assessment()
        findings = [_make_finding()]
        risks = [_make_risk()]
        recs = [_make_recommendation()]
        evidence = [_make_evidence()]

        snap = _build_snapshot(assessment, findings, risks, recs, evidence, user)

        assert "assessment" in snap
        assert "findings" in snap
        assert "risks" in snap
        assert "recommendations" in snap
        assert "evidence" in snap
        assert "meta" in snap

    def test_snapshot_counts(self) -> None:
        user = _make_user()
        snap = _build_snapshot(
            _make_assessment(),
            [_make_finding(), _make_finding(id="find-2")],
            [_make_risk()],
            [],
            [_make_evidence(), _make_evidence(id="ev-2")],
            user,
        )
        assert snap["meta"]["counts"]["findings"] == 2
        assert snap["meta"]["counts"]["risks"] == 1
        assert snap["meta"]["counts"]["recommendations"] == 0
        assert snap["meta"]["counts"]["evidence"] == 2

    def test_snapshot_generated_by(self) -> None:
        user = _make_user(display_name="Jane Analyst")
        snap = _build_snapshot(
            _make_assessment(), [], [], [], [], user
        )
        assert snap["meta"]["generated_by"] == "user-1"
        assert snap["meta"]["generated_by_name"] == "Jane Analyst"

    def test_snapshot_generated_by_falls_back_to_email(self) -> None:
        user = _make_user(display_name=None)
        snap = _build_snapshot(
            _make_assessment(), [], [], [], [], user
        )
        assert snap["meta"]["generated_by_name"] == "analyst@eios.io"

    def test_snapshot_report_id_placeholder(self) -> None:
        user = _make_user()
        snap = _build_snapshot(
            _make_assessment(), [], [], [], [], user
        )
        assert snap["meta"]["report_id"] == ""

    def test_snapshot_assessment_serialized(self) -> None:
        user = _make_user()
        snap = _build_snapshot(
            _make_assessment(title="My Assessment"), [], [], [], [], user
        )
        assert snap["assessment"]["title"] == "My Assessment"

    def test_snapshot_findings_list(self) -> None:
        user = _make_user()
        snap = _build_snapshot(
            _make_assessment(),
            [_make_finding(id="f1"), _make_finding(id="f2")],
            [], [], [], user,
        )
        assert len(snap["findings"]) == 2
        ids = {f["id"] for f in snap["findings"]}
        assert ids == {"f1", "f2"}

    def test_snapshot_empty_lists(self) -> None:
        user = _make_user()
        snap = _build_snapshot(_make_assessment(), [], [], [], [], user)
        assert snap["findings"] == []
        assert snap["risks"] == []
        assert snap["recommendations"] == []
        assert snap["evidence"] == []


# ── PDF renderer ──────────────────────────────────────────────────────────────

class TestPDFRenderer:
    def _full_snapshot(self) -> dict:
        user = _make_user()
        return _build_snapshot(
            _make_assessment(),
            [_make_finding()],
            [_make_risk()],
            [_make_recommendation()],
            [_make_evidence()],
            user,
        )

    def test_render_returns_bytes(self) -> None:
        snap = self._full_snapshot()
        snap["meta"]["report_id"] = "report-1"
        pdf_bytes = render_report_pdf(snap)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_render_starts_with_pdf_magic(self) -> None:
        snap = self._full_snapshot()
        snap["meta"]["report_id"] = "report-1"
        pdf_bytes = render_report_pdf(snap)
        assert pdf_bytes[:4] == b"%PDF"

    def test_render_empty_snapshot(self) -> None:
        snap = {
            "assessment": {"title": "Empty Assessment", "id": "a-1"},
            "findings": [],
            "risks": [],
            "recommendations": [],
            "evidence": [],
            "meta": {"generated_at": "2026-06-16T00:00:00Z", "generated_by_name": "Test", "report_id": "r-1", "counts": {}},
        }
        pdf_bytes = render_report_pdf(snap)
        assert pdf_bytes[:4] == b"%PDF"

    def test_render_with_many_findings(self) -> None:
        user = _make_user()
        findings = [
            _make_finding(
                id=f"f-{i}",
                title=f"Finding {i}",
                severity=["Critical", "High", "Medium", "Low"][i % 4],
            )
            for i in range(20)
        ]
        snap = _build_snapshot(
            _make_assessment(), findings, [], [], [], user
        )
        snap["meta"]["report_id"] = "r-multi"
        pdf_bytes = render_report_pdf(snap)
        assert pdf_bytes[:4] == b"%PDF"

    def test_render_with_unicode_content(self) -> None:
        user = _make_user()
        snap = _build_snapshot(
            _make_assessment(title="ESG Bewertung — Ürün Güvenliği"),
            [_make_finding(title="Çevre Riski", description="Énvironnemental impact assessment")],
            [], [], [], user,
        )
        snap["meta"]["report_id"] = "r-unicode"
        pdf_bytes = render_report_pdf(snap)
        assert pdf_bytes[:4] == b"%PDF"

    def test_render_with_long_descriptions(self) -> None:
        long_desc = "A" * 1000
        user = _make_user()
        snap = _build_snapshot(
            _make_assessment(description=long_desc),
            [_make_finding(description=long_desc)],
            [_make_risk(description=long_desc)],
            [_make_recommendation(description=long_desc)],
            [_make_evidence(description=long_desc)],
            user,
        )
        snap["meta"]["report_id"] = "r-long"
        pdf_bytes = render_report_pdf(snap)
        assert pdf_bytes[:4] == b"%PDF"
