"""
Ingestion pipeline — orchestrates parse → chunk → embed → store (M15).

Traceability chain:
  Evidence (org-scoped, file metadata)
    → ParsedPage (page_number, source_section)
      → EvidenceChunk (chunk_index, page_number, source_section, text, embedding)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from application.ingestion.parsers import ParseResult, parse_document
from application.ports.embeddings import EmbeddingProvider
from domain.enums import EntityStatus
from domain.evidence import Evidence
from domain.evidence_chunk import EvidenceChunk
from infrastructure.embeddings.chunker import chunk_text
from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository

logger = structlog.get_logger(__name__)

# Maximum character length per chunk passed to the embedder.
# Must align with settings.embedding_chunk_size but is taken as an arg
# so callers can override without touching global config.
_DEFAULT_CHUNK_SIZE = 512
_DEFAULT_CHUNK_OVERLAP = 50


@dataclass
class IngestionResult:
    evidence_id: str
    chunks_created: int
    file_name: str
    file_size_bytes: int
    mime_type: str
    ingestion_status: str  # "ingested" | "failed" | "ocr_required"
    warnings: list[str] = field(default_factory=list)
    parser_used: str = ""
    file_type: str = ""


async def ingest_document(
    *,
    evidence: Evidence,
    content: bytes,
    filename: str,
    mime_type: str,
    chunk_repo: SQLEvidenceChunkRepository,
    embedding_provider: EmbeddingProvider,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
    force: bool = False,
) -> IngestionResult:
    """
    Full document ingestion pipeline.

    1. Parse binary content → structured pages with traceability metadata
    2. Detect empty extraction (scanned PDF) → return ocr_required status
    3. Chunk each page independently, carrying page_number and source_section
    4. Embed all chunks in one batch call
    5. Delete existing chunks (if force=True) then persist new ones

    Returns IngestionResult regardless of outcome; never raises.
    Callers should check ingestion_status to determine success.
    """
    file_size = len(content)
    warnings: list[str] = []

    # --- Phase 1: Parse ---
    try:
        parse_result: ParseResult = parse_document(content, mime_type, filename)
    except Exception as exc:
        logger.error("ingestion_parse_error", evidence_id=evidence.id, error=str(exc))
        return IngestionResult(
            evidence_id=evidence.id,
            chunks_created=0,
            file_name=filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            ingestion_status="failed",
            warnings=[f"Unexpected parser error: {exc}"],
        )

    warnings.extend(parse_result.warnings)

    if parse_result.requires_ocr:
        logger.warning("ingestion_ocr_required", evidence_id=evidence.id)
        return IngestionResult(
            evidence_id=evidence.id,
            chunks_created=0,
            file_name=filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            ingestion_status="ocr_required",
            warnings=warnings,
            parser_used=parse_result.parser_used,
            file_type=parse_result.file_type,
        )

    if parse_result.is_empty:
        logger.warning("ingestion_empty_document", evidence_id=evidence.id)
        return IngestionResult(
            evidence_id=evidence.id,
            chunks_created=0,
            file_name=filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            ingestion_status="failed",
            warnings=warnings + ["Document contained no extractable text"],
            parser_used=parse_result.parser_used,
            file_type=parse_result.file_type,
        )

    # --- Phase 2: Chunk (per page, preserving traceability) ---
    chunk_specs: list[
        tuple[str, int | None, str | None]
    ] = []  # (text, page_number, source_section)

    for page in parse_result.pages:
        if not page.text.strip():
            continue
        raw_chunks = chunk_text(page.text, max_chars=chunk_size, overlap_chars=chunk_overlap)
        for chunk_text_str in raw_chunks:
            chunk_specs.append((chunk_text_str, page.page_number or None, page.source_section))

    if not chunk_specs:
        return IngestionResult(
            evidence_id=evidence.id,
            chunks_created=0,
            file_name=filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            ingestion_status="failed",
            warnings=warnings + ["Chunking produced no output"],
            parser_used=parse_result.parser_used,
            file_type=parse_result.file_type,
        )

    # --- Phase 3: Embed (single batch) ---
    texts = [spec[0] for spec in chunk_specs]
    try:
        embeddings = await embedding_provider.embed_documents(texts)
    except Exception as exc:
        logger.error("ingestion_embed_error", evidence_id=evidence.id, error=str(exc))
        return IngestionResult(
            evidence_id=evidence.id,
            chunks_created=0,
            file_name=filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            ingestion_status="failed",
            warnings=warnings + [f"Embedding failed: {exc}"],
            parser_used=parse_result.parser_used,
            file_type=parse_result.file_type,
        )

    # --- Phase 4: Persist ---
    if force:
        existing = await chunk_repo.list_by_evidence(evidence.id)
        if existing:
            await chunk_repo.delete_by_evidence(evidence.id)
            logger.info(
                "ingestion_existing_chunks_deleted", evidence_id=evidence.id, count=len(existing)
            )

    chunks: list[EvidenceChunk] = []
    for i, (text, page_num, section) in enumerate(chunk_specs):
        chunks.append(
            EvidenceChunk(
                evidence_id=evidence.id,
                chunk_index=i,
                text=text,
                token_count=len(text.split()),
                embedding=embeddings[i],
                page_number=page_num,
                source_section=section,
                status=EntityStatus.ACTIVE,
            )
        )

    await chunk_repo.save_many(chunks)

    logger.info(
        "ingestion_complete",
        evidence_id=evidence.id,
        file_name=filename,
        chunks=len(chunks),
        pages=len(parse_result.pages),
        parser=parse_result.parser_used,
    )

    return IngestionResult(
        evidence_id=evidence.id,
        chunks_created=len(chunks),
        file_name=filename,
        file_size_bytes=file_size,
        mime_type=mime_type,
        ingestion_status="ingested",
        warnings=warnings,
        parser_used=parse_result.parser_used,
        file_type=parse_result.file_type,
    )
