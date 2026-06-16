from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.evidence_chunk import EvidenceChunk
from infrastructure.persistence.models.evidence import EvidenceModel
from infrastructure.persistence.models.evidence_chunk import EvidenceChunkModel
from infrastructure.persistence.repositories.base import BaseRepository


@dataclass
class ChunkSearchResult:
    chunk: EvidenceChunk
    evidence_title: str
    evidence_source: str
    similarity: float


class SQLEvidenceChunkRepository(BaseRepository[EvidenceChunk, EvidenceChunkModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EvidenceChunkModel)

    def _to_model(self, entity: EvidenceChunk) -> EvidenceChunkModel:
        model = EvidenceChunkModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            evidence_id=entity.evidence_id,
            chunk_index=entity.chunk_index,
            text=entity.text,
            token_count=entity.token_count,
            page_number=entity.page_number,
            source_section=entity.source_section,
        )
        if entity.embedding is not None:
            model.embedding = entity.embedding
        return model

    def _to_domain(self, model: EvidenceChunkModel) -> EvidenceChunk:
        embedding: list[float] | None = None
        if model.embedding is not None:
            embedding = list(model.embedding)
        return EvidenceChunk(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            evidence_id=model.evidence_id,
            chunk_index=model.chunk_index,
            text=model.text,
            token_count=model.token_count,
            embedding=embedding,
            page_number=model.page_number,
            source_section=model.source_section,
        )

    async def save_many(self, chunks: list[EvidenceChunk]) -> list[EvidenceChunk]:
        saved = []
        for chunk in chunks:
            result = await self.save(chunk)
            saved.append(result)
        return saved

    async def list_by_evidence(self, evidence_id: str) -> list[EvidenceChunk]:
        return await self._list_by_field("evidence_id", evidence_id)

    async def delete_by_evidence(self, evidence_id: str) -> None:
        stmt = delete(EvidenceChunkModel).where(
            EvidenceChunkModel.evidence_id == evidence_id
        )
        await self._session.execute(stmt)

    async def search_similar(
        self,
        embedding: list[float],
        limit: int = 10,
    ) -> list[ChunkSearchResult]:
        """
        Cosine similarity search over all embedded chunks.
        Returns chunks ordered by descending similarity (ascending cosine distance).
        """
        distance_col = EvidenceChunkModel.embedding.cosine_distance(embedding)
        stmt = (
            select(
                EvidenceChunkModel,
                EvidenceModel.title.label("evidence_title"),
                EvidenceModel.source.label("evidence_source"),
                distance_col.label("distance"),
            )
            .join(EvidenceModel, EvidenceChunkModel.evidence_id == EvidenceModel.id)
            .where(EvidenceChunkModel.embedding.is_not(None))
            .order_by(distance_col)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        results: list[ChunkSearchResult] = []
        for row in rows:
            # cosine_distance ∈ [0, 2]; convert to similarity ∈ [-1, 1] then clamp to [0, 1]
            similarity = max(0.0, 1.0 - float(row.distance))
            results.append(
                ChunkSearchResult(
                    chunk=self._to_domain(row.EvidenceChunkModel),
                    evidence_title=row.evidence_title,
                    evidence_source=row.evidence_source,
                    similarity=similarity,
                )
            )
        return results
