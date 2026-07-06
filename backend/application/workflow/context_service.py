"""Workflow context service — builds the Lieferketten-Sorgfalt pipeline chain.

Given any entity (assessment, finding, risk, recommendation) and its org, returns
the full workflow chain with completion status per step so the UI can render the
WorkflowProgressBar and suggest the next action.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLFindingRepository,
    SQLRecommendationRepository,
    SQLRiskRepository,
    SQLSupplierRepository,
)
from infrastructure.persistence.repositories.corrective_action_plan import SQLCAPRepository


@dataclass
class WorkflowStepInfo:
    key: str
    label: str
    count: int
    status: str  # "done" | "partial" | "missing"
    current: bool
    route: str | None
    entities: list[dict] = field(default_factory=list)
    next_action_label: str | None = None
    next_action_route: str | None = None


@dataclass
class WorkflowContext:
    workflow_id: str
    workflow_name: str
    entity_type: str
    entity_id: str
    assessment_id: str | None
    supplier_id: str | None
    supplier_name: str | None
    steps: list[WorkflowStepInfo]
    completion_pct: int
    next_step: WorkflowStepInfo | None


async def get_workflow_context(
    entity_type: str,
    entity_id: str,
    org_id: str,
    session: AsyncSession,
) -> WorkflowContext | None:
    """Return the Lieferketten-Sorgfalt workflow chain for any core entity."""
    assessment_repo = SQLAssessmentRepository(session)
    finding_repo = SQLFindingRepository(session)
    risk_repo = SQLRiskRepository(session)
    rec_repo = SQLRecommendationRepository(session)
    supplier_repo = SQLSupplierRepository(session)
    cap_repo = SQLCAPRepository(session)

    # ── 1. Resolve assessment_id from the anchor entity ───────────────────────
    assessment_id: str | None = None

    if entity_type == "assessment":
        assessment_id = entity_id
    elif entity_type == "finding":
        finding = await finding_repo.get_by_id(entity_id)
        if finding:
            assessment_id = finding.assessment_id
    elif entity_type == "risk":
        risk = await risk_repo.get_by_id(entity_id)
        if risk:
            assessment_id = risk.assessment_id
    elif entity_type == "recommendation":
        rec = await rec_repo.get_by_id(entity_id)
        if rec:
            assessment_id = rec.assessment_id

    if not assessment_id:
        return None

    # ── 2. Load assessment (org scope check) ──────────────────────────────────
    assessment = await assessment_repo.get_by_id(assessment_id)
    if not assessment or assessment.organization_id != org_id:
        return None

    # ── 3. Load all child entities in parallel groups ─────────────────────────
    supplier = None
    if assessment.supplier_id:
        supplier = await supplier_repo.get_by_id(assessment.supplier_id)

    findings = await finding_repo.list_by_assessment(assessment_id)
    risks = await risk_repo.list_by_assessment(assessment_id)
    recommendations = await rec_repo.list_by_assessment(assessment_id)

    caps = []
    for f in findings:
        cap = await cap_repo.get_by_finding(f.id, org_id)
        if cap:
            caps.append(cap)

    # ── 4. Build workflow steps ───────────────────────────────────────────────
    steps: list[WorkflowStepInfo] = []

    if supplier:
        steps.append(WorkflowStepInfo(
            key="supplier",
            label="Lieferant",
            count=1,
            status="done",
            current=entity_type == "supplier",
            route=f"/suppliers/{supplier.id}",
            entities=[{"id": supplier.id, "title": supplier.name}],
        ))

    steps.append(WorkflowStepInfo(
        key="assessment",
        label="Assessment",
        count=1,
        status="done",
        current=entity_type == "assessment",
        route=f"/assessments/{assessment_id}",
        entities=[{"id": assessment_id, "title": assessment.title}],
    ))

    finding_status = "done" if findings else "missing"
    steps.append(WorkflowStepInfo(
        key="finding",
        label="Findings",
        count=len(findings),
        status=finding_status,
        current=entity_type == "finding",
        route=f"/findings?assessment_id={assessment_id}" if findings else None,
        entities=[{"id": f.id, "title": f.title} for f in findings[:3]],
        next_action_label="Finding erstellen" if not findings else None,
        next_action_route=f"/assessments/{assessment_id}?tab=findings" if not findings else None,
    ))

    risk_status = "done" if risks else "missing"
    steps.append(WorkflowStepInfo(
        key="risk",
        label="Risks",
        count=len(risks),
        status=risk_status,
        current=entity_type == "risk",
        route=f"/risks?assessment_id={assessment_id}" if risks else None,
        entities=[{"id": r.id, "title": r.title} for r in risks[:3]],
        next_action_label="Risiko ableiten" if not risks and findings else None,
        next_action_route=f"/assessments/{assessment_id}?tab=risks" if not risks and findings else None,
    ))

    rec_status = "done" if recommendations else "missing"
    steps.append(WorkflowStepInfo(
        key="recommendation",
        label="Empfehlungen",
        count=len(recommendations),
        status=rec_status,
        current=entity_type == "recommendation",
        route=f"/recommendations?assessment_id={assessment_id}" if recommendations else None,
        entities=[{"id": r.id, "title": r.title} for r in recommendations[:3]],
        next_action_label="Empfehlung erstellen" if not recommendations else None,
        next_action_route=f"/recommendations?assessment_id={assessment_id}" if not recommendations else None,
    ))

    cap_total = len(findings)
    cap_done = len(caps)
    if cap_done == 0 and cap_total > 0:
        cap_status = "missing"
    elif cap_done < cap_total:
        cap_status = "partial"
    elif cap_total == 0:
        cap_status = "missing"
    else:
        cap_status = "done"

    remaining_caps = cap_total - cap_done
    steps.append(WorkflowStepInfo(
        key="cap",
        label="Maßnahmen (CAP)",
        count=cap_done,
        status=cap_status,
        current=entity_type == "cap",
        route=f"/corrective-action-plans?assessment_id={assessment_id}" if caps else None,
        entities=[{"id": c.id, "title": c.title} for c in caps[:3]],
        next_action_label=f"CAP erstellen ({remaining_caps} offen)" if remaining_caps > 0 else None,
        next_action_route=f"/corrective-action-plans?assessment_id={assessment_id}" if remaining_caps > 0 else None,
    ))

    # ── 5. Compute completion ─────────────────────────────────────────────────
    done_count = sum(1 for s in steps if s.status in ("done", "partial"))
    completion_pct = int((done_count / len(steps)) * 100) if steps else 0

    next_step = next(
        (s for s in steps if s.status == "missing" and s.next_action_route),
        None,
    )

    return WorkflowContext(
        workflow_id="lieferketten_sorgfalt",
        workflow_name="Lieferketten-Sorgfaltspflicht",
        entity_type=entity_type,
        entity_id=entity_id,
        assessment_id=assessment_id,
        supplier_id=assessment.supplier_id,
        supplier_name=supplier.name if supplier else None,
        steps=steps,
        completion_pct=completion_pct,
        next_step=next_step,
    )
