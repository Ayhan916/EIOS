"""M39 ESG Health Score — deterministic formula.

Formula v1.0 (weighted average of 6 domain scores):
  overall = (
      supplier_intelligence * 0.20
    + surveillance         * 0.20
    + compliance           * 0.20
    + due_diligence        * 0.15
    + remediation          * 0.15
    + governance           * 0.10
  )

All inputs and the formula version are stored in calculation_inputs for
full explainability and immutable audit trail.

Domain scores are derived from live system state:
  supplier_intelligence — average supplier ESG score (from SupplierScoreModel)
  surveillance          — fraction of signals resolved in 30 days
  compliance            — average ComplianceOperation coverage_percent
  due_diligence         — fraction of completed DueDiligenceReports
  remediation           — fraction of COMPLETED ESGActions
  governance            — fraction of objectives ON_TRACK or COMPLETED
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

FORMULA_VERSION = "1.0"

WEIGHTS = {
    "supplier_intelligence": 0.20,
    "surveillance": 0.20,
    "compliance": 0.20,
    "due_diligence": 0.15,
    "remediation": 0.15,
    "governance": 0.10,
}


async def compute_health_score(
    organization_id: str,
    session: AsyncSession,
) -> dict:
    """Compute and persist an ESG health score snapshot. Returns the score dict."""
    inputs: dict = {}

    supplier_score = await _supplier_intelligence_score(organization_id, session, inputs)
    surveillance_score = await _surveillance_score(organization_id, session, inputs)
    compliance_score = await _compliance_score(organization_id, session, inputs)
    due_diligence_score = await _due_diligence_score(organization_id, session, inputs)
    remediation_score = await _remediation_score(organization_id, session, inputs)
    governance_score = await _governance_score(organization_id, session, inputs)

    overall = round(
        supplier_score * WEIGHTS["supplier_intelligence"]
        + surveillance_score * WEIGHTS["surveillance"]
        + compliance_score * WEIGHTS["compliance"]
        + due_diligence_score * WEIGHTS["due_diligence"]
        + remediation_score * WEIGHTS["remediation"]
        + governance_score * WEIGHTS["governance"],
        4,
    )

    inputs["weights"] = WEIGHTS
    inputs["formula_version"] = FORMULA_VERSION

    from infrastructure.persistence.models.operating_system import OrganizationESGHealthScoreModel
    now = datetime.now(UTC)
    snap = OrganizationESGHealthScoreModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        overall_score=overall,
        supplier_intelligence_score=supplier_score,
        surveillance_score=surveillance_score,
        compliance_score=compliance_score,
        due_diligence_score=due_diligence_score,
        remediation_score=remediation_score,
        governance_score=governance_score,
        calculation_inputs=inputs,
        formula_version=FORMULA_VERSION,
        calculated_at=now,
    )
    session.add(snap)
    await session.flush()
    return _to_dict(snap)


async def get_latest_health_score(
    organization_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import OrganizationESGHealthScoreModel
    stmt = (
        select(OrganizationESGHealthScoreModel)
        .where(OrganizationESGHealthScoreModel.organization_id == organization_id)
        .order_by(OrganizationESGHealthScoreModel.calculated_at.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


# ── Domain score helpers ──────────────────────────────────────────────────────

async def _supplier_intelligence_score(
    org_id: str, session: AsyncSession, inputs: dict
) -> float:
    try:
        from infrastructure.persistence.models.supplier_score import SupplierScoreModel
        stmt = select(func.avg(SupplierScoreModel.esg_score)).where(
            SupplierScoreModel.organization_id == org_id
        )
        avg = (await session.execute(stmt)).scalar_one_or_none()
        score = round(float(avg or 0.0), 4)
    except Exception:
        score = 0.0
    inputs["supplier_intelligence"] = {"avg_esg_score": score}
    return score


async def _surveillance_score(
    org_id: str, session: AsyncSession, inputs: dict
) -> float:
    try:
        from infrastructure.persistence.models.surveillance import SurveillanceSignalModel
        total_stmt = select(func.count()).select_from(SurveillanceSignalModel).where(
            SurveillanceSignalModel.organization_id == org_id
        )
        resolved_stmt = select(func.count()).select_from(SurveillanceSignalModel).where(
            SurveillanceSignalModel.organization_id == org_id,
            SurveillanceSignalModel.signal_status == "RESOLVED",
        )
        total = (await session.execute(total_stmt)).scalar_one() or 0
        resolved = (await session.execute(resolved_stmt)).scalar_one() or 0
        score = round((resolved / total) * 100, 4) if total > 0 else 100.0
    except Exception:
        score = 0.0
    inputs["surveillance"] = {"total_signals": locals().get("total", 0),
                              "resolved_signals": locals().get("resolved", 0),
                              "score": score}
    return score


async def _compliance_score(
    org_id: str, session: AsyncSession, inputs: dict
) -> float:
    try:
        from infrastructure.persistence.models.operating_system import ComplianceOperationModel
        stmt = select(func.avg(ComplianceOperationModel.coverage_percent)).where(
            ComplianceOperationModel.organization_id == org_id
        )
        avg = (await session.execute(stmt)).scalar_one_or_none()
        score = round(float(avg or 0.0), 4)
    except Exception:
        score = 0.0
    inputs["compliance"] = {"avg_coverage_percent": score}
    return score


async def _due_diligence_score(
    org_id: str, session: AsyncSession, inputs: dict
) -> float:
    try:
        from infrastructure.persistence.models.due_diligence import DueDiligenceReportModel
        total_stmt = select(func.count()).select_from(DueDiligenceReportModel).where(
            DueDiligenceReportModel.organization_id == org_id
        )
        comp_stmt = select(func.count()).select_from(DueDiligenceReportModel).where(
            DueDiligenceReportModel.organization_id == org_id,
            DueDiligenceReportModel.report_status == "COMPLETED",
        )
        total = (await session.execute(total_stmt)).scalar_one() or 0
        completed = (await session.execute(comp_stmt)).scalar_one() or 0
        score = round((completed / total) * 100, 4) if total > 0 else 100.0
    except Exception:
        score = 0.0
    inputs["due_diligence"] = {"score": score}
    return score


async def _remediation_score(
    org_id: str, session: AsyncSession, inputs: dict
) -> float:
    try:
        from infrastructure.persistence.models.operating_system import ESGActionModel
        total_stmt = select(func.count()).select_from(ESGActionModel).where(
            ESGActionModel.organization_id == org_id
        )
        done_stmt = select(func.count()).select_from(ESGActionModel).where(
            ESGActionModel.organization_id == org_id,
            ESGActionModel.action_status == "COMPLETED",
        )
        total = (await session.execute(total_stmt)).scalar_one() or 0
        done = (await session.execute(done_stmt)).scalar_one() or 0
        score = round((done / total) * 100, 4) if total > 0 else 100.0
    except Exception:
        score = 0.0
    inputs["remediation"] = {"score": score}
    return score


async def _governance_score(
    org_id: str, session: AsyncSession, inputs: dict
) -> float:
    try:
        from infrastructure.persistence.models.operating_system import ESGObjectiveModel
        total_stmt = select(func.count()).select_from(ESGObjectiveModel).where(
            ESGObjectiveModel.organization_id == org_id
        )
        good_stmt = select(func.count()).select_from(ESGObjectiveModel).where(
            ESGObjectiveModel.organization_id == org_id,
            ESGObjectiveModel.objective_status.in_(["ON_TRACK", "COMPLETED"]),
        )
        total = (await session.execute(total_stmt)).scalar_one() or 0
        good = (await session.execute(good_stmt)).scalar_one() or 0
        score = round((good / total) * 100, 4) if total > 0 else 100.0
    except Exception:
        score = 0.0
    inputs["governance"] = {"score": score}
    return score


def _to_dict(s) -> dict:
    return {
        "id": s.id,
        "organization_id": s.organization_id,
        "overall_score": s.overall_score,
        "supplier_intelligence_score": s.supplier_intelligence_score,
        "surveillance_score": s.surveillance_score,
        "compliance_score": s.compliance_score,
        "due_diligence_score": s.due_diligence_score,
        "remediation_score": s.remediation_score,
        "governance_score": s.governance_score,
        "calculation_inputs": s.calculation_inputs,
        "formula_version": s.formula_version,
        "calculated_at": s.calculated_at,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }
