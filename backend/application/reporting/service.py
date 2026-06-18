"""
EIOS Report Service (M18 + M25 evidence intelligence)

Assembles a frozen content snapshot from live database records, renders a PDF,
and persists both the snapshot and PDF bytes in a single atomic operation.

M25: evidence links per finding are included in the snapshot so the PDF can
render page-level citations for ESG auditors.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from domain.assessment import Assessment
from domain.evidence import Evidence
from domain.finding import Finding
from domain.finding_evidence_link import FindingEvidenceLink
from domain.recommendation import Recommendation
from domain.report import Report
from domain.risk import Risk
from domain.user import User
from infrastructure.persistence.repositories.assessment import SQLAssessmentRepository
from infrastructure.persistence.repositories.evidence import SQLEvidenceRepository
from infrastructure.persistence.repositories.finding import SQLFindingRepository
from infrastructure.persistence.repositories.finding_evidence_link import SQLFindingEvidenceLinkRepository
from infrastructure.persistence.repositories.recommendation import SQLRecommendationRepository
from infrastructure.persistence.repositories.report import SQLReportRepository
from infrastructure.persistence.repositories.risk import SQLRiskRepository
from infrastructure.reporting.pdf_renderer import render_report_pdf


class ReportService:
    def __init__(
        self,
        assessment_repo: SQLAssessmentRepository,
        finding_repo: SQLFindingRepository,
        risk_repo: SQLRiskRepository,
        recommendation_repo: SQLRecommendationRepository,
        evidence_repo: SQLEvidenceRepository,
        report_repo: SQLReportRepository,
        finding_evidence_link_repo: SQLFindingEvidenceLinkRepository | None = None,
    ) -> None:
        self._assessment_repo = assessment_repo
        self._finding_repo = finding_repo
        self._risk_repo = risk_repo
        self._recommendation_repo = recommendation_repo
        self._evidence_repo = evidence_repo
        self._report_repo = report_repo
        self._link_repo = finding_evidence_link_repo

    async def generate(
        self,
        assessment_id: str,
        current_user: User,
    ) -> Report:
        assessment = await self._assessment_repo.get_by_id(assessment_id)
        if assessment is None:
            raise ValueError(f"Assessment {assessment_id} not found")

        findings = await self._finding_repo.list_by_assessment(assessment_id)
        risks = await self._risk_repo.list_by_assessment(assessment_id)
        recommendations = await self._recommendation_repo.list_by_assessment(assessment_id)
        evidence = (
            await self._evidence_repo.list_by_organization(assessment.organization_id or "")
            if assessment.organization_id
            else []
        )

        # M25: load evidence links for all findings
        evidence_links: list[FindingEvidenceLink] = []
        if self._link_repo and findings:
            finding_ids = [f.id for f in findings]
            evidence_links = await self._link_repo.list_by_assessment_findings(finding_ids)

        snapshot = _build_snapshot(
            assessment=assessment,
            findings=findings,
            risks=risks,
            recommendations=recommendations,
            evidence=evidence,
            evidence_links=evidence_links,
            current_user=current_user,
        )

        pdf_bytes = render_report_pdf(snapshot)

        report = Report(
            assessment_id=assessment_id,
            title=f"ESG Due Diligence Report — {assessment.title}",
            generated_by=current_user.id,
            organization_id=assessment.organization_id,
            format="pdf",
            finding_count=len(findings),
            risk_count=len(risks),
            recommendation_count=len(recommendations),
            evidence_count=len(evidence),
            content_snapshot=snapshot,
            created_by=current_user.id,
        )

        snapshot["meta"]["report_id"] = report.id
        report.content_snapshot = snapshot

        return await self._report_repo.save_with_pdf(report, pdf_bytes)


# ── Snapshot builder ───────────────────────────────────────────────────────────


def _build_snapshot(
    assessment: Assessment,
    findings: list[Finding],
    risks: list[Risk],
    recommendations: list[Recommendation],
    evidence: list[Evidence],
    current_user: User,
    evidence_links: list[FindingEvidenceLink] | None = None,
) -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat()
    generated_by_name = getattr(current_user, "display_name", None) or current_user.email

    # Group evidence links by finding_id
    links_by_finding: dict[str, list[dict]] = {}
    for lnk in (evidence_links or []):
        links_by_finding.setdefault(lnk.finding_id, []).append(_link_dict(lnk))

    return {
        "assessment": _assessment_dict(assessment),
        "findings": [_finding_dict(f, links_by_finding.get(f.id, [])) for f in findings],
        "risks": [_risk_dict(r) for r in risks],
        "recommendations": [_rec_dict(r) for r in recommendations],
        "evidence": [_evidence_dict(e) for e in evidence],
        "meta": {
            "generated_at": generated_at,
            "generated_by": current_user.id,
            "generated_by_name": generated_by_name,
            "report_id": "",
            "counts": {
                "findings": len(findings),
                "risks": len(risks),
                "recommendations": len(recommendations),
                "evidence": len(evidence),
                "evidence_links": len(evidence_links or []),
            },
        },
    }


def _assessment_dict(a: Assessment) -> dict[str, Any]:
    return {
        "id": a.id,
        "title": a.title,
        "description": a.description,
        "assessment_type": a.assessment_type,
        "scope": a.scope,
        "methodology": a.methodology,
        "confidence": a.confidence.value,
        "status": a.status.value,
        "created_at": a.created_at.isoformat(),
        "organization_id": a.organization_id,
    }


def _enum_val(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


def _finding_dict(f: Finding, links: list[dict] | None = None) -> dict[str, Any]:
    return {
        "id": f.id,
        "title": f.title,
        "description": f.description,
        "category": f.category,
        "severity": _enum_val(f.severity),
        "confidence": _enum_val(f.confidence),
        "reasoning": f.reasoning,
        "uncertainty": f.uncertainty,
        "evidence_strength": f.evidence_strength.value if f.evidence_strength else None,
        "evidence_source_count": f.evidence_source_count,
        "evidence_links": links or [],
    }


def _link_dict(lnk: FindingEvidenceLink) -> dict[str, Any]:
    return {
        "id": lnk.id,
        "evidence_id": lnk.evidence_id,
        "evidence_chunk_id": lnk.evidence_chunk_id,
        "page_number": lnk.page_number,
        "confidence_score": lnk.confidence_score,
        "supporting_excerpt": lnk.supporting_excerpt,
        "link_method": lnk.link_method,
    }


def _risk_dict(r: Risk) -> dict[str, Any]:
    return {
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "category": r.category,
        "risk_level": _enum_val(r.risk_level),
        "probability": r.probability,
        "impact": r.impact,
        "confidence": _enum_val(r.confidence),
        "reasoning": r.reasoning,
        "uncertainty": r.uncertainty,
    }


def _rec_dict(r: Recommendation) -> dict[str, Any]:
    return {
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "priority": _enum_val(r.priority),
        "confidence": _enum_val(r.confidence),
        "action_required": r.action_required,
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "reasoning": r.reasoning,
    }


def _evidence_dict(e: Evidence) -> dict[str, Any]:
    return {
        "id": e.id,
        "title": e.title,
        "description": e.description,
        "evidence_type": e.evidence_type.value,
        "source": e.source,
        "confidence": e.confidence.value,
        "reliability_score": e.reliability_score,
        "published_at": e.published_at.isoformat() if e.published_at else None,
    }
