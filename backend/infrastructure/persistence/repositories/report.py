from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.report import Report
from infrastructure.persistence.models.report import ReportModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLReportRepository(BaseRepository[Report, ReportModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReportModel)

    def _to_model(self, entity: Report) -> ReportModel:
        return ReportModel(
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
            generated_by=entity.generated_by,
            organization_id=entity.organization_id,
            format=entity.format,
            finding_count=entity.finding_count,
            risk_count=entity.risk_count,
            recommendation_count=entity.recommendation_count,
            evidence_count=entity.evidence_count,
            content_snapshot=entity.content_snapshot,
        )

    def _to_domain(self, model: ReportModel) -> Report:
        return Report(
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
            generated_by=model.generated_by,
            organization_id=model.organization_id,
            format=model.format,
            finding_count=model.finding_count,
            risk_count=model.risk_count,
            recommendation_count=model.recommendation_count,
            evidence_count=model.evidence_count,
            content_snapshot=model.content_snapshot or {},
        )

    async def save_with_pdf(self, entity: Report, pdf_data: bytes) -> Report:
        """Persist report metadata and PDF bytes atomically."""
        model = self._to_model(entity)
        model.pdf_data = pdf_data
        merged = await self._session.merge(model)
        await self._session.flush()
        return self._to_domain(merged)

    async def get_pdf_data(self, report_id: str) -> bytes | None:
        """Return raw PDF bytes for a report, or None if not found."""
        result = await self._session.get(ReportModel, report_id)
        if result is None:
            return None
        return result.pdf_data

    async def list_by_assessment(self, assessment_id: str) -> list[Report]:
        return await self._list_by_field("assessment_id", assessment_id)

    async def list_by_organization(self, organization_id: str) -> list[Report]:
        return await self._list_by_field("organization_id", organization_id)

    async def list_assessment_paged(
        self,
        assessment_id: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Report], int]:
        stmt = (
            select(ReportModel)
            .where(ReportModel.assessment_id == assessment_id)
            .order_by(ReportModel.created_at.desc())
        )
        return await self._execute_paged(stmt, page, page_size)
