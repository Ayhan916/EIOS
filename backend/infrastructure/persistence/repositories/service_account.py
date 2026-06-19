from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.service_account import ServiceAccount
from infrastructure.persistence.models.service_account import ServiceAccountModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLServiceAccountRepository(BaseRepository[ServiceAccount, ServiceAccountModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ServiceAccountModel)

    def _to_model(self, entity: ServiceAccount) -> ServiceAccountModel:
        return ServiceAccountModel(
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
            description=entity.description,
            is_active=entity.is_active,
        )

    def _to_domain(self, model: ServiceAccountModel) -> ServiceAccount:
        return ServiceAccount(
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
            description=model.description,
            is_active=model.is_active,
        )

    async def list_for_org(self, organization_id: str) -> list[ServiceAccount]:
        rows = (
            await self._session.execute(
                select(ServiceAccountModel)
                .where(ServiceAccountModel.organization_id == organization_id)
                .order_by(ServiceAccountModel.created_at.desc())
            )
        ).scalars().all()
        return [self._to_domain(r) for r in rows]
