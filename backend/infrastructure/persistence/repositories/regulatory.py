from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.compliance_gap import ComplianceGap
from domain.compliance_report import ComplianceReport
from domain.enums import EntityStatus
from domain.regulation import Regulation, RegulationRequirement
from domain.requirement_mapping import RequirementMapping
from infrastructure.persistence.models.regulatory import (
    ComplianceGapModel,
    ComplianceReportModel,
    RegulationModel,
    RegulationRequirementModel,
    RequirementMappingModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


class SQLRegulationRepository(BaseRepository[Regulation, RegulationModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RegulationModel)

    def _to_model(self, entity: Regulation) -> RegulationModel:
        return RegulationModel(
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
            jurisdiction=entity.jurisdiction,
            reg_version=entity.reg_version,
            effective_date=entity.effective_date,
            reg_status=entity.reg_status,
            description=entity.description,
        )

    def _to_domain(self, model: RegulationModel) -> Regulation:
        return Regulation(
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
            jurisdiction=model.jurisdiction,
            reg_version=model.reg_version,
            effective_date=model.effective_date,
            reg_status=model.reg_status,
            description=model.description,
        )

    async def get_by_code(self, code: str) -> Regulation | None:
        row = (
            await self._session.execute(select(RegulationModel).where(RegulationModel.code == code))
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_active(self) -> list[Regulation]:
        rows = (
            (
                await self._session.execute(
                    select(RegulationModel)
                    .where(RegulationModel.reg_status == "active")
                    .order_by(RegulationModel.code)
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]


class SQLRegulationRequirementRepository(
    BaseRepository[RegulationRequirement, RegulationRequirementModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RegulationRequirementModel)

    def _to_model(self, entity: RegulationRequirement) -> RegulationRequirementModel:
        return RegulationRequirementModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            regulation_id=entity.regulation_id,
            code=entity.code,
            reference=entity.reference,
            title=entity.title,
            description=entity.description,
            category=entity.category,
            pillar=entity.pillar,
            severity=entity.severity,
            obligation_type=entity.obligation_type,
            keywords=entity.keywords,
        )

    def _to_domain(self, model: RegulationRequirementModel) -> RegulationRequirement:
        return RegulationRequirement(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            regulation_id=model.regulation_id,
            code=model.code,
            reference=model.reference,
            title=model.title,
            description=model.description,
            category=model.category,
            pillar=model.pillar,
            severity=model.severity,
            obligation_type=model.obligation_type,
            keywords=list(model.keywords or []),
        )

    async def get_by_code(self, code: str) -> RegulationRequirement | None:
        row = (
            await self._session.execute(
                select(RegulationRequirementModel).where(RegulationRequirementModel.code == code)
            )
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_for_regulation(self, regulation_id: str) -> list[RegulationRequirement]:
        rows = (
            (
                await self._session.execute(
                    select(RegulationRequirementModel)
                    .where(RegulationRequirementModel.regulation_id == regulation_id)
                    .order_by(RegulationRequirementModel.code)
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]

    async def list_all_active(self) -> list[RegulationRequirement]:
        rows = (
            (
                await self._session.execute(
                    select(RegulationRequirementModel).order_by(RegulationRequirementModel.code)
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]

    async def list_by_codes(self, codes: list[str]) -> list[RegulationRequirement]:
        if not codes:
            return []
        rows = (
            (
                await self._session.execute(
                    select(RegulationRequirementModel).where(
                        RegulationRequirementModel.code.in_(codes)
                    )
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]


class SQLRequirementMappingRepository(BaseRepository[RequirementMapping, RequirementMappingModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RequirementMappingModel)

    def _to_model(self, entity: RequirementMapping) -> RequirementMappingModel:
        return RequirementMappingModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            regulation_requirement_id=entity.regulation_requirement_id,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            confidence=entity.confidence,
            rationale=entity.rationale,
            mapping_method=entity.mapping_method,
            mapping_version=entity.mapping_version,
            regulation_version_at_mapping=entity.regulation_version_at_mapping,
            mapped_at=entity.mapped_at,
            supplier_id=entity.supplier_id,
            assessment_id=entity.assessment_id,
        )

    def _to_domain(self, model: RequirementMappingModel) -> RequirementMapping:
        return RequirementMapping(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            regulation_requirement_id=model.regulation_requirement_id,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            confidence=model.confidence,
            rationale=model.rationale,
            mapping_method=model.mapping_method,
            mapping_version=model.mapping_version,
            regulation_version_at_mapping=model.regulation_version_at_mapping or "1.0",
            mapped_at=model.mapped_at,
            supplier_id=model.supplier_id,
            assessment_id=model.assessment_id,
        )

    async def list_for_org(
        self,
        organization_id: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        requirement_id: str | None = None,
        supplier_id: str | None = None,
        assessment_id: str | None = None,
    ) -> list[RequirementMapping]:
        stmt = select(RequirementMappingModel).where(
            RequirementMappingModel.organization_id == organization_id
        )
        if entity_type:
            stmt = stmt.where(RequirementMappingModel.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(RequirementMappingModel.entity_id == entity_id)
        if requirement_id:
            stmt = stmt.where(RequirementMappingModel.regulation_requirement_id == requirement_id)
        if supplier_id:
            stmt = stmt.where(RequirementMappingModel.supplier_id == supplier_id)
        if assessment_id:
            stmt = stmt.where(RequirementMappingModel.assessment_id == assessment_id)
        stmt = stmt.order_by(RequirementMappingModel.mapped_at.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_covered_requirement_ids(self, organization_id: str) -> set[str]:
        rows = (
            (
                await self._session.execute(
                    select(RequirementMappingModel.regulation_requirement_id)
                    .where(RequirementMappingModel.organization_id == organization_id)
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
        return set(rows)

    async def exists(
        self,
        organization_id: str,
        regulation_requirement_id: str,
        entity_type: str,
        entity_id: str,
    ) -> bool:
        row = (
            await self._session.execute(
                select(RequirementMappingModel.id)
                .where(
                    RequirementMappingModel.organization_id == organization_id,
                    RequirementMappingModel.regulation_requirement_id == regulation_requirement_id,
                    RequirementMappingModel.entity_type == entity_type,
                    RequirementMappingModel.entity_id == entity_id,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return row is not None


class SQLComplianceGapRepository(BaseRepository[ComplianceGap, ComplianceGapModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ComplianceGapModel)

    def _to_model(self, entity: ComplianceGap) -> ComplianceGapModel:
        return ComplianceGapModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            regulation_requirement_id=entity.regulation_requirement_id,
            supplier_id=entity.supplier_id,
            gap_type=entity.gap_type,
            severity=entity.severity,
            description=entity.description,
            evidence_refs=entity.evidence_refs,
            source_entity_type=entity.source_entity_type,
            source_entity_id=entity.source_entity_id,
            calculated_at=entity.calculated_at,
            calculation_version=entity.calculation_version,
            regulation_version_at_calculation=entity.regulation_version_at_calculation,
            is_resolved=entity.is_resolved,
            resolved_at=entity.resolved_at,
            resolved_by=entity.resolved_by,
        )

    def _to_domain(self, model: ComplianceGapModel) -> ComplianceGap:
        return ComplianceGap(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            regulation_requirement_id=model.regulation_requirement_id,
            supplier_id=model.supplier_id,
            gap_type=model.gap_type,
            severity=model.severity,
            description=model.description,
            evidence_refs=list(model.evidence_refs or []),
            source_entity_type=model.source_entity_type,
            source_entity_id=model.source_entity_id,
            calculated_at=model.calculated_at,
            calculation_version=model.calculation_version,
            regulation_version_at_calculation=model.regulation_version_at_calculation or "1.0",
            is_resolved=model.is_resolved,
            resolved_at=model.resolved_at,
            resolved_by=model.resolved_by,
        )

    async def list_for_org(
        self,
        organization_id: str,
        supplier_id: str | None = None,
        severity: str | None = None,
        gap_type: str | None = None,
        requirement_id: str | None = None,
        include_resolved: bool = False,
        limit: int = 200,
    ) -> list[ComplianceGap]:
        stmt = select(ComplianceGapModel).where(
            ComplianceGapModel.organization_id == organization_id
        )
        if supplier_id:
            stmt = stmt.where(ComplianceGapModel.supplier_id == supplier_id)
        if severity:
            stmt = stmt.where(ComplianceGapModel.severity == severity)
        if gap_type:
            stmt = stmt.where(ComplianceGapModel.gap_type == gap_type)
        if requirement_id:
            stmt = stmt.where(ComplianceGapModel.regulation_requirement_id == requirement_id)
        if not include_resolved:
            stmt = stmt.where(ComplianceGapModel.is_resolved.is_(False))
        stmt = stmt.order_by(ComplianceGapModel.calculated_at.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def delete_unresolved_for_org(self, organization_id: str) -> int:
        """Remove open (unresolved) gaps before a recalculation run."""
        from sqlalchemy import delete  # noqa: PLC0415

        result = await self._session.execute(
            delete(ComplianceGapModel).where(
                ComplianceGapModel.organization_id == organization_id,
                ComplianceGapModel.is_resolved.is_(False),
            )
        )
        return result.rowcount


class SQLComplianceReportRepository(BaseRepository[ComplianceReport, ComplianceReportModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ComplianceReportModel)

    def _to_model(self, entity: ComplianceReport) -> ComplianceReportModel:
        return ComplianceReportModel(
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
            framework_code=entity.framework_code,
            framework_version=entity.framework_version,
            generated_at=entity.generated_at,
            generated_by=entity.generated_by,
            report_data=entity.report_data,
            report_hash=entity.report_hash,
        )

    def _to_domain(self, model: ComplianceReportModel) -> ComplianceReport:
        return ComplianceReport(
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
            framework_code=model.framework_code,
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
        limit: int = 50,
    ) -> list[ComplianceReport]:
        stmt = select(ComplianceReportModel).where(
            ComplianceReportModel.organization_id == organization_id
        )
        if report_type:
            stmt = stmt.where(ComplianceReportModel.report_type == report_type)
        stmt = stmt.order_by(ComplianceReportModel.generated_at.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]
