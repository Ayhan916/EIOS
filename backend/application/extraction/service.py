"""
StructuredExtractionService — converts agent text outputs into domain entities.

Called after a workflow completes. Reads agent step outputs and creates
Assessment, Finding, Risk, and Recommendation domain objects.

Design principles:
- Pure function logic: no I/O, no database, no LLM calls
- Caller (API router) is responsible for persisting the returned entities
- Partial extraction is acceptable: creates whatever can be parsed
- Always returns an Assessment, even if other entities are empty
"""

from __future__ import annotations

from typing import Optional

from application.compliance.coverage import compute_coverage
from application.compliance.scoring import compute_quality_score
from domain.assessment import Assessment
from domain.enums import ConfidenceLevel, EntityStatus, RiskLevel
from domain.finding import Finding
from domain.recommendation import Recommendation
from domain.risk import Risk
from domain.workflow_run import WorkflowRun

from .parsers import (
    ParsedFinding,
    ParsedRecommendation,
    ParsedRisk,
    parse_findings,
    parse_recommendations,
    parse_risks,
)
from .validator import (
    build_extraction_report,
    validate_findings,
    validate_risks,
    validate_recommendations,
)

_CONFIDENCE_MAP = {"High": ConfidenceLevel.HIGH, "Medium": ConfidenceLevel.MEDIUM, "Low": ConfidenceLevel.LOW}
_RISK_LEVEL_MAP = {"Critical": RiskLevel.CRITICAL, "High": RiskLevel.HIGH, "Medium": RiskLevel.MEDIUM, "Low": RiskLevel.LOW}


class StructuredExtractionService:
    """Parse agent outputs into domain entities after workflow completion."""

    def extract(
        self,
        workflow_run: WorkflowRun,
        step_outputs: dict[str, str],
        created_by: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> tuple[Assessment, list[Finding], list[Risk], list[Recommendation]]:
        """Return (Assessment, findings, risks, recommendations).

        `step_outputs` maps agent_type → result_content for each completed step.
        """
        assessment = self._build_assessment(workflow_run, step_outputs, created_by, organization_id)

        raw_findings = parse_findings(step_outputs.get("esg_assessment", ""))
        raw_risks = parse_risks(step_outputs.get("risk_assessment", ""))
        raw_recs = parse_recommendations(step_outputs.get("recommendation", ""))

        # Validate and normalise — never discards, only warns
        valid_findings, findings_warnings = validate_findings(raw_findings, "esg_assessment")
        valid_risks, risks_warnings = validate_risks(raw_risks)
        valid_recs, recs_warnings = validate_recommendations(raw_recs)

        all_warnings = findings_warnings + risks_warnings + recs_warnings
        report = build_extraction_report(
            raw_findings=raw_findings,
            valid_findings=valid_findings,
            raw_risks=raw_risks,
            valid_risks=valid_risks,
            raw_recommendations=raw_recs,
            valid_recommendations=valid_recs,
            all_warnings=all_warnings,
            step_outputs=step_outputs,
        )
        assessment.extraction_metadata = report.to_dict()

        findings = [self._finding_to_domain(pf, assessment.id, created_by) for pf in valid_findings]
        risks = [self._risk_to_domain(pr, assessment.id, created_by) for pr in valid_risks]
        recommendations = [self._rec_to_domain(pr, assessment.id, created_by) for pr in valid_recs]

        # Link finding IDs into the assessment
        assessment.finding_ids = [f.id for f in findings]
        assessment.risk_ids = [r.id for r in risks]

        # Compute compliance coverage and quality score
        coverage = compute_coverage(list(step_outputs.values()))
        assessment.quality_score = compute_quality_score(
            finding_count=len(findings),
            risk_count=len(risks),
            recommendation_count=len(recommendations),
            coverage=coverage,
            verdict=workflow_run.verdict,
        )

        return assessment, findings, risks, recommendations

    # ------------------------------------------------------------------

    def _build_assessment(
        self,
        workflow_run: WorkflowRun,
        step_outputs: dict[str, str],
        created_by: Optional[str],
        organization_id: Optional[str] = None,
    ) -> Assessment:
        query_title = workflow_run.query[:200]
        description = (
            f"AI-generated assessment produced by {workflow_run.workflow_type} workflow.\n"
            f"Verdict: {workflow_run.verdict or 'n/a'} | "
            f"Overall risk: {workflow_run.overall_risk_level or 'Unknown'}"
        )

        # Use first paragraph of reporting output as methodology if available
        methodology: Optional[str] = None
        report = step_outputs.get("reporting", "")
        if report:
            lines = [l.strip() for l in report.split("\n") if l.strip() and not l.startswith("#")]
            if lines:
                methodology = lines[0][:500]

        return Assessment(
            title=f"ESG Assessment: {query_title}",
            description=description,
            assessment_type=workflow_run.workflow_type,
            scope=workflow_run.workflow_type,
            methodology=methodology,
            confidence=ConfidenceLevel.MEDIUM,
            status=EntityStatus.REVIEWED,
            created_by=created_by,
            organization_id=organization_id,
        )

    def _finding_to_domain(
        self, pf: ParsedFinding, assessment_id: str, created_by: Optional[str]
    ) -> Finding:
        return Finding(
            title=pf.title,
            description=pf.description or pf.title,
            assessment_id=assessment_id,
            category=pf.category,
            severity=_RISK_LEVEL_MAP.get(pf.severity, RiskLevel.MEDIUM),
            confidence=_CONFIDENCE_MAP.get(pf.confidence, ConfidenceLevel.MEDIUM),
            reasoning=pf.reasoning or None,
            status=EntityStatus.REVIEWED,
            created_by=created_by,
        )

    def _risk_to_domain(
        self, pr: ParsedRisk, assessment_id: str, created_by: Optional[str]
    ) -> Risk:
        return Risk(
            title=pr.title,
            description=pr.description or pr.title,
            assessment_id=assessment_id,
            category=pr.category,
            risk_level=_RISK_LEVEL_MAP.get(pr.risk_level, RiskLevel.MEDIUM),
            probability=pr.probability,
            impact=pr.impact,
            confidence=ConfidenceLevel.MEDIUM,
            reasoning=pr.reasoning or None,
            status=EntityStatus.REVIEWED,
            created_by=created_by,
        )

    def _rec_to_domain(
        self, pr: ParsedRecommendation, assessment_id: str, created_by: Optional[str]
    ) -> Recommendation:
        return Recommendation(
            title=pr.title,
            description=pr.description or pr.title,
            assessment_id=assessment_id,
            priority=_RISK_LEVEL_MAP.get(pr.priority, RiskLevel.MEDIUM),
            action_required=pr.action_required,
            reasoning=pr.reasoning or None,
            status=EntityStatus.REVIEWED,
            created_by=created_by,
        )
