"""Product BOM Compliance Scan Service — M7.

Scans a product's Bill-of-Materials against one regulation code by querying
MaterialComplianceFlagModel entries for each BOM material.

scan_result logic:
  COMPLIANT      — all materials flagged for this regulation are COMPLIANT
  NON_COMPLIANT  — at least one material is NON_COMPLIANT
  PARTIAL        — mix of COMPLIANT and (UNKNOWN or no flag)
  UNKNOWN        — no material has any flag for this regulation
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.material import MaterialComplianceFlagModel
from infrastructure.persistence.models.product import ProductBOMItemModel
from infrastructure.persistence.models.regulatory import ProductComplianceScanModel

_SCAN_VERSION = "1.0"


class ProductComplianceScanService:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def scan_product_bom(
        self,
        organization_id: str,
        product_id: str,
        regulation_code: str,
        actor_id: str | None = None,
    ) -> ProductComplianceScanModel:
        bom_result = await self._db.execute(
            select(ProductBOMItemModel).where(
                ProductBOMItemModel.organization_id == organization_id,
                ProductBOMItemModel.product_id == product_id,
            )
        )
        bom_items = bom_result.scalars().all()
        material_ids = [item.material_id for item in bom_items]

        if not material_ids:
            return await self._write_scan(
                organization_id,
                product_id,
                regulation_code,
                total=0,
                compliant=0,
                non_compliant=0,
                unknown=0,
                flagged_ids=[],
                actor_id=actor_id,
            )

        flags_result = await self._db.execute(
            select(MaterialComplianceFlagModel).where(
                MaterialComplianceFlagModel.organization_id == organization_id,
                MaterialComplianceFlagModel.material_id.in_(material_ids),
                MaterialComplianceFlagModel.regulation == regulation_code,
            )
        )
        flags = flags_result.scalars().all()
        flag_by_material = {f.material_id: f.compliance_status for f in flags}

        compliant = 0
        non_compliant = 0
        unknown = 0
        flagged_ids: list[str] = []

        for mid in material_ids:
            status = flag_by_material.get(mid, "UNKNOWN")
            if status == "COMPLIANT":
                compliant += 1
            elif status == "NON_COMPLIANT":
                non_compliant += 1
                flagged_ids.append(mid)
            else:
                unknown += 1

        return await self._write_scan(
            organization_id,
            product_id,
            regulation_code,
            total=len(material_ids),
            compliant=compliant,
            non_compliant=non_compliant,
            unknown=unknown,
            flagged_ids=flagged_ids,
            actor_id=actor_id,
        )

    async def _write_scan(
        self,
        organization_id: str,
        product_id: str,
        regulation_code: str,
        total: int,
        compliant: int,
        non_compliant: int,
        unknown: int,
        flagged_ids: list[str],
        actor_id: str | None,
    ) -> ProductComplianceScanModel:
        if total == 0:
            result = "UNKNOWN"
        elif non_compliant > 0:
            result = "NON_COMPLIANT"
        elif compliant > 0 and unknown > 0:
            result = "PARTIAL"
        elif compliant > 0:
            result = "COMPLIANT"
        else:
            result = "UNKNOWN"

        scan = ProductComplianceScanModel(
            organization_id=organization_id,
            product_id=product_id,
            regulation_code=regulation_code,
            scan_result=result,
            total_materials=total,
            compliant_count=compliant,
            non_compliant_count=non_compliant,
            unknown_count=unknown,
            flagged_material_ids=flagged_ids,
            scan_version=_SCAN_VERSION,
            scanned_at=datetime.now(UTC),
            scanned_by=actor_id,
        )
        self._db.add(scan)
        await self._db.flush()
        return scan

    async def list_scans_for_product(
        self,
        organization_id: str,
        product_id: str,
        limit: int = 50,
    ) -> list[ProductComplianceScanModel]:
        result = await self._db.execute(
            select(ProductComplianceScanModel)
            .where(
                ProductComplianceScanModel.organization_id == organization_id,
                ProductComplianceScanModel.product_id == product_id,
            )
            .order_by(ProductComplianceScanModel.scanned_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_non_compliant_products(
        self,
        organization_id: str,
        limit: int = 100,
    ) -> list[ProductComplianceScanModel]:
        """Latest scan per product that is NON_COMPLIANT."""
        result = await self._db.execute(
            select(ProductComplianceScanModel)
            .where(
                ProductComplianceScanModel.organization_id == organization_id,
                ProductComplianceScanModel.scan_result == "NON_COMPLIANT",
            )
            .order_by(ProductComplianceScanModel.scanned_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
