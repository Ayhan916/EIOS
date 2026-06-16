from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.assessment import Assessment
from domain.enums import ConfidenceLevel, EntityStatus
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLAssessmentRepository(BaseRepository[Assessment, AssessmentModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AssessmentModel)

    def _to_model(self, entity: Assessment) -> AssessmentModel:
        return AssessmentModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            title=entity.title,
            description=entity.description,
            assessment_type=entity.assessment_type,
            scope=entity.scope,
            methodology=entity.methodology,
            confidence=entity.confidence.value,
            sector_id=entity.sector_id,
            organization_id=entity.organization_id,
            approved_by=entity.approved_by,
            approval_date=entity.approval_date,
            quality_score=entity.quality_score,
            extraction_metadata=entity.extraction_metadata,
        )

    def _to_domain(self, model: AssessmentModel) -> Assessment:
        return Assessment(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            title=model.title,
            description=model.description,
            assessment_type=model.assessment_type,
            scope=model.scope,
            methodology=model.methodology,
            confidence=ConfidenceLevel(model.confidence),
            sector_id=model.sector_id,
            organization_id=model.organization_id,
            approved_by=model.approved_by,
            approval_date=model.approval_date,
            quality_score=model.quality_score,
            extraction_metadata=model.extraction_metadata,
        )

    async def list_by_sector(self, sector_id: str) -> list[Assessment]:
        return await self._list_by_field("sector_id", sector_id)

    async def list_by_organization(self, organization_id: str) -> list[Assessment]:
        return await self._list_by_field("organization_id", organization_id)

    async def list_org_paged(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        status: Optional[str] = None,
        assessment_type: Optional[str] = None,
        sector_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[Assessment], int]:
        stmt = (
            select(AssessmentModel)
            .where(AssessmentModel.organization_id == organization_id)
            .order_by(AssessmentModel.created_at.desc())
        )
        if status:
            stmt = stmt.where(AssessmentModel.status == status)
        if assessment_type:
            stmt = stmt.where(AssessmentModel.assessment_type == assessment_type)
        if sector_id:
            stmt = stmt.where(AssessmentModel.sector_id == sector_id)
        if search:
            stmt = stmt.where(AssessmentModel.title.ilike(f"%{search}%"))
        return await self._execute_paged(stmt, page, page_size)
