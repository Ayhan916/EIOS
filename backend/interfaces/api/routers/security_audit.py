"""M49 — Security Audit API Router.

G-021: OWASP Top 10 pentest readiness + finding management
G-048: SOC 2 Type I controls management + readiness assessment
Production cutover checklist management
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from infrastructure.persistence.database import AsyncSessionFactory
from interfaces.api.deps import get_current_user, require_admin
from interfaces.api.schemas import UserResponse

router = APIRouter(tags=["security-audit"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class Soc2ControlUpdate(BaseModel):
    status: str = Field(..., pattern="^(Not Started|In Progress|Implemented|Tested)$")
    evidence_notes: str | None = None
    owner: str | None = None


class PentestFindingCreate(BaseModel):
    owasp_category: str = Field(..., pattern="^A(0[1-9]|10)$")
    title: str = Field(..., min_length=3, max_length=255)
    severity: str = Field("MEDIUM", pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFO)$")
    cvss_score: float | None = Field(None, ge=0.0, le=10.0)
    description: str | None = None
    remediation_notes: str | None = None
    reported_by: str | None = None


class ChecklistItemUpdate(BaseModel):
    status: str = Field(..., pattern="^(Pending|Complete|N/A)$")
    owner: str | None = None
    notes: str | None = None


# ── G-048: SOC 2 Controls ────────────────────────────────────────────────────

@router.post(
    "/security/soc2/seed",
    summary="G-048: Seed all SOC 2 Trust Service Criteria controls for the organisation",
    dependencies=[Depends(require_admin)],
)
async def seed_soc2_controls(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from application.security.soc2_service import SOC2_CONTROLS, get_eios_evidence
    from infrastructure.persistence.models.soc2_control import Soc2ControlModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session, session.begin():
        existing = await session.execute(
            select(Soc2ControlModel.control_id).where(
                Soc2ControlModel.organization_id == current_user.organization_id
            )
        )
        existing_ids = {row[0] for row in existing.all()}

        created = 0
        for ctrl in SOC2_CONTROLS:
            if ctrl["control_id"] in existing_ids:
                continue
            evidence = get_eios_evidence(ctrl["control_id"])
            model = Soc2ControlModel(
                id=str(uuid.uuid4()),
                organization_id=current_user.organization_id,
                control_id=ctrl["control_id"],
                category=ctrl["category"],
                control_name=ctrl["control_name"],
                description=ctrl["description"],
                status="In Progress" if evidence else "Not Started",
                evidence_notes=evidence,
            )
            session.add(model)
            created += 1

    return {"seeded": created, "already_existed": len(existing_ids), "total": len(SOC2_CONTROLS)}


@router.get(
    "/security/soc2/controls",
    summary="G-048: List SOC 2 controls for the organisation",
)
async def list_soc2_controls(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    category: str | None = Query(None),
    status: str | None = Query(None),
):
    from infrastructure.persistence.models.soc2_control import Soc2ControlModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session:
        q = select(Soc2ControlModel).where(
            Soc2ControlModel.organization_id == current_user.organization_id
        )
        if category:
            q = q.where(Soc2ControlModel.category == category)
        if status:
            q = q.where(Soc2ControlModel.status == status)
        result = await session.execute(q.order_by(Soc2ControlModel.control_id))
        controls = result.scalars().all()

    return {
        "items": [
            {
                "id": c.id,
                "control_id": c.control_id,
                "category": c.category,
                "control_name": c.control_name,
                "description": c.description,
                "status": c.status,
                "evidence_notes": c.evidence_notes,
                "owner": c.owner,
            }
            for c in controls
        ],
        "total": len(controls),
    }


@router.put(
    "/security/soc2/controls/{control_id}",
    summary="G-048: Update SOC 2 control status and evidence",
    dependencies=[Depends(require_admin)],
)
async def update_soc2_control(
    control_id: str,
    body: Soc2ControlUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.soc2_control import Soc2ControlModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session, session.begin():
        result = await session.execute(
            select(Soc2ControlModel).where(
                Soc2ControlModel.organization_id == current_user.organization_id,
                Soc2ControlModel.control_id == control_id,
            )
        )
        ctrl = result.scalar_one_or_none()
        if not ctrl:
            raise HTTPException(status_code=404, detail=f"Control {control_id} not found — run /seed first")
        ctrl.status = body.status
        if body.evidence_notes is not None:
            ctrl.evidence_notes = body.evidence_notes
        if body.owner is not None:
            ctrl.owner = body.owner

    return {"control_id": control_id, "status": body.status}


@router.get(
    "/security/soc2/readiness",
    summary="G-048: Compute SOC 2 Type I readiness score",
)
async def get_soc2_readiness(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from application.security.soc2_service import compute_readiness_score
    from infrastructure.persistence.models.soc2_control import Soc2ControlModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Soc2ControlModel).where(
                Soc2ControlModel.organization_id == current_user.organization_id
            )
        )
        controls = [
            {
                "organization_id": c.organization_id,
                "control_id": c.control_id,
                "category": c.category,
                "control_name": c.control_name,
                "status": c.status,
            }
            for c in result.scalars().all()
        ]

    report = compute_readiness_score(controls)
    return report.to_dict()


# ── G-021: Pentest Findings ───────────────────────────────────────────────────

@router.get(
    "/security/pentest/owasp",
    summary="G-021: OWASP Top 10 coverage assessment for EIOS",
)
async def get_owasp_assessment(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from application.security.pentest_readiness import assess_owasp_status
    return assess_owasp_status().to_dict()


@router.post(
    "/security/pentest/findings",
    summary="G-021: Log a pentest finding",
    dependencies=[Depends(require_admin)],
)
async def create_pentest_finding(
    body: PentestFindingCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.pentest_finding import PentestFindingModel

    finding = PentestFindingModel(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        owasp_category=body.owasp_category,
        title=body.title,
        severity=body.severity,
        status="Open",
        cvss_score=body.cvss_score,
        description=body.description,
        remediation_notes=body.remediation_notes,
        reported_by=body.reported_by,
        discovered_at=datetime.now(UTC),
    )
    async with AsyncSessionFactory() as session, session.begin():
        session.add(finding)

    return {"id": finding.id, "owasp_category": finding.owasp_category, "severity": finding.severity}


@router.get(
    "/security/pentest/findings",
    summary="G-021: List pentest findings",
)
async def list_pentest_findings(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    status: str | None = Query(None),
    severity: str | None = Query(None),
):
    from infrastructure.persistence.models.pentest_finding import PentestFindingModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session:
        q = select(PentestFindingModel).where(
            PentestFindingModel.organization_id == current_user.organization_id
        )
        if status:
            q = q.where(PentestFindingModel.status == status)
        if severity:
            q = q.where(PentestFindingModel.severity == severity)
        result = await session.execute(q.order_by(PentestFindingModel.created_at.desc()))
        findings = result.scalars().all()

    return {
        "items": [
            {
                "id": f.id,
                "owasp_category": f.owasp_category,
                "title": f.title,
                "severity": f.severity,
                "status": f.status,
                "cvss_score": f.cvss_score,
                "discovered_at": f.discovered_at.isoformat() if f.discovered_at else None,
                "remediated_at": f.remediated_at.isoformat() if f.remediated_at else None,
            }
            for f in findings
        ],
        "total": len(findings),
        "open": sum(1 for f in findings if f.status == "Open"),
    }


# ── Production Checklist ──────────────────────────────────────────────────────

@router.post(
    "/security/production-checklist/seed",
    summary="Seed production cutover checklist for the organisation",
    dependencies=[Depends(require_admin)],
)
async def seed_production_checklist(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from application.security.production_checklist_service import PRODUCTION_CHECKLIST
    from infrastructure.persistence.models.production_checklist import ProductionChecklistItemModel
    from sqlalchemy import select, func

    async with AsyncSessionFactory() as session:
        count_result = await session.execute(
            select(func.count()).where(
                ProductionChecklistItemModel.organization_id == current_user.organization_id
            )
        )
        existing_count = count_result.scalar() or 0

    if existing_count > 0:
        return {"seeded": 0, "message": "Checklist already seeded", "total": existing_count}

    async with AsyncSessionFactory() as session, session.begin():
        for item in PRODUCTION_CHECKLIST:
            model = ProductionChecklistItemModel(
                id=str(uuid.uuid4()),
                organization_id=current_user.organization_id,
                category=item["category"],
                item_name=item["item_name"],
                description=item["description"],
                priority=item["priority"],
                status="Pending",
            )
            session.add(model)

    return {"seeded": len(PRODUCTION_CHECKLIST), "total": len(PRODUCTION_CHECKLIST)}


@router.get(
    "/security/production-checklist",
    summary="List production cutover checklist items",
)
async def list_production_checklist(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    category: str | None = Query(None),
    status: str | None = Query(None),
):
    from application.security.production_checklist_service import compute_checklist_summary
    from infrastructure.persistence.models.production_checklist import ProductionChecklistItemModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session:
        q = select(ProductionChecklistItemModel).where(
            ProductionChecklistItemModel.organization_id == current_user.organization_id
        )
        if category:
            q = q.where(ProductionChecklistItemModel.category == category)
        if status:
            q = q.where(ProductionChecklistItemModel.status == status)
        result = await session.execute(q.order_by(ProductionChecklistItemModel.category, ProductionChecklistItemModel.priority))
        items = result.scalars().all()

    item_dicts = [
        {
            "id": i.id,
            "category": i.category,
            "item_name": i.item_name,
            "description": i.description,
            "status": i.status,
            "priority": i.priority,
            "owner": i.owner,
            "notes": i.notes,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
        }
        for i in items
    ]
    summary = compute_checklist_summary(item_dicts)
    return {"items": item_dicts, "summary": summary.to_dict()}


@router.put(
    "/security/production-checklist/{item_id}",
    summary="Update a production checklist item",
    dependencies=[Depends(require_admin)],
)
async def update_checklist_item(
    item_id: str,
    body: ChecklistItemUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from infrastructure.persistence.models.production_checklist import ProductionChecklistItemModel

    async with AsyncSessionFactory() as session, session.begin():
        item = await session.get(ProductionChecklistItemModel, item_id)
        if not item or item.organization_id != current_user.organization_id:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        item.status = body.status
        if body.owner is not None:
            item.owner = body.owner
        if body.notes is not None:
            item.notes = body.notes
        if body.status == "Complete" and not item.completed_at:
            item.completed_at = datetime.now(UTC)

    return {"id": item_id, "status": body.status}


# ── M50.2: Auditor Sign-off Package ──────────────────────────────────────────

@router.get(
    "/security/auditor/sign-off",
    summary="M50.2: Generate auditor sign-off readiness package (JSON)",
)
async def get_auditor_sign_off_package(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Returns a structured sign-off readiness package for external auditors.

    Aggregates SOC2 readiness, OWASP coverage, production checklist, and
    open pentest findings into a single auditor-facing JSON document.
    """
    from application.security.pentest_readiness import assess_owasp_status
    from application.security.soc2_service import compute_readiness_score
    from application.security.production_checklist_service import compute_checklist_summary
    from infrastructure.persistence.models.soc2_control import Soc2ControlModel
    from infrastructure.persistence.models.pentest_finding import PentestFindingModel
    from infrastructure.persistence.models.production_checklist import ProductionChecklistItemModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session:
        soc2_res = await session.execute(
            select(Soc2ControlModel).where(
                Soc2ControlModel.organization_id == current_user.organization_id
            )
        )
        soc2_rows = soc2_res.scalars().all()
        soc2_controls = [
            {
                "organization_id": c.organization_id,
                "control_id": c.control_id,
                "category": c.category,
                "control_name": c.control_name,
                "status": c.status,
                "evidence_notes": c.evidence_notes,
                "owner": c.owner,
            }
            for c in soc2_rows
        ]

        findings_res = await session.execute(
            select(PentestFindingModel).where(
                PentestFindingModel.organization_id == current_user.organization_id
            )
        )
        pentest_findings = [
            {
                "owasp_category": f.owasp_category,
                "title": f.title,
                "severity": f.severity,
                "status": f.status,
                "cvss_score": f.cvss_score,
            }
            for f in findings_res.scalars().all()
        ]

        checklist_res = await session.execute(
            select(ProductionChecklistItemModel).where(
                ProductionChecklistItemModel.organization_id == current_user.organization_id
            )
        )
        checklist_items = [
            {"category": i.category, "item_name": i.item_name, "status": i.status, "priority": i.priority, "owner": i.owner}
            for i in checklist_res.scalars().all()
        ]

    soc2_report = compute_readiness_score(
        [{"organization_id": c["organization_id"], "control_id": c["control_id"], "category": c["category"],
          "control_name": c["control_name"], "status": c["status"]} for c in soc2_controls]
    )
    owasp_assessment = assess_owasp_status()
    checklist_summary = compute_checklist_summary(
        [{"category": i["category"], "status": i["status"], "priority": i["priority"]} for i in checklist_items]
    )

    critical_open = sum(1 for f in pentest_findings if f["severity"] == "CRITICAL" and f["status"] == "Open")
    high_open = sum(1 for f in pentest_findings if f["severity"] == "HIGH" and f["status"] == "Open")
    ga_ready = (
        soc2_report.overall_pct >= 80.0
        and owasp_assessment.overall_pct >= 80.0
        and checklist_summary.completion_pct >= 90.0
        and critical_open == 0
        and high_open == 0
    )

    return {
        "document_type": "EIOS Auditor Sign-Off Package",
        "generated_at": datetime.now(UTC).isoformat(),
        "organization_id": current_user.organization_id,
        "prepared_by": current_user.email,
        "ga_ready": ga_ready,
        "soc2": {
            "readiness_pct": soc2_report.overall_pct,
            "implemented": soc2_report.implemented,
            "total": soc2_report.total_controls,
            "by_category": soc2_report.by_category if hasattr(soc2_report, "by_category") else {},
            "controls": soc2_controls,
        },
        "owasp": {
            "coverage_pct": owasp_assessment.overall_pct,
            "categories_covered": owasp_assessment.implemented,
            "total": owasp_assessment.total,
        },
        "pentest_findings": pentest_findings,
        "production_checklist": {
            "completion_pct": checklist_summary.completion_pct,
            "complete": checklist_summary.complete,
            "total": checklist_summary.total,
            "items": checklist_items,
        },
    }


# ── Security Summary ──────────────────────────────────────────────────────────

@router.get(
    "/security/audit-summary",
    summary="Complete security posture summary (SOC2 + OWASP + Checklist)",
)
async def get_security_audit_summary(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    from application.security.pentest_readiness import assess_owasp_status
    from application.security.soc2_service import compute_readiness_score
    from application.security.production_checklist_service import compute_checklist_summary
    from infrastructure.persistence.models.soc2_control import Soc2ControlModel
    from infrastructure.persistence.models.pentest_finding import PentestFindingModel
    from infrastructure.persistence.models.production_checklist import ProductionChecklistItemModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session:
        soc2_res = await session.execute(
            select(Soc2ControlModel).where(
                Soc2ControlModel.organization_id == current_user.organization_id
            )
        )
        soc2_controls = [
            {"organization_id": c.organization_id, "control_id": c.control_id,
             "category": c.category, "control_name": c.control_name, "status": c.status}
            for c in soc2_res.scalars().all()
        ]

        findings_res = await session.execute(
            select(PentestFindingModel).where(
                PentestFindingModel.organization_id == current_user.organization_id,
                PentestFindingModel.status == "Open",
            )
        )
        open_findings = findings_res.scalars().all()

        checklist_res = await session.execute(
            select(ProductionChecklistItemModel).where(
                ProductionChecklistItemModel.organization_id == current_user.organization_id
            )
        )
        checklist_items = [
            {"category": i.category, "status": i.status, "priority": i.priority}
            for i in checklist_res.scalars().all()
        ]

    soc2_report = compute_readiness_score(soc2_controls)
    owasp_assessment = assess_owasp_status()
    checklist_summary = compute_checklist_summary(checklist_items)

    critical_open = sum(1 for f in open_findings if f.severity == "CRITICAL")
    high_open = sum(1 for f in open_findings if f.severity == "HIGH")

    ga_ready = (
        soc2_report.overall_pct >= 80.0
        and owasp_assessment.overall_pct >= 80.0
        and checklist_summary.completion_pct >= 90.0
        and critical_open == 0
        and high_open == 0
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "organization_id": current_user.organization_id,
        "ga_ready": ga_ready,
        "soc2": {
            "readiness_pct": soc2_report.overall_pct,
            "implemented": soc2_report.implemented,
            "total": soc2_report.total_controls,
        },
        "owasp": {
            "coverage_pct": owasp_assessment.overall_pct,
            "categories_covered": owasp_assessment.implemented,
            "total": owasp_assessment.total,
        },
        "pentest": {
            "open_findings": len(open_findings),
            "critical_open": critical_open,
            "high_open": high_open,
        },
        "production_checklist": {
            "completion_pct": checklist_summary.completion_pct,
            "complete": checklist_summary.complete,
            "total": checklist_summary.total,
        },
    }
