"""Repositories for RegulatoryChange and RegulatoryChangeImpact (GAP-19)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.regulatory_change import RegulatoryChange, RegulatoryChangeImpact
from infrastructure.persistence.models.regulatory_change import (
    RegulatoryChangeImpactModel,
    RegulatoryChangeModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


class SQLRegulatoryChangeRepository(BaseRepository[RegulatoryChange, RegulatoryChangeModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RegulatoryChangeModel)

    def _to_model(self, entity: RegulatoryChange) -> RegulatoryChangeModel:
        return RegulatoryChangeModel(
            id=entity.id,
            organization_id=entity.organization_id,
            framework_code=entity.framework_code,
            change_title=entity.change_title,
            change_description=entity.change_description,
            affected_article=entity.affected_article,
            effective_date=entity.effective_date,
            severity=entity.severity,
            change_status=entity.change_status,
            source_name=entity.source_name,
            source_url=entity.source_url,
            affected_sectors=entity.affected_sectors,
            affected_frameworks=entity.affected_frameworks,
            impact_summary=entity.impact_summary,
            impacted_assessment_count=entity.impacted_assessment_count,
            impacted_gap_count=entity.impacted_gap_count,
            regulation_refs=entity.regulation_refs,
            status=entity.status,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )

    def _to_domain(self, model: RegulatoryChangeModel) -> RegulatoryChange:
        return RegulatoryChange(
            id=model.id,
            organization_id=model.organization_id,
            framework_code=model.framework_code,
            change_title=model.change_title,
            change_description=model.change_description,
            affected_article=model.affected_article,
            effective_date=model.effective_date,
            severity=model.severity,
            change_status=model.change_status,
            source_name=model.source_name,
            source_url=model.source_url,
            affected_sectors=model.affected_sectors or [],
            affected_frameworks=model.affected_frameworks or [],
            impact_summary=model.impact_summary,
            impacted_assessment_count=model.impacted_assessment_count,
            impacted_gap_count=model.impacted_gap_count,
            regulation_refs=model.regulation_refs,
            status=model.status,
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_for_org(
        self,
        organization_id: str,
        *,
        status_filter: str | None = None,
        framework_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RegulatoryChange]:
        """Return global changes + org-specific changes, newest first."""
        stmt = select(RegulatoryChangeModel).where(
            (RegulatoryChangeModel.organization_id == organization_id)
            | (RegulatoryChangeModel.organization_id.is_(None))
        )
        if status_filter:
            stmt = stmt.where(RegulatoryChangeModel.change_status == status_filter)
        if framework_filter:
            stmt = stmt.where(RegulatoryChangeModel.framework_code == framework_filter)
        stmt = stmt.order_by(RegulatoryChangeModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def count_new_for_org(self, organization_id: str) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(RegulatoryChangeModel)
            .where(
                RegulatoryChangeModel.change_status == "new",
                (RegulatoryChangeModel.organization_id == organization_id)
                | (RegulatoryChangeModel.organization_id.is_(None)),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


class SQLRegulatoryChangeImpactRepository(
    BaseRepository[RegulatoryChangeImpact, RegulatoryChangeImpactModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RegulatoryChangeImpactModel)

    def _to_model(self, entity: RegulatoryChangeImpact) -> RegulatoryChangeImpactModel:
        return RegulatoryChangeImpactModel(
            id=entity.id,
            organization_id=entity.organization_id,
            change_id=entity.change_id,
            assessment_id=entity.assessment_id,
            compliance_gap_id=entity.compliance_gap_id,
            impact_type=entity.impact_type,
            re_review_required=entity.re_review_required,
            notification_sent=entity.notification_sent,
            acknowledged_by_user_id=entity.acknowledged_by_user_id,
            acknowledged_at=entity.acknowledged_at,
            status=entity.status,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )

    def _to_domain(self, model: RegulatoryChangeImpactModel) -> RegulatoryChangeImpact:
        return RegulatoryChangeImpact(
            id=model.id,
            organization_id=model.organization_id,
            change_id=model.change_id,
            assessment_id=model.assessment_id,
            compliance_gap_id=model.compliance_gap_id,
            impact_type=model.impact_type,
            re_review_required=model.re_review_required,
            notification_sent=model.notification_sent,
            acknowledged_by_user_id=model.acknowledged_by_user_id,
            acknowledged_at=model.acknowledged_at,
            status=model.status,
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_by_change(
        self, change_id: str, organization_id: str
    ) -> list[RegulatoryChangeImpact]:
        stmt = (
            select(RegulatoryChangeImpactModel)
            .where(
                RegulatoryChangeImpactModel.change_id == change_id,
                RegulatoryChangeImpactModel.organization_id == organization_id,
            )
            .order_by(RegulatoryChangeImpactModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def list_pending_re_review(self, organization_id: str) -> list[RegulatoryChangeImpact]:
        stmt = (
            select(RegulatoryChangeImpactModel)
            .where(
                RegulatoryChangeImpactModel.organization_id == organization_id,
                RegulatoryChangeImpactModel.re_review_required.is_(True),
                RegulatoryChangeImpactModel.acknowledged_at.is_(None),
            )
            .order_by(RegulatoryChangeImpactModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]
