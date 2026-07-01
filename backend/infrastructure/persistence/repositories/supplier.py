from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus, SupplierStatus, SupplierTier
from domain.supplier import Supplier
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLSupplierRepository(BaseRepository[Supplier, SupplierModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SupplierModel)

    def _to_model(self, entity: Supplier) -> SupplierModel:
        return SupplierModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            name=entity.name,
            legal_name=entity.legal_name,
            country=entity.country,
            industry=entity.industry,
            nace_code=entity.nace_code,
            website=entity.website,
            supplier_tier=entity.supplier_tier.value,
            supplier_status=entity.supplier_status.value,
            notes=entity.notes,
        )

    def _to_domain(self, model: SupplierModel) -> Supplier:
        return Supplier(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            name=model.name,
            legal_name=model.legal_name,
            country=model.country,
            industry=model.industry,
            nace_code=model.nace_code,
            website=model.website,
            supplier_tier=SupplierTier(model.supplier_tier),
            supplier_status=SupplierStatus(model.supplier_status),
            notes=model.notes,
        )

    async def get_by_name_and_org(self, name: str, organization_id: str) -> Supplier | None:
        stmt = (
            select(SupplierModel)
            .where(
                SupplierModel.organization_id == organization_id,
                SupplierModel.name == name,
                SupplierModel.status.notin_(["Deleted", "Archived"]),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_archived_by_name_and_org(self, name: str, organization_id: str) -> Supplier | None:
        stmt = (
            select(SupplierModel)
            .where(
                SupplierModel.organization_id == organization_id,
                SupplierModel.name == name,
                SupplierModel.status == "Archived",
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_by_organization(self, organization_id: str) -> list[Supplier]:
        return await self._list_by_field("organization_id", organization_id)

    async def list_org_paged(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        status: str | None = None,
        country: str | None = None,
        industry: str | None = None,
        supplier_tier: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Supplier], int]:
        stmt = (
            select(SupplierModel)
            .where(SupplierModel.organization_id == organization_id)
            .where(SupplierModel.status.notin_(["Deleted", "Archived"]))
            .order_by(SupplierModel.name.asc())
        )
        if status:
            stmt = stmt.where(SupplierModel.supplier_status == status)
        if country:
            stmt = stmt.where(SupplierModel.country == country)
        if industry:
            stmt = stmt.where(SupplierModel.industry.ilike(f"%{industry}%"))
        if supplier_tier:
            stmt = stmt.where(SupplierModel.supplier_tier == supplier_tier)
        if search:
            stmt = stmt.where(
                SupplierModel.name.ilike(f"%{search}%")
                | SupplierModel.legal_name.ilike(f"%{search}%")
            )
        return await self._execute_paged(stmt, page, page_size)
