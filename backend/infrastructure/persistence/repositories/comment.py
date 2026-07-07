from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.comment import Comment
from domain.enums import EntityStatus
from infrastructure.persistence.models.comment import CommentModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLCommentRepository(BaseRepository[Comment, CommentModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CommentModel)

    def _to_model(self, entity: Comment) -> CommentModel:
        return CommentModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            author_id=entity.author_id,
            content=entity.content,
            edited_at=entity.edited_at,
            deleted_at=entity.deleted_at,
            mentioned_user_ids=",".join(entity.mentioned_user_ids)
            if entity.mentioned_user_ids
            else None,
        )

    def _to_domain(self, model: CommentModel) -> Comment:
        mentioned = (
            [uid for uid in model.mentioned_user_ids.split(",") if uid]
            if model.mentioned_user_ids
            else []
        )
        return Comment(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            author_id=model.author_id,
            content=model.content,
            edited_at=model.edited_at,
            deleted_at=model.deleted_at,
            mentioned_user_ids=mentioned,
        )

    async def list_by_entity(
        self, entity_type: str, entity_id: str, include_deleted: bool = False
    ) -> list[Comment]:
        stmt = (
            select(CommentModel)
            .where(
                CommentModel.entity_type == entity_type,
                CommentModel.entity_id == entity_id,
            )
            .order_by(CommentModel.created_at.asc())
        )
        if not include_deleted:
            stmt = stmt.where(CommentModel.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def count_by_entity(self, entity_type: str, entity_id: str) -> int:
        from sqlalchemy import func

        stmt = select(func.count(CommentModel.id)).where(
            CommentModel.entity_type == entity_type,
            CommentModel.entity_id == entity_id,
            CommentModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0
