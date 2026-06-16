from __future__ import annotations

from pydantic import BaseModel


class RemediationActionResponse(BaseModel):
    priority_rank: int
    article_code: str
    framework: str
    article: str
    gap_title: str
    gap_severity: str
    regulatory_exposure: float
    timeline_label: str
    explanation: str
    remediation_hint: str
    linked_recommendation_ids: list[str]
    linked_recommendation_titles: list[str]


class RemediationPlanResponse(BaseModel):
    assessment_id: str
    total_gaps: int
    immediate_actions: list[RemediationActionResponse]
    short_term_actions: list[RemediationActionResponse]
    medium_term_actions: list[RemediationActionResponse]
    linked_gap_count: int
    unlinked_gap_count: int


class DecisionBriefResponse(BaseModel):
    assessment_id: str
    assessment_title: str
    assessment_status: str
    compliance_verdict: str
    mandatory_coverage_pct: int
    quality_score: float | None
    finding_count: int
    risk_count: int
    recommendation_count: int
    critical_gap_count: int
    immediate_action_count: int
    executive_summary: str
    key_findings: list[str]
    top_critical_gaps: list[str]
    top_recommendations: list[str]
    disclaimer: str


class AssessmentTraceResponse(BaseModel):
    assessment_id: str
    assessment_title: str
    assessment_status: str
    quality_score: float | None
    workflow_run_id: str | None
    workflow_type: str | None
    workflow_verdict: str | None
    workflow_overall_risk_level: str | None
    workflow_steps_completed: int
    workflow_total_steps: int
    finding_count: int
    risk_count: int
    recommendation_count: int
    compliance_mandatory_coverage_ratio: float
    compliance_mandatory_coverage_pct: int
    compliance_critical_gap_count: int
    compliance_verdict_status: str
    audit_event_count: int
