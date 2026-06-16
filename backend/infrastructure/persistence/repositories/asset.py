from sqlalchemy.ext.asyncio import AsyncSession

from domain.asset import Asset
from domain.enums import EntityStatus
from infrastructure.persistence.models.asset import AssetModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLAssetRepository(BaseRepository[Asset, AssetModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AssetModel)

    def _to_model(self, entity: Asset) -> AssetModel:
        return AssetModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            title=entity.title,
            description=entity.description,
            asset_type=entity.asset_type,
            asset_class=entity.asset_class,
            location=entity.location,
            organization_id=entity.organization_id,
        )

    def _to_domain(self, model: AssetModel) -> Asset:
        return Asset(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            title=model.title,
            description=model.description,
            asset_type=model.asset_type,
            asset_class=model.asset_class,
            location=model.location,
            organization_id=model.organization_id,
        )

    async def list_by_organization(self, organization_id: str) -> list[Asset]:
        return await self._list_by_field("organization_id", organization_id)
