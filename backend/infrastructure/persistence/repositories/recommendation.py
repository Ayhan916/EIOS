from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import ActionStatus, ConfidenceLevel, EntityStatus, RiskLevel
from domain.recommendation import Recommendation
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLRecommendationRepository(BaseRepository[Recommendation, RecommendationModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RecommendationModel)

    def _to_model(self, entity: Recommendation) -> RecommendationModel:
        return RecommendationModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            assessment_id=entity.assessment_id,
            title=entity.title,
            description=entity.description,
            priority=entity.priority.value,
            confidence=entity.confidence.value,
            reasoning=entity.reasoning,
            action_required=entity.action_required,
            due_date=entity.due_date,
            approved_by=entity.approved_by,
            action_status=entity.action_status.value,
            assigned_to_id=entity.assigned_to_id,
        )

    def _to_domain(self, model: RecommendationModel) -> Recommendation:
        return Recommendation(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            assessment_id=model.assessment_id,
            title=model.title,
            description=model.description,
            priority=RiskLevel(model.priority),
            confidence=ConfidenceLevel(model.confidence),
            reasoning=model.reasoning,
            action_required=model.action_required,
            due_date=model.due_date,
            approved_by=model.approved_by,
            action_status=ActionStatus(model.action_status),
            assigned_to_id=model.assigned_to_id,
        )

    async def list_by_assessment(self, assessment_id: str) -> list[Recommendation]:
        return await self._list_by_field("assessment_id", assessment_id)

    async def list_overdue(self, reference_date: date) -> list[Recommendation]:
        """Return all open/in-progress recommendations with due_date < reference_date."""
        stmt = select(RecommendationModel).where(
            RecommendationModel.due_date < reference_date,
            RecommendationModel.action_status.notin_(
                [ActionStatus.RESOLVED.value, ActionStatus.VERIFIED.value]
            ),
            RecommendationModel.assigned_to_id.isnot(None),
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def list_overdue_with_assignees(
        self, reference_date: date, limit: int = 500, offset: int = 0
    ) -> list["OverdueScanRow"]:
        """
        Single JOIN query: returns overdue recs with their assignee's user data.

        Eliminates the N+1 pattern in the overdue background task — one query per
        batch instead of one query per recommendation.
        """
        from infrastructure.persistence.models.user import UserModel

        stmt = (
            select(
                RecommendationModel.id,
                RecommendationModel.title,
                RecommendationModel.due_date,
                UserModel.id.label("user_id"),
                UserModel.email.label("user_email"),
                UserModel.organization_id,
                UserModel.notification_preferences,
            )
            .join(UserModel, RecommendationModel.assigned_to_id == UserModel.id)
            .where(
                RecommendationModel.due_date < reference_date,
                RecommendationModel.action_status.notin_(
                    [ActionStatus.RESOLVED.value, ActionStatus.VERIFIED.value]
                ),
                UserModel.is_active.is_(True),
            )
            .order_by(RecommendationModel.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [
            OverdueScanRow(
                recommendation_id=row.id,
                recommendation_title=row.title,
                due_date=row.due_date,
                user_id=row.user_id,
                user_email=row.user_email,
                organization_id=row.organization_id or "",
                notification_preferences=row.notification_preferences or {},
            )
            for row in result.all()
        ]


@dataclass(frozen=True)
class OverdueScanRow:
    recommendation_id: str
    recommendation_title: str
    due_date: date | None
    user_id: str
    user_email: str
    organization_id: str
    notification_preferences: dict

    async def list_by_org_and_status(
        self, organization_id: str, action_status: ActionStatus | None = None
    ) -> list[Recommendation]:
        from infrastructure.persistence.models.assessment import AssessmentModel

        stmt = (
            select(RecommendationModel)
            .join(AssessmentModel, RecommendationModel.assessment_id == AssessmentModel.id)
            .where(AssessmentModel.organization_id == organization_id)
        )
        if action_status is not None:
            stmt = stmt.where(RecommendationModel.action_status == action_status.value)
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]
