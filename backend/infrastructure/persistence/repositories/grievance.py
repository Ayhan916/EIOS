"""Repository for GrievanceReport — LkSG §8 / CSDDD Art. 14."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.supplier_portal import GrievanceReport
from infrastructure.persistence.models.supplier_portal import GrievanceReportModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLGrievanceRepository(BaseRepository[GrievanceReport, GrievanceReportModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GrievanceReportModel)

    def _to_model(self, entity: GrievanceReport) -> GrievanceReportModel:
        return GrievanceReportModel(
            id=entity.id,
            organization_id=entity.organization_id,
            category=entity.category,
            grievance_status=entity.grievance_status,
            title=entity.title,
            description=entity.description,
            submitted_by_email=entity.submitted_by_email,
            submitted_by_name=entity.submitted_by_name,
            is_anonymous=entity.is_anonymous,
            anonymized_reference_code=entity.anonymized_reference_code,
            related_supplier_id=entity.related_supplier_id,
            assigned_to_user_id=entity.assigned_to_user_id,
            reviewer_notes=entity.reviewer_notes,
            resolution_notes=entity.resolution_notes,
            resolved_at=entity.resolved_at,
            regulation_refs=entity.regulation_refs,
            linked_finding_id=entity.linked_finding_id,
            status=entity.status,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )

    def _to_domain(self, model: GrievanceReportModel) -> GrievanceReport:
        return GrievanceReport(
            id=model.id,
            organization_id=model.organization_id,
            category=model.category,
            grievance_status=model.grievance_status,
            title=model.title,
            description=model.description,
            submitted_by_email=model.submitted_by_email,
            submitted_by_name=model.submitted_by_name,
            is_anonymous=model.is_anonymous,
            anonymized_reference_code=model.anonymized_reference_code,
            related_supplier_id=model.related_supplier_id,
            assigned_to_user_id=model.assigned_to_user_id,
            reviewer_notes=model.reviewer_notes,
            resolution_notes=model.resolution_notes,
            resolved_at=model.resolved_at,
            regulation_refs=model.regulation_refs,
            linked_finding_id=model.linked_finding_id,
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
        status_filter: str | None = None,
        category_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GrievanceReport]:
        stmt = select(GrievanceReportModel).where(
            GrievanceReportModel.organization_id == organization_id
        )
        if status_filter:
            stmt = stmt.where(GrievanceReportModel.grievance_status == status_filter)
        if category_filter:
            stmt = stmt.where(GrievanceReportModel.category == category_filter)
        stmt = stmt.order_by(GrievanceReportModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def get_by_reference_code(self, reference_code: str) -> GrievanceReport | None:
        stmt = select(GrievanceReportModel).where(
            GrievanceReportModel.anonymized_reference_code == reference_code
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def count_by_org(self, organization_id: str) -> dict[str, int]:
        """Return counts grouped by status for summary reporting."""
        from sqlalchemy import func

        stmt = (
            select(GrievanceReportModel.grievance_status, func.count().label("n"))
            .where(GrievanceReportModel.organization_id == organization_id)
            .group_by(GrievanceReportModel.grievance_status)
        )
        result = await self._session.execute(stmt)
        return {row.grievance_status: row.n for row in result.all()}
