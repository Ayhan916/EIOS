"""
M48 Pipeline Readiness — per-step completeness check for the EIOS due diligence pipeline.

Returns a single aggregated readiness response covering all 9 process steps.
The frontend caches this for 5 minutes and uses it to drive contextual banners
and sidebar warning indicators — no N separate API calls needed.

Security: organization_id is always derived from the authenticated user, never
from query params. All queries are scoped to the org.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.user import User
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.associations import assessment_evidence, risk_finding
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.report import ReportModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.supplier import SupplierModel
from interfaces.api.deps import get_current_user, get_db

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MissingItem(BaseModel):
    type: str        # "upload" | "data" | "action"
    label: str
    count: int
    href: str


class StepReadiness(BaseModel):
    key: str
    status: str      # "ok" | "warning" | "error"
    score: int       # 0–100
    open_count: int
    missing: list[MissingItem]


class PipelineReadiness(BaseModel):
    overall_score: int
    steps: list[StepReadiness]
    checked_at: str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/readiness", response_model=PipelineReadiness)
async def get_pipeline_readiness(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PipelineReadiness:
    """Return per-step readiness for the 9-stage EIOS due diligence pipeline."""
    org_id = current_user.organization_id

    # ── Step 1: Suppliers ─────────────────────────────────────────────────────
    sup_total: int = await db.scalar(
        select(func.count(SupplierModel.id)).where(SupplierModel.organization_id == org_id)
    ) or 0
    sup_no_nace: int = await db.scalar(
        select(func.count(SupplierModel.id)).where(
            SupplierModel.organization_id == org_id,
            SupplierModel.nace_code.is_(None),
        )
    ) or 0
    sup_no_country: int = await db.scalar(
        select(func.count(SupplierModel.id)).where(
            SupplierModel.organization_id == org_id,
            SupplierModel.country == "",
        )
    ) or 0

    # ── Step 2 & 3: Assessments ───────────────────────────────────────────────
    asm_total: int = await db.scalar(
        select(func.count(AssessmentModel.id)).where(
            AssessmentModel.organization_id == org_id
        )
    ) or 0
    asm_draft: int = await db.scalar(
        select(func.count(AssessmentModel.id)).where(
            AssessmentModel.organization_id == org_id,
            AssessmentModel.review_status == "Draft",
        )
    ) or 0
    # Assessments with no linked evidence documents (need PDF/Excel upload)
    asm_no_evidence: int = await db.scalar(
        select(func.count(AssessmentModel.id)).where(
            AssessmentModel.organization_id == org_id,
            ~(
                select(assessment_evidence.c.assessment_id)
                .where(assessment_evidence.c.assessment_id == AssessmentModel.id)
                .exists()
            ),
        )
    ) or 0

    # ── Step 4: Findings ──────────────────────────────────────────────────────
    fin_total: int = await db.scalar(
        select(func.count(FindingModel.id))
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(AssessmentModel.organization_id == org_id)
    ) or 0
    # Findings with no linked risk
    fin_no_risk: int = await db.scalar(
        select(func.count(FindingModel.id))
        .join(AssessmentModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == org_id,
            ~(
                select(risk_finding.c.finding_id)
                .where(risk_finding.c.finding_id == FindingModel.id)
                .exists()
            ),
        )
    ) or 0

    # ── Step 5: Risks ─────────────────────────────────────────────────────────
    rsk_total: int = await db.scalar(
        select(func.count(RiskModel.id))
        .join(AssessmentModel, RiskModel.assessment_id == AssessmentModel.id)
        .where(AssessmentModel.organization_id == org_id)
    ) or 0

    # ── Step 6 & 7 & 8: Recommendations ──────────────────────────────────────
    org_assessment_ids = select(AssessmentModel.id).where(
        AssessmentModel.organization_id == org_id
    ).scalar_subquery()
    rec_total: int = await db.scalar(
        select(func.count(RecommendationModel.id)).where(
            RecommendationModel.assessment_id.in_(org_assessment_ids)
        )
    ) or 0
    rec_open: int = await db.scalar(
        select(func.count(RecommendationModel.id)).where(
            RecommendationModel.assessment_id.in_(org_assessment_ids),
            RecommendationModel.action_status == "open",
        )
    ) or 0
    now = datetime.now(UTC)
    rec_overdue: int = await db.scalar(
        select(func.count(RecommendationModel.id)).where(
            RecommendationModel.assessment_id.in_(org_assessment_ids),
            RecommendationModel.action_status == "open",
            RecommendationModel.due_date.is_not(None),
            RecommendationModel.due_date < now,
        )
    ) or 0

    # ── Step 9: Reports ───────────────────────────────────────────────────────
    cutoff = now - timedelta(days=90)
    rep_recent: int = await db.scalar(
        select(func.count(ReportModel.id)).where(
            ReportModel.organization_id == org_id,
            ReportModel.created_at >= cutoff,
        )
    ) or 0

    # ── Derive step readiness ─────────────────────────────────────────────────
    steps: list[StepReadiness] = []

    # Step 1 — Supplier Onboarding
    s1_missing: list[MissingItem] = []
    if sup_total == 0:
        s1_missing.append(MissingItem(type="action", label="Noch keine Lieferanten angelegt", count=0, href="/suppliers"))
    else:
        if sup_no_nace > 0:
            s1_missing.append(MissingItem(type="data", label="NACE-Branchencode fehlt", count=sup_no_nace, href="/suppliers"))
        if sup_no_country > 0:
            s1_missing.append(MissingItem(type="data", label="Herkunftsland fehlt", count=sup_no_country, href="/suppliers"))
    steps.append(StepReadiness(
        key="onboard",
        status="ok" if not s1_missing else ("error" if sup_total == 0 else "warning"),
        score=100 if not s1_missing else (50 if sup_total > 0 else 0),
        open_count=sup_total,
        missing=s1_missing,
    ))

    # Step 2 — Assessment Planning
    s2_missing: list[MissingItem] = []
    if asm_total == 0:
        s2_missing.append(MissingItem(type="action", label="Kein Assessment geplant — Zeitplan erstellen", count=0, href="/assessments/schedules"))
    elif asm_draft > 0:
        s2_missing.append(MissingItem(type="action", label="Assessments noch im Entwurfsstatus", count=asm_draft, href="/assessments"))
    steps.append(StepReadiness(
        key="plan",
        status="ok" if not s2_missing else ("error" if asm_total == 0 else "warning"),
        score=100 if asm_total > 0 and asm_draft == 0 else (60 if asm_total > 0 else 0),
        open_count=asm_total,
        missing=s2_missing,
    ))

    # Step 3 — Assessment Execution (document evidence needed)
    s3_missing: list[MissingItem] = []
    if asm_no_evidence > 0:
        s3_missing.append(MissingItem(
            type="upload",
            label=f"Nachweise hochladen (PDF, Excel, CSV) — {asm_no_evidence} Assessment(s) ohne Dokumente",
            count=asm_no_evidence,
            href="/evidence",
        ))
    steps.append(StepReadiness(
        key="assess",
        status="ok" if not s3_missing else "warning",
        score=100 if not s3_missing else max(0, 100 - int((asm_no_evidence / max(asm_total, 1)) * 100)),
        open_count=asm_total,
        missing=s3_missing,
    ))

    # Step 4 — Findings Identification
    s4_missing: list[MissingItem] = []
    if asm_total > 0 and fin_total == 0:
        s4_missing.append(MissingItem(type="action", label="Keine Findings dokumentiert", count=0, href="/findings"))
    steps.append(StepReadiness(
        key="findings",
        status="ok" if not s4_missing else "warning",
        score=100 if fin_total > 0 else (0 if asm_total > 0 else 100),
        open_count=fin_total,
        missing=s4_missing,
    ))

    # Step 5 — Risk Derivation
    s5_missing: list[MissingItem] = []
    if fin_total > 0 and rsk_total == 0:
        s5_missing.append(MissingItem(type="action", label="Keine Risiken aus Findings abgeleitet", count=fin_total, href="/risks"))
    elif fin_no_risk > 0:
        s5_missing.append(MissingItem(type="action", label="Findings ohne Risikoverknüpfung", count=fin_no_risk, href="/risks"))
    steps.append(StepReadiness(
        key="risks",
        status="ok" if not s5_missing else "warning",
        score=100 if rsk_total > 0 and fin_no_risk == 0 else (50 if rsk_total > 0 else (0 if fin_total > 0 else 100)),
        open_count=rsk_total,
        missing=s5_missing,
    ))

    # Step 6 — Recommendations
    s6_missing: list[MissingItem] = []
    if rsk_total > 0 and rec_total == 0:
        s6_missing.append(MissingItem(type="action", label="Keine Empfehlungen zu offenen Risiken erstellt", count=rsk_total, href="/recommendations"))
    steps.append(StepReadiness(
        key="recommendations",
        status="ok" if not s6_missing else "warning",
        score=100 if rec_total > 0 else (0 if rsk_total > 0 else 100),
        open_count=rec_total,
        missing=s6_missing,
    ))

    # Step 7 — Remediation Planning
    s7_missing: list[MissingItem] = []
    if rec_overdue > 0:
        s7_missing.append(MissingItem(type="action", label="Überfällige Maßnahmen ohne Umsetzungsnachweis", count=rec_overdue, href="/recommendations"))
    steps.append(StepReadiness(
        key="remediation",
        status="ok" if not s7_missing else "error",
        score=100 if not s7_missing else max(0, 100 - int((rec_overdue / max(rec_open, 1)) * 100)),
        open_count=rec_open,
        missing=s7_missing,
    ))

    # Step 8 — Verification
    s8_missing: list[MissingItem] = []
    if rec_open > 0:
        s8_missing.append(MissingItem(type="action", label="Offene Maßnahmen warten auf Verifikation", count=rec_open, href="/recommendations"))
    steps.append(StepReadiness(
        key="verification",
        status="ok" if rec_open == 0 else "warning",
        score=100 if rec_open == 0 else max(0, 100 - int((rec_open / max(rec_total, 1)) * 50)),
        open_count=rec_open,
        missing=s8_missing,
    ))

    # Step 9 — Reporting & Disclosure
    s9_missing: list[MissingItem] = []
    if rep_recent == 0:
        s9_missing.append(MissingItem(type="action", label="Kein Bericht in den letzten 90 Tagen erstellt", count=0, href="/reports"))
    steps.append(StepReadiness(
        key="reporting",
        status="ok" if not s9_missing else "warning",
        score=100 if rep_recent > 0 else 0,
        open_count=rep_recent,
        missing=s9_missing,
    ))

    overall_score = int(sum(s.score for s in steps) / len(steps))

    return PipelineReadiness(
        overall_score=overall_score,
        steps=steps,
        checked_at=datetime.now(UTC).isoformat(),
    )
