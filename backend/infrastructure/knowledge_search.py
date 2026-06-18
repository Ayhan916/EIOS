from application.ports.embeddings import EmbeddingProvider
from application.ports.knowledge import RetrievedChunkMeta
from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository


class EvidenceChunkSearchAdapter:
    """Implements KnowledgeSearchPort using the pgvector evidence chunk store.

    Returns full chunk metadata (id, evidence, page, text, score) so the
    workflow engine can record traceable evidence links after extraction.
    """

    def __init__(
        self,
        chunk_repo: SQLEvidenceChunkRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._repo = chunk_repo
        self._embeddings = embedding_provider

    async def search(self, query: str, limit: int = 10) -> list[RetrievedChunkMeta]:
        query_embedding = await self._embeddings.embed_query(query)
        results = await self._repo.search_similar(query_embedding, limit=limit)
        return [
            RetrievedChunkMeta(
                chunk_id=r.chunk.id,
                evidence_id=r.chunk.evidence_id,
                page_number=r.chunk.page_number,
                source_section=r.chunk.source_section,
                text=r.chunk.text,
                similarity_score=r.similarity,
                evidence_title=r.evidence_title,
                evidence_source=r.evidence_source,
            )
            for r in results
        ]
