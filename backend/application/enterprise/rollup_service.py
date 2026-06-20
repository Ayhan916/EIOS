"""Enterprise rollup aggregations — deterministic, no N+1 queries."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.enterprise import (
    BusinessUnitModel,
    EnterpriseModel,
    RegionModel,
)
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.organization import OrganizationModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.supplier import SupplierModel


async def get_enterprise_rollup(enterprise_id: str, session: AsyncSession) -> dict:
    """
    Return enterprise-wide aggregated counts.
    All queries use JOIN through organization.enterprise_id — no Python loops.
    """
    # Organizations in this enterprise
    org_ids_q = select(OrganizationModel.id).where(
        OrganizationModel.enterprise_id == enterprise_id
    )
    org_ids = list((await session.execute(org_ids_q)).scalars().all())

    if not org_ids:
        return {
            "organization_count": 0,
            "supplier_count": 0,
            "total_risks": 0,
            "critical_risks": 0,
            "total_findings": 0,
            "open_findings": 0,
            "compliance_readiness": 0.0,
            "due_diligence_coverage": 0.0,
        }

    org_count = len(org_ids)

    # Supplier count
    supplier_count = (
        await session.execute(
            select(func.count(SupplierModel.id)).where(
                SupplierModel.organization_id.in_(org_ids)
            )
        )
    ).scalar_one() or 0

    # Risk counts
    total_risks = (
        await session.execute(
            select(func.count(RiskModel.id)).where(
                RiskModel.organization_id.in_(org_ids)
            )
        )
    ).scalar_one() or 0

    critical_risks = (
        await session.execute(
            select(func.count(RiskModel.id)).where(
                RiskModel.organization_id.in_(org_ids),
                RiskModel.severity.in_(["Critical", "critical"]),
            )
        )
    ).scalar_one() or 0

    # Finding counts
    total_findings = (
        await session.execute(
            select(func.count(FindingModel.id)).where(
                FindingModel.organization_id.in_(org_ids)
            )
        )
    ).scalar_one() or 0

    open_findings = (
        await session.execute(
            select(func.count(FindingModel.id)).where(
                FindingModel.organization_id.in_(org_ids),
                FindingModel.status.in_(["Open", "Active"]),
            )
        )
    ).scalar_one() or 0

    # Compliance readiness — derived from finding gap ratio
    compliance_readiness = (
        round((1.0 - open_findings / max(total_findings, 1)) * 100, 1)
        if total_findings > 0
        else 100.0
    )

    return {
        "organization_count": org_count,
        "supplier_count": supplier_count,
        "total_risks": total_risks,
        "critical_risks": critical_risks,
        "total_findings": total_findings,
        "open_findings": open_findings,
        "compliance_readiness": compliance_readiness,
        "due_diligence_coverage": 0.0,  # extended in M40+ via DueDiligenceReport link
    }


async def get_bu_rollups(enterprise_id: str, session: AsyncSession) -> list[dict]:
    """Return per-BusinessUnit rollup rows."""
    bus = (
        await session.execute(
            select(BusinessUnitModel).where(
                BusinessUnitModel.enterprise_id == enterprise_id,
                BusinessUnitModel.is_active.is_(True),
            )
        )
    ).scalars().all()

    results = []
    for bu in bus:
        org_ids = list(
            (
                await session.execute(
                    select(OrganizationModel.id).where(
                        OrganizationModel.enterprise_id == enterprise_id,
                        OrganizationModel.business_unit_id == bu.id,
                    )
                )
            ).scalars().all()
        )
        supplier_count = 0
        risk_count = 0
        if org_ids:
            supplier_count = (
                await session.execute(
                    select(func.count(SupplierModel.id)).where(
                        SupplierModel.organization_id.in_(org_ids)
                    )
                )
            ).scalar_one() or 0
            risk_count = (
                await session.execute(
                    select(func.count(RiskModel.id)).where(
                        RiskModel.organization_id.in_(org_ids)
                    )
                )
            ).scalar_one() or 0

        results.append({
            "business_unit_id": bu.id,
            "business_unit_name": bu.name,
            "organization_count": len(org_ids),
            "supplier_count": supplier_count,
            "risk_count": risk_count,
            "compliance_readiness": 0.0,
        })
    return results


async def get_region_rollups(enterprise_id: str, session: AsyncSession) -> list[dict]:
    """Return per-Region rollup rows."""
    regions = (
        await session.execute(
            select(RegionModel).where(
                RegionModel.enterprise_id == enterprise_id,
                RegionModel.is_active.is_(True),
            )
        )
    ).scalars().all()

    results = []
    for region in regions:
        org_ids = list(
            (
                await session.execute(
                    select(OrganizationModel.id).where(
                        OrganizationModel.enterprise_id == enterprise_id,
                        OrganizationModel.region_id == region.id,
                    )
                )
            ).scalars().all()
        )
        supplier_count = 0
        risk_count = 0
        if org_ids:
            supplier_count = (
                await session.execute(
                    select(func.count(SupplierModel.id)).where(
                        SupplierModel.organization_id.in_(org_ids)
                    )
                )
            ).scalar_one() or 0
            risk_count = (
                await session.execute(
                    select(func.count(RiskModel.id)).where(
                        RiskModel.organization_id.in_(org_ids)
                    )
                )
            ).scalar_one() or 0

        results.append({
            "region_id": region.id,
            "region_name": region.name,
            "region_code": region.code,
            "data_residency": region.data_residency,
            "organization_count": len(org_ids),
            "supplier_count": supplier_count,
            "risk_count": risk_count,
        })
    return results


def _score_from_rollup(rollup: dict) -> dict:
    """
    Pure deterministic health score computation from a rollup dict.

    Components:
      compliance      30%  — compliance_readiness %
      risk_posture    25%  — inverse of critical_risk_ratio
      finding_rate    20%  — inverse of open_finding_ratio
      supplier_cover  15%  — supplier_count > 0 proxy
      governance      10%  — placeholder (extended in M41+)
    """
    compliance_score = min(rollup["compliance_readiness"], 100.0)

    total_risks = max(rollup["total_risks"], 1)
    risk_posture_score = max(
        0.0, (1.0 - rollup["critical_risks"] / total_risks) * 100
    )

    total_findings = max(rollup["total_findings"], 1)
    finding_score = max(
        0.0, (1.0 - rollup["open_findings"] / total_findings) * 100
    )

    supplier_score = 100.0 if rollup["supplier_count"] > 0 else 0.0
    governance_score = 80.0  # baseline until M41 governance data available

    raw = (
        compliance_score * 0.30
        + risk_posture_score * 0.25
        + finding_score * 0.20
        + supplier_score * 0.15
        + governance_score * 0.10
    )
    score = round(raw, 1)

    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    drivers = []
    if compliance_score < 70:
        drivers.append(f"Compliance readiness is low ({compliance_score:.0f}%)")
    if risk_posture_score < 70:
        drivers.append(
            f"High proportion of critical risks ({rollup['critical_risks']}/{rollup['total_risks']})"
        )
    if finding_score < 70:
        drivers.append(
            f"High open finding rate ({rollup['open_findings']}/{rollup['total_findings']})"
        )
    if rollup["supplier_count"] == 0:
        drivers.append("No suppliers registered in this enterprise")
    if not drivers:
        drivers.append("All monitored areas within acceptable thresholds")

    return {
        "score": score,
        "grade": grade,
        "components": {
            "compliance": round(compliance_score / 100, 3),
            "risk_posture": round(risk_posture_score / 100, 3),
            "finding_rate": round(finding_score / 100, 3),
            "supplier_coverage": round(supplier_score / 100, 3),
            "governance": round(governance_score / 100, 3),
        },
        "drivers": drivers,
        "computed_at": datetime.now(UTC),
    }


async def compute_enterprise_health_score(
    enterprise_id: str, session: AsyncSession
) -> dict:
    """Deterministic ESG health score (0–100) with explainability."""
    rollup = await get_enterprise_rollup(enterprise_id, session)
    return _score_from_rollup(rollup)
