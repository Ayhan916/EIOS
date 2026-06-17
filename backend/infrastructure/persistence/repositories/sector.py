from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.sector import Sector
from infrastructure.persistence.models.sector import SectorModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLSectorRepository(BaseRepository[Sector, SectorModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SectorModel)

    def _to_model(self, entity: Sector) -> SectorModel:
        return SectorModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            name=entity.name,
            nace_code=entity.nace_code,
            nace_description=entity.nace_description,
            risk_profile=entity.risk_profile,
            parent_sector_id=entity.parent_sector_id,
            organization_id=entity.organization_id,
        )

    def _to_domain(self, model: SectorModel) -> Sector:
        return Sector(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            name=model.name,
            nace_code=model.nace_code,
            nace_description=model.nace_description,
            risk_profile=model.risk_profile,
            parent_sector_id=model.parent_sector_id,
            organization_id=model.organization_id,
        )

    async def get_by_nace_code(self, nace_code: str) -> Sector | None:
        results = await self._list_by_field("nace_code", nace_code)
        return results[0] if results else None

    async def list_children(self, parent_id: str) -> list[Sector]:
        return await self._list_by_field("parent_sector_id", parent_id)
