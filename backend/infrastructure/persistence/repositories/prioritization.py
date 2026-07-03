"""Repository for PrioritizationDecision — GAP-18 / CSDDD Art. 10."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.prioritization import PrioritizationDecision
from infrastructure.persistence.models.prioritization import PrioritizationDecisionModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLPrioritizationRepository(
    BaseRepository[PrioritizationDecision, PrioritizationDecisionModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PrioritizationDecisionModel)

    def _to_model(self, entity: PrioritizationDecision) -> PrioritizationDecisionModel:
        return PrioritizationDecisionModel(
            id=entity.id,
            organization_id=entity.organization_id,
            supplier_id=entity.supplier_id,
            supplier_name=entity.supplier_name,
            severity_weight=entity.severity_weight,
            probability_weight=entity.probability_weight,
            people_affected_weight=entity.people_affected_weight,
            priority_score=entity.priority_score,
            priority_rank=entity.priority_rank,
            resource_capacity_per_quarter=entity.resource_capacity_per_quarter,
            reasoning=entity.reasoning,
            overridden_manually=entity.overridden_manually,
            override_comment=entity.override_comment,
            decided_by_user_id=entity.decided_by_user_id,
            decided_at=entity.decided_at,
            regulation_refs=entity.regulation_refs,
            status=entity.status,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )

    def _to_domain(self, model: PrioritizationDecisionModel) -> PrioritizationDecision:
        return PrioritizationDecision(
            id=model.id,
            organization_id=model.organization_id,
            supplier_id=model.supplier_id,
            supplier_name=model.supplier_name,
            severity_weight=model.severity_weight,
            probability_weight=model.probability_weight,
            people_affected_weight=model.people_affected_weight,
            priority_score=model.priority_score,
            priority_rank=model.priority_rank,
            resource_capacity_per_quarter=model.resource_capacity_per_quarter,
            reasoning=model.reasoning,
            overridden_manually=model.overridden_manually,
            override_comment=model.override_comment,
            decided_by_user_id=model.decided_by_user_id,
            decided_at=model.decided_at,
            regulation_refs=model.regulation_refs,
            status=model.status,
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_by_org(
        self,
        organization_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PrioritizationDecision]:
        stmt = (
            select(PrioritizationDecisionModel)
            .where(PrioritizationDecisionModel.organization_id == organization_id)
            .order_by(PrioritizationDecisionModel.priority_rank.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def get_by_supplier(
        self, organization_id: str, supplier_id: str
    ) -> PrioritizationDecision | None:
        stmt = (
            select(PrioritizationDecisionModel)
            .where(
                PrioritizationDecisionModel.organization_id == organization_id,
                PrioritizationDecisionModel.supplier_id == supplier_id,
            )
            .order_by(PrioritizationDecisionModel.decided_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def delete_all_by_org(self, organization_id: str) -> None:
        """Remove all decisions for an org before recomputing a fresh ranking."""
        from sqlalchemy import delete as sa_delete

        stmt = sa_delete(PrioritizationDecisionModel).where(
            PrioritizationDecisionModel.organization_id == organization_id
        )
        await self._session.execute(stmt)
