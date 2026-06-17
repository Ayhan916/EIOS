import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.evidence_chunk import EvidenceChunk
from domain.user import User
from infrastructure.embeddings.chunker import chunk_text
from infrastructure.embeddings.deps import get_embedding_provider
from infrastructure.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider
from infrastructure.persistence.repositories import (
    SQLEvidenceChunkRepository,
    SQLEvidenceRepository,
)
from interfaces.api.deps import get_current_user, get_db, get_evidence_repo, require_analyst
from interfaces.api.schemas.knowledge import (
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from shared.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(get_current_user)],
)


async def get_chunk_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLEvidenceChunkRepository:
    return SQLEvidenceChunkRepository(session)


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_analyst)],
)
async def ingest_evidence(
    body: IngestRequest,
    current_user: User = Depends(get_current_user),
    evidence_repo: SQLEvidenceRepository = Depends(get_evidence_repo),
    chunk_repo: SQLEvidenceChunkRepository = Depends(get_chunk_repo),
    provider: SentenceTransformerEmbeddingProvider = Depends(get_embedding_provider),
) -> IngestResponse:
    """
    Chunk an Evidence document and store its embeddings.

    If the evidence has already been ingested, pass force=True to re-ingest
    (deletes existing chunks and recreates them).
    """
    evidence = await evidence_repo.get_by_id(body.evidence_id)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {body.evidence_id} not found",
        )

    # Tenant isolation: only ingest evidence belonging to the user's org
    if (
        evidence.organization_id
        and current_user.organization_id
        and evidence.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {body.evidence_id} not found",
        )

    existing = await chunk_repo.list_by_evidence(body.evidence_id)
    if existing and not body.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Evidence {body.evidence_id} already ingested ({len(existing)} chunks). "
            "Use force=true to re-ingest.",
        )

    if existing and body.force:
        await chunk_repo.delete_by_evidence(body.evidence_id)
        logger.info("knowledge_reingest", evidence_id=body.evidence_id, deleted=len(existing))

    text = f"{evidence.title}\n\n{evidence.description}"
    if evidence.source:
        text = f"Source: {evidence.source}\n\n{text}"

    raw_chunks = chunk_text(
        text,
        max_chars=settings.embedding_chunk_size,
        overlap_chars=settings.embedding_chunk_overlap,
    )

    if not raw_chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Evidence text is empty — nothing to ingest",
        )

    embeddings = await provider.embed_documents(raw_chunks)

    chunks = [
        EvidenceChunk(
            evidence_id=body.evidence_id,
            chunk_index=i,
            text=raw_chunks[i],
            token_count=len(raw_chunks[i].split()),
            embedding=embeddings[i],
            status=EntityStatus.ACTIVE,
        )
        for i in range(len(raw_chunks))
    ]

    await chunk_repo.save_many(chunks)

    logger.info(
        "knowledge_ingested",
        evidence_id=body.evidence_id,
        chunks=len(chunks),
        model=settings.embedding_model,
    )

    return IngestResponse(
        evidence_id=body.evidence_id,
        chunks_created=len(chunks),
        model=settings.embedding_model,
    )


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    body: SearchRequest,
    chunk_repo: SQLEvidenceChunkRepository = Depends(get_chunk_repo),
    provider: SentenceTransformerEmbeddingProvider = Depends(get_embedding_provider),
) -> SearchResponse:
    """Semantic similarity search over ingested evidence chunks."""
    query_embedding = await provider.embed_query(body.query)

    raw_results = await chunk_repo.search_similar(
        embedding=query_embedding,
        limit=body.limit,
    )

    filtered = [r for r in raw_results if r.similarity >= body.min_similarity]

    results = [
        SearchResultItem(
            chunk_id=r.chunk.id,
            evidence_id=r.chunk.evidence_id,
            evidence_title=r.evidence_title,
            evidence_source=r.evidence_source,
            text=r.chunk.text,
            similarity=round(r.similarity, 4),
            chunk_index=r.chunk.chunk_index,
        )
        for r in filtered
    ]

    logger.info(
        "knowledge_search",
        query_len=len(body.query),
        results=len(results),
        model=settings.embedding_model,
    )

    return SearchResponse(
        query=body.query,
        results=results,
        model=settings.embedding_model,
    )
