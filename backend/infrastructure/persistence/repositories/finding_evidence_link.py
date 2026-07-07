from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.finding_evidence_link import FindingEvidenceLink
from infrastructure.persistence.models.finding_evidence_link import FindingEvidenceLinkModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLFindingEvidenceLinkRepository(
    BaseRepository[FindingEvidenceLink, FindingEvidenceLinkModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FindingEvidenceLinkModel)

    def _to_model(self, entity: FindingEvidenceLink) -> FindingEvidenceLinkModel:
        return FindingEvidenceLinkModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            finding_id=entity.finding_id,
            evidence_id=entity.evidence_id,
            evidence_chunk_id=entity.evidence_chunk_id,
            page_number=entity.page_number,
            confidence_score=entity.confidence_score,
            supporting_excerpt=entity.supporting_excerpt,
            link_method=entity.link_method,
        )

    def _to_domain(self, model: FindingEvidenceLinkModel) -> FindingEvidenceLink:
        return FindingEvidenceLink(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            finding_id=model.finding_id,
            evidence_id=model.evidence_id,
            evidence_chunk_id=model.evidence_chunk_id,
            page_number=model.page_number,
            confidence_score=float(model.confidence_score)
            if model.confidence_score is not None
            else None,
            supporting_excerpt=model.supporting_excerpt,
            link_method=model.link_method,
        )

    async def list_by_finding(self, finding_id: str) -> list[FindingEvidenceLink]:
        stmt = (
            select(FindingEvidenceLinkModel)
            .where(FindingEvidenceLinkModel.finding_id == finding_id)
            .order_by(FindingEvidenceLinkModel.confidence_score.desc().nulls_last())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def list_by_assessment_findings(
        self, finding_ids: list[str]
    ) -> list[FindingEvidenceLink]:
        if not finding_ids:
            return []
        stmt = (
            select(FindingEvidenceLinkModel)
            .where(FindingEvidenceLinkModel.finding_id.in_(finding_ids))
            .order_by(
                FindingEvidenceLinkModel.finding_id,
                FindingEvidenceLinkModel.confidence_score.desc().nulls_last(),
            )
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]
