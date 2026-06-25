import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

import application.audit as audit_factory
from application.ingestion.parsers import MIME_BY_EXTENSION, resolve_mime_type
from application.ingestion.pipeline import ingest_document
from domain.evidence import Evidence
from domain.user import User
from infrastructure.embeddings.deps import get_embedding_provider
from infrastructure.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,  # concrete type for DI
)
from infrastructure.persistence.repositories import SQLAuditEventRepository, SQLEvidenceRepository
from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository
from interfaces.api.deps import (
    get_audit_event_repo,
    get_chunk_repo,
    get_current_user,
    get_evidence_repo,
    require_admin,
    require_analyst,
)
from interfaces.api.schemas.evidence import (
    DocumentUploadResponse,
    EvidenceDownloadResponse,
    EvidenceCreate,
    EvidenceResponse,
    IngestionStatusResponse,
)
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
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
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
        async_path=settings.s3_enabled,
    )

    # ── Async path (S3 enabled): store → dispatch Celery task → 202 ──────────
    if settings.s3_enabled:
        import uuid as _uuid  # noqa: PLC0415
        from infrastructure.storage.s3 import upload_file  # noqa: PLC0415
        from infrastructure.celery.tasks.ingestion import ingest_evidence_task  # noqa: PLC0415

        s3_key = (
            f"{evidence.organization_id or 'global'}/evidences"
            f"/{evidence_id}/{_uuid.uuid4()}-{filename}"
        )
        await upload_file(content, s3_key, mime_type)

        task = ingest_evidence_task.delay(evidence_id, s3_key, filename, mime_type)
        task_id = str(task.id)

        evidence.file_name = filename
        evidence.file_size_bytes = len(content)
        evidence.file_mime_type = mime_type
        evidence.ingestion_status = "processing"
        evidence.s3_object_key = s3_key
        evidence.ingestion_job_id = task_id
        await evidence_repo.save(evidence)

        await audit_repo.save(
            audit_factory.evidence_uploaded(
                evidence_id=evidence_id,
                actor_id=current_user.id,
                file_name=filename,
                file_size_bytes=len(content),
                ingestion_status="processing",
                chunks_created=0,
            )
        )

        return DocumentUploadResponse(
            evidence_id=evidence_id,
            file_name=filename,
            file_size_bytes=len(content),
            mime_type=mime_type,
            ingestion_status="processing",
            chunks_created=0,
            task_id=task_id,
            s3_object_key=s3_key,
        )

    # ── Sync path (S3 disabled, default): ingest inline ──────────────────────
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

    evidence.file_name = result.file_name
    evidence.file_size_bytes = result.file_size_bytes
    evidence.file_mime_type = result.mime_type
    evidence.ingestion_status = result.ingestion_status
    evidence.chunk_count = result.chunks_created
    await evidence_repo.save(evidence)

    await audit_repo.save(
        audit_factory.evidence_uploaded(
            evidence_id=evidence_id,
            actor_id=current_user.id,
            file_name=result.file_name,
            file_size_bytes=result.file_size_bytes,
            ingestion_status=result.ingestion_status,
            chunks_created=result.chunks_created,
        )
    )

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


@router.get(
    "/{evidence_id}/ingestion-status",
    response_model=IngestionStatusResponse,
    dependencies=[Depends(require_analyst)],
)
async def get_ingestion_status(
    evidence_id: str,
    evidence_repo: SQLEvidenceRepository = Depends(get_evidence_repo),
    current_user: User = Depends(get_current_user),
) -> IngestionStatusResponse:
    """Poll the async Celery ingestion status for an evidence document (M45.2)."""
    evidence = await evidence_repo.get_by_id(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    if (
        evidence.organization_id
        and current_user.organization_id
        and evidence.organization_id != current_user.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    task_id = getattr(evidence, "ingestion_job_id", None)
    task_state = "N/A"
    task_result = None

    if task_id and settings.s3_enabled:
        from infrastructure.celery.app import celery_app  # noqa: PLC0415
        from celery.result import AsyncResult  # noqa: PLC0415
        ar = AsyncResult(task_id, app=celery_app)
        task_state = ar.state
        if ar.successful():
            task_result = ar.result

    return IngestionStatusResponse(
        evidence_id=evidence_id,
        task_id=task_id,
        task_state=task_state,
        ingestion_status=evidence.ingestion_status,
        result=task_result,
    )


@router.get(
    "/{evidence_id}/download",
    response_model=EvidenceDownloadResponse,
    dependencies=[Depends(require_analyst)],
)
async def download_evidence_file(
    evidence_id: str,
    evidence_repo: SQLEvidenceRepository = Depends(get_evidence_repo),
    current_user: User = Depends(get_current_user),
) -> EvidenceDownloadResponse:
    """Generate a presigned S3 URL to download the uploaded evidence file (M45.2).

    Only available when S3_ENABLED=true and the file has been uploaded.
    """
    if not settings.s3_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="S3 storage is not enabled (S3_ENABLED=false)",
        )

    evidence = await evidence_repo.get_by_id(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    if (
        evidence.organization_id
        and current_user.organization_id
        and evidence.organization_id != current_user.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    s3_key = getattr(evidence, "s3_object_key", None)
    if not s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No file stored for this evidence record",
        )

    from infrastructure.storage.s3 import generate_presigned_url  # noqa: PLC0415
    presigned_url = await generate_presigned_url(s3_key)

    return EvidenceDownloadResponse(
        evidence_id=evidence_id,
        file_name=evidence.file_name,
        presigned_url=presigned_url,
        expires_in_seconds=settings.s3_presigned_url_expire_seconds,
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


# ── Document version history (G-045) ─────────────────────────────────────────

@router.get("/{evidence_id}/versions", response_model=list[dict])
async def list_evidence_versions(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLEvidenceRepository = Depends(get_evidence_repo),
) -> list[dict]:
    """Return the version history for an evidence document.

    Each version corresponds to a file that was previously the current version.
    The current file is in the evidence record itself; prior versions are here.
    """
    from infrastructure.persistence.models.evidence_version import EvidenceVersionModel  # noqa: PLC0415
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    evidence = await repo.get_by_id(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    if (
        evidence.organization_id
        and current_user.organization_id
        and evidence.organization_id != current_user.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    # Access via the repo session (injected through get_evidence_repo → get_db)
    from interfaces.api.deps import get_db  # noqa: PLC0415
    stmt = (
        select(EvidenceVersionModel)
        .where(EvidenceVersionModel.evidence_id == evidence_id)
        .order_by(EvidenceVersionModel.version_number.desc())
    )
    # Reuse session from repo
    result = await repo._session.execute(stmt)
    versions = list(result.scalars().all())

    return [
        {
            "id": v.id,
            "evidence_id": v.evidence_id,
            "version_number": v.version_number,
            "file_name": v.file_name,
            "file_size_bytes": v.file_size_bytes,
            "file_mime_type": v.file_mime_type,
            "s3_key": v.s3_key,
            "ingestion_status": v.ingestion_status,
            "created_by": v.created_by,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "notes": v.notes,
        }
        for v in versions
    ]
