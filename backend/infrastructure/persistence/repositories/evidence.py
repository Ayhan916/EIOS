from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import ConfidenceLevel, EntityStatus, EvidenceType
from domain.evidence import Evidence
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.evidence import EvidenceModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLEvidenceRepository(BaseRepository[Evidence, EvidenceModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EvidenceModel)

    def _to_model(self, entity: Evidence) -> EvidenceModel:
        return EvidenceModel(
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
            source=entity.source,
            description=entity.description,
            evidence_type=entity.evidence_type.value,
            confidence=entity.confidence.value,
            url=entity.url,
            language=entity.language,
            published_at=entity.published_at,
            retrieved_at=entity.retrieved_at,
            reliability_score=entity.reliability_score,
            ingestion_status=entity.ingestion_status,
            chunk_count=entity.chunk_count,
            file_name=entity.file_name,
            file_size_bytes=entity.file_size_bytes,
            file_mime_type=entity.file_mime_type,
        )

    def _to_domain(self, model: EvidenceModel) -> Evidence:
        return Evidence(
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
            source=model.source,
            description=model.description,
            evidence_type=EvidenceType(model.evidence_type),
            confidence=ConfidenceLevel(model.confidence),
            url=model.url,
            language=model.language,
            published_at=model.published_at,
            retrieved_at=model.retrieved_at,
            reliability_score=model.reliability_score,
            ingestion_status=model.ingestion_status,
            chunk_count=model.chunk_count,
            file_name=model.file_name,
            file_size_bytes=model.file_size_bytes,
            file_mime_type=model.file_mime_type,
        )

    async def list_by_organization(self, organization_id: str) -> list[Evidence]:
        return await self._list_by_field("organization_id", organization_id)

    async def list_org_paged(
        self,
        organization_id: str,
        page: int,
        page_size: int,
        evidence_type: str | None = None,
        language: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Evidence], int]:
        stmt = (
            select(EvidenceModel)
            .where(EvidenceModel.organization_id == organization_id)
            .order_by(EvidenceModel.created_at.desc())
        )
        if evidence_type:
            stmt = stmt.where(EvidenceModel.evidence_type == evidence_type)
        if language:
            stmt = stmt.where(EvidenceModel.language == language)
        if search:
            stmt = stmt.where(
                EvidenceModel.title.ilike(f"%{search}%") | EvidenceModel.source.ilike(f"%{search}%")
            )
        return await self._execute_paged(stmt, page, page_size)

    async def list_by_assessment(self, assessment_id: str) -> list[Evidence]:
        stmt = (
            select(EvidenceModel)
            .join(EvidenceModel.assessments)
            .where(AssessmentModel.id == assessment_id)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]
