from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.user import User
from infrastructure.persistence.models.user import UserModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLUserRepository(BaseRepository[User, UserModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserModel)

    def _to_model(self, entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            email=entity.email,
            display_name=entity.display_name,
            role=entity.role,
            organization_id=entity.organization_id,
            is_active=entity.is_active,
            last_login_at=entity.last_login_at,
            password_hash=entity.password_hash,
            notification_preferences=entity.notification_preferences,
        )

    def _to_domain(self, model: UserModel) -> User:
        return User(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            email=model.email,
            display_name=model.display_name,
            role=model.role,
            organization_id=model.organization_id,
            is_active=model.is_active,
            last_login_at=model.last_login_at,
            password_hash=model.password_hash,
            notification_preferences=model.notification_preferences or {},
        )

    async def get_by_email(self, email: str) -> User | None:
        results = await self._list_by_field("email", email)
        return results[0] if results else None

    async def list_by_organization(self, organization_id: str) -> list[User]:
        return await self._list_by_field("organization_id", organization_id)
