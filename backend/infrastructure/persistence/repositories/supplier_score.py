from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus, RiskBand, TrendDirection
from domain.supplier_score import SupplierScore
from infrastructure.persistence.models.supplier_score import SupplierScoreModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLSupplierScoreRepository(BaseRepository[SupplierScore, SupplierScoreModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SupplierScoreModel)

    def _to_model(self, entity: SupplierScore) -> SupplierScoreModel:
        return SupplierScoreModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            supplier_id=entity.supplier_id,
            organization_id=entity.organization_id,
            score_version=entity.score_version,
            esg_score=entity.esg_score,
            environmental_score=entity.environmental_score,
            social_score=entity.social_score,
            governance_score=entity.governance_score,
            risk_score=entity.risk_score,
            risk_band=entity.risk_band.value,
            trend=entity.trend.value,
            trend_delta=entity.trend_delta,
            sector_percentile=entity.sector_percentile,
            inputs=entity.inputs,
            drivers=entity.drivers,
        )

    def _to_domain(self, model: SupplierScoreModel) -> SupplierScore:
        return SupplierScore(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            supplier_id=model.supplier_id,
            organization_id=model.organization_id,
            score_version=model.score_version,
            esg_score=model.esg_score,
            environmental_score=model.environmental_score,
            social_score=model.social_score,
            governance_score=model.governance_score,
            risk_score=model.risk_score,
            risk_band=RiskBand(model.risk_band),
            trend=TrendDirection(model.trend),
            trend_delta=model.trend_delta,
            sector_percentile=model.sector_percentile,
            inputs=model.inputs,
            drivers=model.drivers,
        )

    async def get_latest_for_supplier(self, supplier_id: str) -> SupplierScore | None:
        stmt = (
            select(SupplierScoreModel)
            .where(SupplierScoreModel.supplier_id == supplier_id)
            .order_by(SupplierScoreModel.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_history_for_supplier(
        self, supplier_id: str, limit: int = 12
    ) -> list[SupplierScore]:
        stmt = (
            select(SupplierScoreModel)
            .where(SupplierScoreModel.supplier_id == supplier_id)
            .order_by(SupplierScoreModel.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_latest_for_org(self, organization_id: str) -> list[SupplierScore]:
        """
        Return the most recent score snapshot for every supplier in the org.

        Uses a derived table (MAX per supplier) to avoid a window function,
        which keeps the query portable across PostgreSQL versions.
        """
        latest_subq = (
            select(
                SupplierScoreModel.supplier_id,
                func.max(SupplierScoreModel.created_at).label("max_created"),
            )
            .where(SupplierScoreModel.organization_id == organization_id)
            .group_by(SupplierScoreModel.supplier_id)
            .subquery()
        )
        stmt = select(SupplierScoreModel).join(
            latest_subq,
            and_(
                SupplierScoreModel.supplier_id == latest_subq.c.supplier_id,
                SupplierScoreModel.created_at == latest_subq.c.max_created,
            ),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]
