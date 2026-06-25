"""Document ingestion Celery task (M45.2).

Flow when S3 is enabled:
  1. FastAPI upload endpoint stores file to S3, dispatches this task, returns 202.
  2. This task downloads the file from S3, runs the embedding pipeline,
     updates the evidence record in the database.
  3. Client polls GET /evidences/{id}/ingestion-status until status != "processing".

Asyncio compatibility:
  This task runs asyncio.run() internally because Celery workers use --pool=solo,
  giving a single-threaded event loop per worker process.  No sync wrappers needed.
"""

from __future__ import annotations

import asyncio
import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="eios.tasks.ingest_evidence",
    max_retries=3,
    default_retry_delay=30,
)
def ingest_evidence_task(
    self,
    evidence_id: str,
    s3_key: str,
    filename: str,
    mime_type: str,
) -> dict[str, object]:
    """Download file from S3 and run the embedding ingestion pipeline.

    Returns a dict serialisable to JSON — stored in the Celery result backend
    and surfaced via GET /evidences/{id}/ingestion-status.
    """
    try:
        return asyncio.run(_run_ingestion(evidence_id, s3_key, filename, mime_type))
    except Exception as exc:
        logger.error(
            "ingestion_task_failed",
            evidence_id=evidence_id,
            s3_key=s3_key,
            error=str(exc),
        )
        raise self.retry(exc=exc) from exc


async def _run_ingestion(
    evidence_id: str,
    s3_key: str,
    filename: str,
    mime_type: str,
) -> dict[str, object]:
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.repositories.evidence import SQLEvidenceRepository  # noqa: PLC0415
    from infrastructure.persistence.repositories.evidence_chunk import (  # noqa: PLC0415
        SQLEvidenceChunkRepository,
    )
    from infrastructure.embeddings.deps import get_embedding_provider  # noqa: PLC0415
    from infrastructure.storage.s3 import download_file  # noqa: PLC0415
    from application.ingestion.pipeline import ingest_document  # noqa: PLC0415
    from shared.config import settings  # noqa: PLC0415

    # Download file bytes from S3
    content = await download_file(s3_key)

    # Run ingestion pipeline
    async with AsyncSessionFactory() as session, session.begin():
        evidence_repo = SQLEvidenceRepository(session)
        chunk_repo = SQLEvidenceChunkRepository(session)
        embedding_provider = get_embedding_provider()

        evidence = await evidence_repo.get_by_id(evidence_id)
        if evidence is None:
            logger.warning("ingestion_evidence_not_found", evidence_id=evidence_id)
            return {"status": "failed", "error": "Evidence record not found"}

        result = await ingest_document(
            evidence=evidence,
            content=content,
            filename=filename,
            mime_type=mime_type,
            chunk_repo=chunk_repo,
            embedding_provider=embedding_provider,
            chunk_size=settings.embedding_chunk_size,
            chunk_overlap=settings.embedding_chunk_overlap,
            force=True,
        )

        evidence.file_name = result.file_name
        evidence.file_size_bytes = result.file_size_bytes
        evidence.file_mime_type = result.mime_type
        evidence.ingestion_status = result.ingestion_status
        evidence.chunk_count = result.chunks_created
        await evidence_repo.save(evidence)

        logger.info(
            "ingestion_task_complete",
            evidence_id=evidence_id,
            status=result.ingestion_status,
            chunks=result.chunks_created,
        )

        return {
            "evidence_id": evidence_id,
            "ingestion_status": result.ingestion_status,
            "chunks_created": result.chunks_created,
            "file_name": result.file_name,
            "warnings": result.warnings,
            "parser_used": result.parser_used,
        }
