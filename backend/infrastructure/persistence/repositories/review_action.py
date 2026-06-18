from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus, ReviewActionType
from domain.review_action import ReviewAction
from infrastructure.persistence.models.review_action import ReviewActionModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLReviewActionRepository(BaseRepository[ReviewAction, ReviewActionModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReviewActionModel)

    def _to_model(self, entity: ReviewAction) -> ReviewActionModel:
        return ReviewActionModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            assessment_id=entity.assessment_id,
            actor_id=entity.actor_id,
            actor_email=entity.actor_email,
            action_type=entity.action_type.value,
            comment=entity.comment,
        )

    def _to_domain(self, model: ReviewActionModel) -> ReviewAction:
        return ReviewAction(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            assessment_id=model.assessment_id,
            actor_id=model.actor_id,
            actor_email=model.actor_email,
            action_type=ReviewActionType(model.action_type),
            comment=model.comment,
        )

    async def list_by_assessment(self, assessment_id: str) -> list[ReviewAction]:
        stmt = (
            select(ReviewActionModel)
            .where(ReviewActionModel.assessment_id == assessment_id)
            .order_by(ReviewActionModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]
