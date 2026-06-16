from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.organization import Organization
from infrastructure.persistence.models.organization import OrganizationModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLOrganizationRepository(BaseRepository[Organization, OrganizationModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrganizationModel)

    def _to_model(self, entity: Organization) -> OrganizationModel:
        return OrganizationModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            name=entity.name,
            description=entity.description,
            organization_type=entity.organization_type,
            country=entity.country,
            industry=entity.industry,
        )

    def _to_domain(self, model: OrganizationModel) -> Organization:
        return Organization(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            name=model.name,
            description=model.description,
            organization_type=model.organization_type,
            country=model.country,
            industry=model.industry,
        )
