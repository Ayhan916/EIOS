from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.notification import Notification
from infrastructure.persistence.models.notification import NotificationModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLNotificationRepository(BaseRepository[Notification, NotificationModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, NotificationModel)

    def _to_model(self, entity: Notification) -> NotificationModel:
        return NotificationModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            user_id=entity.user_id,
            organization_id=entity.organization_id,
            notification_type=entity.notification_type,
            title=entity.title,
            body=entity.body,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            is_read=entity.is_read,
            read_at=entity.read_at,
            dedupe_key=entity.dedupe_key,
        )

    def _to_domain(self, model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            user_id=model.user_id,
            organization_id=model.organization_id,
            notification_type=model.notification_type,
            title=model.title,
            body=model.body,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            is_read=model.is_read,
            read_at=model.read_at,
            dedupe_key=model.dedupe_key,
        )

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[Notification]:
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def unread_count(self, user_id: str) -> int:
        stmt = select(NotificationModel).where(
            NotificationModel.user_id == user_id,
            NotificationModel.is_read.is_(False),
        )
        result = await self._session.execute(stmt)
        return len(result.scalars().all())

    async def mark_read(self, notification_id: str, user_id: str) -> None:
        now = datetime.now(UTC)
        await self._session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.id == notification_id,
                NotificationModel.user_id == user_id,
            )
            .values(is_read=True, read_at=now, updated_at=now)
        )
        await self._session.flush()

    async def mark_all_read(self, user_id: str) -> None:
        now = datetime.now(UTC)
        await self._session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read.is_(False),
            )
            .values(is_read=True, read_at=now, updated_at=now)
        )
        await self._session.flush()

    async def exists_by_dedupe_key(self, dedupe_key: str) -> bool:
        stmt = select(NotificationModel).where(NotificationModel.dedupe_key == dedupe_key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
