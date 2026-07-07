from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.due_diligence_report import DueDiligenceReport
from domain.enums import EntityStatus
from infrastructure.persistence.models.due_diligence import DueDiligenceReportModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLDueDiligenceReportRepository(BaseRepository[DueDiligenceReport, DueDiligenceReportModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DueDiligenceReportModel)

    def _to_model(self, entity: DueDiligenceReport) -> DueDiligenceReportModel:
        return DueDiligenceReportModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            report_type=entity.report_type,
            framework=entity.framework,
            framework_version=entity.framework_version,
            generated_at=entity.generated_at,
            generated_by=entity.generated_by,
            report_data=entity.report_data,
            report_hash=entity.report_hash,
        )

    def _to_domain(self, model: DueDiligenceReportModel) -> DueDiligenceReport:
        return DueDiligenceReport(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            report_type=model.report_type,
            framework=model.framework,
            framework_version=model.framework_version,
            generated_at=model.generated_at,
            generated_by=model.generated_by,
            report_data=dict(model.report_data or {}),
            report_hash=model.report_hash,
        )

    async def list_for_org(
        self,
        organization_id: str,
        report_type: str | None = None,
        framework: str | None = None,
        limit: int = 50,
    ) -> list[DueDiligenceReport]:
        stmt = select(DueDiligenceReportModel).where(
            DueDiligenceReportModel.organization_id == organization_id
        )
        if report_type:
            stmt = stmt.where(DueDiligenceReportModel.report_type == report_type)
        if framework:
            stmt = stmt.where(DueDiligenceReportModel.framework == framework)
        stmt = stmt.order_by(DueDiligenceReportModel.generated_at.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]
