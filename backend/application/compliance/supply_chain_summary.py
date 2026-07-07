"""Supply Chain Compliance Summary Service — M7.

Aggregates compliance state across Material Twins → Product Twins → DPPs for
an organisation. All counts are computed from DB state at call time (no cache).

Output is a plain dict — deterministic, auditable, no LLM scoring.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.dpp import DigitalProductPassportModel
from infrastructure.persistence.models.material import (
    MaterialComplianceFlagModel,
    MaterialModel,
)
from infrastructure.persistence.models.product import ProductBOMItemModel, ProductModel
from infrastructure.persistence.models.regulatory import ProductComplianceScanModel


class SupplyChainComplianceSummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def compute_summary(self, organization_id: str) -> dict:
        material_stats = await self._material_stats(organization_id)
        product_stats = await self._product_stats(organization_id)
        dpp_stats = await self._dpp_stats(organization_id)
        top_regulations = await self._top_non_compliant_regulations(organization_id)

        return {
            "organization_id": organization_id,
            "materials": material_stats,
            "products": product_stats,
            "digital_product_passports": dpp_stats,
            "top_at_risk_regulations": top_regulations,
        }

    async def _material_stats(self, org_id: str) -> dict:
        total_res = await self._db.execute(
            select(func.count()).where(
                MaterialModel.organization_id == org_id,
                MaterialModel.material_status == "ACTIVE",
            )
        )
        total = total_res.scalar_one() or 0

        flagged_res = await self._db.execute(
            select(func.count(MaterialComplianceFlagModel.material_id.distinct())).where(
                MaterialComplianceFlagModel.organization_id == org_id,
                MaterialComplianceFlagModel.compliance_status == "NON_COMPLIANT",
            )
        )
        non_compliant = flagged_res.scalar_one() or 0

        substances_res = await self._db.execute(
            select(func.count()).where(
                ProductBOMItemModel.organization_id == org_id,
                ProductBOMItemModel.is_substance_of_concern == True,  # noqa: E712
            )
        )
        substances_of_concern = substances_res.scalar_one() or 0

        return {
            "total_active": total,
            "non_compliant": non_compliant,
            "substances_of_concern_in_bom": substances_of_concern,
        }

    async def _product_stats(self, org_id: str) -> dict:
        total_res = await self._db.execute(
            select(func.count()).where(
                ProductModel.organization_id == org_id,
                ProductModel.product_status == "ACTIVE",
            )
        )
        total = total_res.scalar_one() or 0

        non_compliant_res = await self._db.execute(
            select(func.count(ProductComplianceScanModel.product_id.distinct())).where(
                ProductComplianceScanModel.organization_id == org_id,
                ProductComplianceScanModel.scan_result == "NON_COMPLIANT",
            )
        )
        non_compliant = non_compliant_res.scalar_one() or 0

        scanned_res = await self._db.execute(
            select(func.count(ProductComplianceScanModel.product_id.distinct())).where(
                ProductComplianceScanModel.organization_id == org_id,
            )
        )
        scanned = scanned_res.scalar_one() or 0

        return {
            "total_active": total,
            "scanned": scanned,
            "non_compliant": non_compliant,
        }

    async def _dpp_stats(self, org_id: str) -> dict:
        total_res = await self._db.execute(
            select(func.count()).where(
                DigitalProductPassportModel.organization_id == org_id,
            )
        )
        total = total_res.scalar_one() or 0

        disclosed_res = await self._db.execute(
            select(func.count()).where(
                DigitalProductPassportModel.organization_id == org_id,
                DigitalProductPassportModel.disclosed_at.is_not(None),
            )
        )
        disclosed = disclosed_res.scalar_one() or 0

        non_compliant_res = await self._db.execute(
            select(func.count()).where(
                DigitalProductPassportModel.organization_id == org_id,
                DigitalProductPassportModel.non_compliant_regulations_count > 0,
            )
        )
        non_compliant_dpp = non_compliant_res.scalar_one() or 0

        return {
            "total": total,
            "disclosed": disclosed,
            "non_compliant": non_compliant_dpp,
        }

    async def _top_non_compliant_regulations(self, org_id: str, limit: int = 5) -> list[dict]:
        result = await self._db.execute(
            select(
                MaterialComplianceFlagModel.regulation,
                func.count().label("count"),
            )
            .where(
                MaterialComplianceFlagModel.organization_id == org_id,
                MaterialComplianceFlagModel.compliance_status == "NON_COMPLIANT",
            )
            .group_by(MaterialComplianceFlagModel.regulation)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [
            {"regulation_code": row.regulation, "non_compliant_materials": row.count}
            for row in result.all()
        ]
