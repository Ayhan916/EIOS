import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from application.ingestion.parsers import MIME_BY_EXTENSION, resolve_mime_type
from application.ingestion.pipeline import ingest_document
from domain.evidence import Evidence
from domain.user import User
from infrastructure.embeddings.deps import get_embedding_provider
from infrastructure.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,  # concrete type for DI
)
from infrastructure.persistence.repositories import SQLEvidenceRepository
from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository
from interfaces.api.deps import (
    get_chunk_repo,
    get_current_user,
    get_evidence_repo,
    require_admin,
    require_analyst,
)
from interfaces.api.schemas.evidence import DocumentUploadResponse, EvidenceCreate, EvidenceResponse
from interfaces.api.schemas.pagination import Page, PaginationParams
from shared.config import settings

logger = structlog.get_logger(__name__)

_ALLOWED_EXTENSIONS = frozenset(MIME_BY_EXTENSION.keys()) - {".doc", ".xls"}  # only modern formats

router = APIRouter(
    prefix="/evidences",
    tags=["evidences"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_evidence(
    body: EvidenceCreate,
    current_user: User = Depends(get_current_user),
    repo: SQLEvidenceRepository = Depends(get_evidence_repo),
) -> EvidenceResponse:
    evidence = Evidence(
        title=body.title,
        source=body.source,
        description=body.description,
        evidence_type=body.evidence_type,
        confidence=body.confidence,
        url=body.url,
        language=body.language,
        published_at=body.published_at,
        reliability_score=body.reliability_score,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    saved = await repo.save(evidence)
    return EvidenceResponse.model_validate(saved)


@router.get("/", response_model=Page[EvidenceResponse])
async def list_evidences(
    pagination: PaginationParams = Depends(),
    evidence_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    search: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    repo: SQLEvidenceRepository = Depends(get_evidence_repo),
) -> Page[EvidenceResponse]:
    """List evidence records for the current user's organization, newest first."""
    if not current_user.organization_id:
        return Page(items=[], total=0, page=pagination.page, page_size=pagination.page_size)
    items, total = await repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        evidence_type=evidence_type,
        language=language,
        search=search,
    )
    return Page(
        items=[EvidenceResponse.model_validate(e) for e in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/{evidence_id}/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_analyst)],
)
async def upload_document(
    evidence_id: str,
    file: UploadFile = File(...),
    force: bool = Query(default=False, description="Re-ingest even if already ingested"),
    current_user: User = Depends(get_current_user),
    evidence_repo: SQLEvidenceRepository = Depends(get_evidence_repo),
    chunk_repo: SQLEvidenceChunkRepository = Depends(get_chunk_repo),
    embedding_provider: SentenceTransformerEmbeddingProvider = Depends(get_embedding_provider),
) -> DocumentUploadResponse:
    """
    Upload a PDF, DOCX, or XLSX file and ingest it into the knowledge pipeline.

    The document is parsed, chunked, and embedded synchronously.
    Use force=true to re-ingest an already-ingested evidence record.
    When ingestion_status is 'ocr_required', the PDF has no text layer
    and cannot be processed without OCR tooling.
    """
    evidence = await evidence_repo.get_by_id(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    if (
        evidence.organization_id
        and current_user.organization_id
        and evidence.organization_id != current_user.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    # Validate extension
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{ext}'. Allowed: .pdf, .docx, .xlsx",
        )

    # Guard against re-ingestion without force
    if evidence.ingestion_status == "ingested" and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Evidence already has {evidence.chunk_count} chunks ingested. "
                "Use force=true to re-ingest."
            ),
        )

    # Read and size-check
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB",
        )

    mime_type = resolve_mime_type(filename, file.content_type)

    logger.info(
        "document_upload_started",
        evidence_id=evidence_id,
        filename=filename,
        size_bytes=len(content),
        mime_type=mime_type,
    )

    result = await ingest_document(
        evidence=evidence,
        content=content,
        filename=filename,
        mime_type=mime_type,
        chunk_repo=chunk_repo,
        embedding_provider=embedding_provider,
        chunk_size=settings.embedding_chunk_size,
        chunk_overlap=settings.embedding_chunk_overlap,
        force=force,
    )

    # Update evidence record with file metadata and ingestion outcome
    evidence.file_name = result.file_name
    evidence.file_size_bytes = result.file_size_bytes
    evidence.file_mime_type = result.mime_type
    evidence.ingestion_status = result.ingestion_status
    evidence.chunk_count = result.chunks_created
    await evidence_repo.save(evidence)

    return DocumentUploadResponse(
        evidence_id=evidence_id,
        file_name=result.file_name,
        file_size_bytes=result.file_size_bytes,
        mime_type=result.mime_type,
        ingestion_status=result.ingestion_status,
        chunks_created=result.chunks_created,
        warnings=result.warnings,
        parser_used=result.parser_used,
    )


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLEvidenceRepository = Depends(get_evidence_repo),
) -> EvidenceResponse:
    evidence = await repo.get_by_id(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    if (
        evidence.organization_id
        and current_user.organization_id
        and evidence.organization_id != current_user.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return EvidenceResponse.model_validate(evidence)


@router.delete(
    "/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_evidence(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLEvidenceRepository = Depends(get_evidence_repo),
) -> None:
    existing = await repo.get_by_id(evidence_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    if (
        existing.organization_id
        and current_user.organization_id
        and existing.organization_id != current_user.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    await repo.delete(evidence_id)
