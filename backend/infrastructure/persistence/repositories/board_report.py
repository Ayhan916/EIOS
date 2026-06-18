from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.board_report import BoardReport, ReportSchedule
from domain.enums import EntityStatus
from infrastructure.persistence.models.board_report import (
    BoardReportModel,
    ReportScheduleModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


class SQLBoardReportRepository(BaseRepository[BoardReport, BoardReportModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BoardReportModel)

    def _to_model(self, entity: BoardReport) -> BoardReportModel:
        return BoardReportModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            title=entity.title,
            report_version=entity.report_version,
            period_start=entity.period_start,
            period_end=entity.period_end,
            executive_summary=entity.executive_summary,
            report_data=entity.report_data,
            supplier_snapshot=entity.supplier_snapshot,
        )

    def _to_domain(self, model: BoardReportModel) -> BoardReport:
        return BoardReport(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            title=model.title,
            report_version=model.report_version,
            period_start=model.period_start,
            period_end=model.period_end,
            executive_summary=model.executive_summary,
            report_data=model.report_data,
            supplier_snapshot=model.supplier_snapshot,
        )

    async def list_for_org(
        self, organization_id: str, limit: int = 20
    ) -> list[BoardReport]:
        stmt = (
            select(BoardReportModel)
            .where(
                BoardReportModel.organization_id == organization_id,
                BoardReportModel.status != EntityStatus.DELETED.value,
            )
            .order_by(BoardReportModel.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]


class SQLReportScheduleRepository(BaseRepository[ReportSchedule, ReportScheduleModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReportScheduleModel)

    def _to_model(self, entity: ReportSchedule) -> ReportScheduleModel:
        return ReportScheduleModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            frequency=entity.frequency,
            next_run_at=entity.next_run_at,
            last_run_at=entity.last_run_at,
            report_config=entity.report_config,
            is_active=entity.is_active,
        )

    def _to_domain(self, model: ReportScheduleModel) -> ReportSchedule:
        return ReportSchedule(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            frequency=model.frequency,
            next_run_at=model.next_run_at,
            last_run_at=model.last_run_at,
            report_config=model.report_config,
            is_active=model.is_active,
        )

    async def list_for_org(self, organization_id: str) -> list[ReportSchedule]:
        stmt = (
            select(ReportScheduleModel)
            .where(
                ReportScheduleModel.organization_id == organization_id,
                ReportScheduleModel.status != EntityStatus.DELETED.value,
            )
            .order_by(ReportScheduleModel.created_at.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]
