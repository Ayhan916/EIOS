"""Workflow context service — builds pipeline chains for Lieferketten-Sorgfalt and Grievance/Remedy.

Given any entity and its org, returns the full workflow chain with completion status per step
so the UI can render the WorkflowProgressBar and suggest the next action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import cast, func, select, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.remedy_case import RemedyCaseModel
from infrastructure.persistence.models.supplier_portal import GrievanceReportModel
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLFindingRepository,
    SQLRecommendationRepository,
    SQLRiskRepository,
    SQLSupplierRepository,
)
from infrastructure.persistence.repositories.corrective_action_plan import SQLCAPRepository
from infrastructure.persistence.repositories.grievance import SQLGrievanceRepository


@dataclass
class WorkflowStepInfo:
    key: str
    label: str
    count: int
    status: str  # "done" | "partial" | "missing"
    current: bool
    route: str | None
    entities: list[dict[str, Any]] = field(default_factory=list)
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


@dataclass
class ActiveWorkflow:
    workflow_id: str
    workflow_name: str
    entity_type: str
    entity_id: str
    entity_label: str
    supplier_id: str | None
    supplier_name: str | None
    completion_pct: int
    next_step_label: str | None
    route: str


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
        steps.append(
            WorkflowStepInfo(
                key="supplier",
                label="Lieferant",
                count=1,
                status="done",
                current=entity_type == "supplier",
                route=f"/suppliers/{supplier.id}",
                entities=[{"id": supplier.id, "title": supplier.name}],
            )
        )

    steps.append(
        WorkflowStepInfo(
            key="assessment",
            label="Assessment",
            count=1,
            status="done",
            current=entity_type == "assessment",
            route=f"/assessments/{assessment_id}",
            entities=[{"id": assessment_id, "title": assessment.title}],
        )
    )

    finding_status = "done" if findings else "missing"
    steps.append(
        WorkflowStepInfo(
            key="finding",
            label="Findings",
            count=len(findings),
            status=finding_status,
            current=entity_type == "finding",
            route=f"/findings?assessment_id={assessment_id}" if findings else None,
            entities=[{"id": f.id, "title": f.title} for f in findings[:3]],
            next_action_label="Finding erstellen" if not findings else None,
            next_action_route=f"/assessments/{assessment_id}?tab=findings"
            if not findings
            else None,
        )
    )

    risk_status = "done" if risks else "missing"
    steps.append(
        WorkflowStepInfo(
            key="risk",
            label="Risks",
            count=len(risks),
            status=risk_status,
            current=entity_type == "risk",
            route=f"/risks?assessment_id={assessment_id}" if risks else None,
            entities=[{"id": r.id, "title": r.title} for r in risks[:3]],
            next_action_label="Risiko ableiten" if not risks and findings else None,
            next_action_route=f"/assessments/{assessment_id}?tab=risks"
            if not risks and findings
            else None,
        )
    )

    rec_status = "done" if recommendations else "missing"
    steps.append(
        WorkflowStepInfo(
            key="recommendation",
            label="Empfehlungen",
            count=len(recommendations),
            status=rec_status,
            current=entity_type == "recommendation",
            route=f"/recommendations?assessment_id={assessment_id}" if recommendations else None,
            entities=[{"id": r.id, "title": r.title} for r in recommendations[:3]],
            next_action_label="Empfehlung erstellen" if not recommendations else None,
            next_action_route=f"/recommendations?assessment_id={assessment_id}"
            if not recommendations
            else None,
        )
    )

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
    steps.append(
        WorkflowStepInfo(
            key="cap",
            label="Maßnahmen (CAP)",
            count=cap_done,
            status=cap_status,
            current=entity_type == "cap",
            route=f"/corrective-action-plans?assessment_id={assessment_id}" if caps else None,
            entities=[{"id": c.id, "title": c.title} for c in caps[:3]],
            next_action_label=f"CAP erstellen ({remaining_caps} offen)"
            if remaining_caps > 0
            else None,
            next_action_route=f"/corrective-action-plans?assessment_id={assessment_id}"
            if remaining_caps > 0
            else None,
        )
    )

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


async def get_grievance_workflow_context(
    entity_type: str,
    entity_id: str,
    org_id: str,
    session: AsyncSession,
) -> WorkflowContext | None:
    """Return the Grievance → Remedy workflow chain for a grievance or remedy_case entity."""
    grievance_repo = SQLGrievanceRepository(session)
    supplier_repo = SQLSupplierRepository(session)
    finding_repo = SQLFindingRepository(session)

    # ── 1. Resolve grievance_id ───────────────────────────────────────────────
    grievance_id: str | None = None

    if entity_type == "grievance":
        grievance_id = entity_id
    elif entity_type == "remedy_case":
        stmt = select(RemedyCaseModel.source_grievance_id).where(
            cast(RemedyCaseModel.id, PG_UUID) == cast(entity_id, PG_UUID),
            cast(RemedyCaseModel.organization_id, PG_UUID) == cast(org_id, PG_UUID),
        )
        result = await session.execute(stmt)
        src = result.scalar_one_or_none()
        grievance_id = str(src) if src else None

    if not grievance_id:
        return None

    # ── 2. Load grievance (org scope check) ───────────────────────────────────
    grievance = await grievance_repo.get_by_id(grievance_id)
    if not grievance or grievance.organization_id != org_id:
        return None

    # ── 3. Load related supplier and linked finding ────────────────────────────
    supplier = None
    if grievance.related_supplier_id:
        supplier = await supplier_repo.get_by_id(grievance.related_supplier_id)

    linked_finding = None
    if grievance.linked_finding_id:
        linked_finding = await finding_repo.get_by_id(grievance.linked_finding_id)

    # ── 4. Load remedy cases for this grievance ────────────────────────────────
    remedy_stmt = (
        select(RemedyCaseModel)
        .where(
            cast(RemedyCaseModel.source_grievance_id, PG_UUID) == cast(grievance_id, PG_UUID),
            cast(RemedyCaseModel.organization_id, PG_UUID) == cast(org_id, PG_UUID),
        )
        .order_by(RemedyCaseModel.created_at.desc())
        .limit(10)
    )
    remedy_result = await session.execute(remedy_stmt)
    remedy_cases = remedy_result.scalars().all()

    # ── 5. Build workflow steps ───────────────────────────────────────────────
    steps: list[WorkflowStepInfo] = []

    if supplier:
        steps.append(
            WorkflowStepInfo(
                key="supplier",
                label="Lieferant",
                count=1,
                status="done",
                current=entity_type == "supplier",
                route=f"/suppliers/{supplier.id}",
                entities=[{"id": supplier.id, "title": supplier.name}],
            )
        )

    steps.append(
        WorkflowStepInfo(
            key="grievance",
            label="Beschwerde",
            count=1,
            status="done",
            current=entity_type == "grievance",
            route=f"/grievances/{grievance_id}",
            entities=[{"id": grievance_id, "title": grievance.title}],
        )
    )

    if linked_finding:
        steps.append(
            WorkflowStepInfo(
                key="finding",
                label="Finding",
                count=1,
                status="done",
                current=False,
                route=f"/findings/{linked_finding.id}",
                entities=[{"id": linked_finding.id, "title": linked_finding.title}],
            )
        )

    remedy_status: str
    if remedy_cases:
        all_closed = all(str(r.status) in ("closed", "resolved") for r in remedy_cases)
        remedy_status = "done" if all_closed else "partial"
    else:
        remedy_status = "missing"

    steps.append(
        WorkflowStepInfo(
            key="remedy_case",
            label="Abhilfemaßnahme",
            count=len(remedy_cases),
            status=remedy_status,
            current=entity_type == "remedy_case",
            route=f"/remedy-cases?grievance_id={grievance_id}" if remedy_cases else None,
            entities=[
                {"id": str(r.id), "title": str(r.title)} for r in remedy_cases[:3]
            ],
            next_action_label="Abhilfemaßnahme erstellen" if not remedy_cases else None,
            next_action_route=f"/remedy-cases?grievance_id={grievance_id}"
            if not remedy_cases
            else None,
        )
    )

    # ── 6. Compute completion ─────────────────────────────────────────────────
    done_count = sum(1 for s in steps if s.status in ("done", "partial"))
    completion_pct = int((done_count / len(steps)) * 100) if steps else 0

    next_step = next(
        (s for s in steps if s.status == "missing" and s.next_action_route),
        None,
    )

    return WorkflowContext(
        workflow_id="grievance_remedy",
        workflow_name="Beschwerde & Abhilfemaßnahme",
        entity_type=entity_type,
        entity_id=entity_id,
        assessment_id=None,
        supplier_id=grievance.related_supplier_id,
        supplier_name=supplier.name if supplier else None,
        steps=steps,
        completion_pct=completion_pct,
        next_step=next_step,
    )


async def get_active_workflows(
    org_id: str,
    session: AsyncSession,
    *,
    limit: int = 20,
) -> list[ActiveWorkflow]:
    """Return incomplete workflows for the org (both Lieferketten and Grievance chains)."""
    supplier_repo = SQLSupplierRepository(session)
    results: list[ActiveWorkflow] = []

    # ── Lieferketten: assessments where CAPs < findings (incomplete chain) ────
    lk_stmt = text("""
        SELECT
            a.id        AS assessment_id,
            a.title     AS assessment_title,
            a.supplier_id,
            COUNT(DISTINCT f.id)   AS finding_count,
            COUNT(DISTINCT r.id)   AS risk_count,
            COUNT(DISTINCT rec.id) AS rec_count,
            COUNT(DISTINCT cap.id) AS cap_count
        FROM assessments a
        LEFT JOIN findings f   ON f.assessment_id   = a.id
        LEFT JOIN risks    r   ON r.assessment_id   = a.id
        LEFT JOIN recommendations rec ON rec.assessment_id = a.id
        LEFT JOIN corrective_action_plans cap ON cap.finding_id = f.id
        WHERE a.organization_id = :org_id
        GROUP BY a.id, a.title, a.supplier_id
        HAVING
            COUNT(DISTINCT f.id) = 0
            OR COUNT(DISTINCT cap.id) < COUNT(DISTINCT f.id)
        ORDER BY a.id
        LIMIT :lim
    """)
    lk_rows = (await session.execute(lk_stmt, {"org_id": org_id, "lim": limit})).all()

    for row in lk_rows:
        # 5 steps: supplier, assessment, finding, risk, rec, cap — but supplier optional
        # simplify: 5 core steps (assessment always 1)
        step_count = 5  # assessment + finding + risk + rec + cap
        done = 1  # assessment always exists
        if row.finding_count > 0:
            done += 1
        if row.risk_count > 0:
            done += 1
        if row.rec_count > 0:
            done += 1
        if row.cap_count > 0 and row.cap_count >= row.finding_count:
            done += 1
        pct = int((done / step_count) * 100)

        supplier_name: str | None = None
        if row.supplier_id:
            s = await supplier_repo.get_by_id(row.supplier_id)
            supplier_name = s.name if s else None

        if row.finding_count == 0:
            next_label = "Finding erstellen"
        elif row.risk_count == 0:
            next_label = "Risiko ableiten"
        elif row.rec_count == 0:
            next_label = "Empfehlung erstellen"
        else:
            next_label = f"CAP erstellen ({row.finding_count - row.cap_count} offen)"

        results.append(
            ActiveWorkflow(
                workflow_id="lieferketten_sorgfalt",
                workflow_name="Lieferketten-Sorgfaltspflicht",
                entity_type="assessment",
                entity_id=str(row.assessment_id),
                entity_label=str(row.assessment_title),
                supplier_id=str(row.supplier_id) if row.supplier_id else None,
                supplier_name=supplier_name,
                completion_pct=pct,
                next_step_label=next_label,
                route=f"/assessments/{row.assessment_id}",
            )
        )

    # ── Grievance: open grievances without a remedy case ─────────────────────
    grv_stmt = (
        select(GrievanceReportModel)
        .where(
            GrievanceReportModel.organization_id == org_id,
            GrievanceReportModel.grievance_status.notin_(["closed", "resolved"]),
        )
        .order_by(GrievanceReportModel.created_at.desc())
        .limit(limit)
    )
    grv_rows = (await session.execute(grv_stmt)).scalars().all()

    for grv in grv_rows:
        # Check if any remedy case exists for this grievance
        remedy_count_stmt = select(func.count()).where(
            cast(RemedyCaseModel.source_grievance_id, PG_UUID) == cast(str(grv.id), PG_UUID),
            cast(RemedyCaseModel.organization_id, PG_UUID) == cast(org_id, PG_UUID),
        )
        remedy_count = (await session.execute(remedy_count_stmt)).scalar_one()

        step_count = 2  # grievance + remedy
        done = 1 + (1 if remedy_count > 0 else 0)
        pct = int((done / step_count) * 100)

        supplier_name = None
        if grv.related_supplier_id:
            s = await supplier_repo.get_by_id(grv.related_supplier_id)
            supplier_name = s.name if s else None

        results.append(
            ActiveWorkflow(
                workflow_id="grievance_remedy",
                workflow_name="Beschwerde & Abhilfemaßnahme",
                entity_type="grievance",
                entity_id=str(grv.id),
                entity_label=str(grv.title),
                supplier_id=str(grv.related_supplier_id) if grv.related_supplier_id else None,
                supplier_name=supplier_name,
                completion_pct=pct,
                next_step_label="Abhilfemaßnahme erstellen" if remedy_count == 0 else None,
                route=f"/grievances/{grv.id}",
            )
        )

    # Sort by completion ascending (most incomplete first)
    results.sort(key=lambda w: w.completion_pct)
    return results[:limit]
