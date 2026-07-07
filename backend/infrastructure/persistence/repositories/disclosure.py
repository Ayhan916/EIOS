from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.disclosure import DisclosureFramework, DisclosureRequirement, DisclosureResponse
from domain.enums import EntityStatus
from domain.reporting_package import ReportingPackage
from infrastructure.persistence.models.disclosure import (
    DisclosureFrameworkModel,
    DisclosureRequirementModel,
    DisclosureResponseModel,
    ReportingPackageModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


class SQLDisclosureFrameworkRepository(
    BaseRepository[DisclosureFramework, DisclosureFrameworkModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DisclosureFrameworkModel)

    def _to_model(self, entity: DisclosureFramework) -> DisclosureFrameworkModel:
        return DisclosureFrameworkModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            code=entity.code,
            name=entity.name,
            fw_version=entity.fw_version,
            jurisdiction=entity.jurisdiction,
            effective_date=entity.effective_date,
            description=entity.description,
        )

    def _to_domain(self, model: DisclosureFrameworkModel) -> DisclosureFramework:
        return DisclosureFramework(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            code=model.code,
            name=model.name,
            fw_version=model.fw_version,
            jurisdiction=model.jurisdiction,
            effective_date=model.effective_date,
            description=model.description,
        )

    async def get_by_code(self, code: str) -> DisclosureFramework | None:
        row = (
            await self._session.execute(
                select(DisclosureFrameworkModel).where(DisclosureFrameworkModel.code == code)
            )
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_active(self) -> list[DisclosureFramework]:
        rows = (
            (
                await self._session.execute(
                    select(DisclosureFrameworkModel)
                    .where(DisclosureFrameworkModel.status == EntityStatus.ACTIVE.value)
                    .order_by(DisclosureFrameworkModel.code)
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]


class SQLDisclosureRequirementRepository(
    BaseRepository[DisclosureRequirement, DisclosureRequirementModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DisclosureRequirementModel)

    def _to_model(self, entity: DisclosureRequirement) -> DisclosureRequirementModel:
        return DisclosureRequirementModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            framework_id=entity.framework_id,
            reference=entity.reference,
            title=entity.title,
            description=entity.description,
            category=entity.category,
        )

    def _to_domain(self, model: DisclosureRequirementModel) -> DisclosureRequirement:
        return DisclosureRequirement(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            framework_id=model.framework_id,
            reference=model.reference,
            title=model.title,
            description=model.description,
            category=model.category,
        )

    async def list_for_framework(self, framework_id: str) -> list[DisclosureRequirement]:
        rows = (
            (
                await self._session.execute(
                    select(DisclosureRequirementModel)
                    .where(DisclosureRequirementModel.framework_id == framework_id)
                    .order_by(DisclosureRequirementModel.reference)
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]

    async def get_by_reference(self, reference: str) -> DisclosureRequirement | None:
        row = (
            await self._session.execute(
                select(DisclosureRequirementModel).where(
                    DisclosureRequirementModel.reference == reference
                )
            )
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None


class SQLDisclosureResponseRepository(BaseRepository[DisclosureResponse, DisclosureResponseModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DisclosureResponseModel)

    def _to_model(self, entity: DisclosureResponse) -> DisclosureResponseModel:
        return DisclosureResponseModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            requirement_id=entity.requirement_id,
            disclosure_status=entity.disclosure_status,
            narrative_text=entity.narrative_text,
            evidence_coverage=entity.evidence_coverage,
            coverage_category=entity.coverage_category,
            coverage_rationale=entity.coverage_rationale,
            readiness_status=entity.readiness_status,
            readiness_rationale=entity.readiness_rationale,
            reviewed_by=entity.reviewed_by,
            approved_by=entity.approved_by,
            published_at=entity.published_at,
        )

    def _to_domain(self, model: DisclosureResponseModel) -> DisclosureResponse:
        return DisclosureResponse(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            requirement_id=model.requirement_id,
            disclosure_status=model.disclosure_status,
            narrative_text=model.narrative_text or "",
            evidence_coverage=model.evidence_coverage or 0.0,
            coverage_category=model.coverage_category or "Weak",
            coverage_rationale=list(model.coverage_rationale or []),
            readiness_status=model.readiness_status or "Not Started",
            readiness_rationale=model.readiness_rationale or "",
            reviewed_by=model.reviewed_by,
            approved_by=model.approved_by,
            published_at=model.published_at,
        )

    async def get_for_requirement(
        self, organization_id: str, requirement_id: str
    ) -> DisclosureResponse | None:
        row = (
            await self._session.execute(
                select(DisclosureResponseModel).where(
                    DisclosureResponseModel.organization_id == organization_id,
                    DisclosureResponseModel.requirement_id == requirement_id,
                )
            )
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_for_org(
        self,
        organization_id: str,
        framework_id: str | None = None,
        disclosure_status: str | None = None,
        readiness_status: str | None = None,
        limit: int = 200,
    ) -> list[DisclosureResponse]:
        stmt = select(DisclosureResponseModel).where(
            DisclosureResponseModel.organization_id == organization_id
        )
        if disclosure_status:
            stmt = stmt.where(DisclosureResponseModel.disclosure_status == disclosure_status)
        if readiness_status:
            stmt = stmt.where(DisclosureResponseModel.readiness_status == readiness_status)
        if framework_id:
            stmt = stmt.join(
                DisclosureRequirementModel,
                DisclosureResponseModel.requirement_id == DisclosureRequirementModel.id,
            ).where(DisclosureRequirementModel.framework_id == framework_id)
        stmt = stmt.order_by(DisclosureResponseModel.updated_at.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def count_by_status(self, organization_id: str) -> dict[str, int]:
        from sqlalchemy import func  # noqa: PLC0415

        rows = (
            await self._session.execute(
                select(
                    DisclosureResponseModel.disclosure_status,
                    func.count(DisclosureResponseModel.id),
                )
                .where(DisclosureResponseModel.organization_id == organization_id)
                .group_by(DisclosureResponseModel.disclosure_status)
            )
        ).all()
        return {status: count for status, count in rows}


class SQLReportingPackageRepository(BaseRepository[ReportingPackage, ReportingPackageModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReportingPackageModel)

    def _to_model(self, entity: ReportingPackage) -> ReportingPackageModel:
        return ReportingPackageModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            framework_id=entity.framework_id,
            framework_code=entity.framework_code,
            framework_version=entity.framework_version,
            package_type=entity.package_type,
            publication_date=entity.publication_date,
            published_by=entity.published_by,
            report_data=entity.report_data,
            report_hash=entity.report_hash,
        )

    def _to_domain(self, model: ReportingPackageModel) -> ReportingPackage:
        return ReportingPackage(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            framework_id=model.framework_id,
            framework_code=model.framework_code,
            framework_version=model.framework_version,
            package_type=model.package_type,
            publication_date=model.publication_date,
            published_by=model.published_by,
            report_data=dict(model.report_data or {}),
            report_hash=model.report_hash,
        )

    async def list_for_org(
        self,
        organization_id: str,
        framework_code: str | None = None,
        limit: int = 50,
    ) -> list[ReportingPackage]:
        stmt = select(ReportingPackageModel).where(
            ReportingPackageModel.organization_id == organization_id
        )
        if framework_code:
            stmt = stmt.where(ReportingPackageModel.framework_code == framework_code)
        stmt = stmt.order_by(ReportingPackageModel.publication_date.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]
