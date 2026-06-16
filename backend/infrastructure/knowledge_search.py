from application.ports.embeddings import EmbeddingProvider
from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository


class EvidenceChunkSearchAdapter:
    """Implements KnowledgeSearchPort using the pgvector evidence chunk store.

    This adapter lives in infrastructure — it wires the abstract port to the
    concrete SQLEvidenceChunkRepository and EmbeddingProvider.
    """

    def __init__(
        self,
        chunk_repo: SQLEvidenceChunkRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._repo = chunk_repo
        self._embeddings = embedding_provider

    async def search(self, query: str, limit: int = 10) -> list[str]:
        query_embedding = await self._embeddings.embed_query(query)
        results = await self._repo.search_similar(query_embedding, limit=limit)
        return [r.chunk.text for r in results]
