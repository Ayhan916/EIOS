"""Unit tests for the M15 ingestion pipeline.

Tests cover: IngestionResult dataclass, OCR-required detection,
empty document detection, chunk-index assignment, and the
page_number / source_section traceability fields carried through
from parsers to EvidenceChunk objects.

The pipeline itself is not called end-to-end (that would require
a live embedding model and DB); instead we test the data-shaping
logic by calling the pipeline with mocked dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from application.ingestion.parsers import ParsedPage, ParseResult
from application.ingestion.pipeline import IngestionResult, ingest_document

# ---------------------------------------------------------------------------
# IngestionResult dataclass
# ---------------------------------------------------------------------------


class TestIngestionResult:
    def test_ingested_status(self) -> None:
        r = IngestionResult(
            evidence_id="ev-1",
            chunks_created=5,
            file_name="report.pdf",
            file_size_bytes=12345,
            mime_type="application/pdf",
            ingestion_status="ingested",
        )
        assert r.ingestion_status == "ingested"
        assert r.chunks_created == 5
        assert r.warnings == []

    def test_ocr_required_status(self) -> None:
        r = IngestionResult(
            evidence_id="ev-2",
            chunks_created=0,
            file_name="scan.pdf",
            file_size_bytes=2000,
            mime_type="application/pdf",
            ingestion_status="ocr_required",
            warnings=["PDF is scanned"],
        )
        assert r.ingestion_status == "ocr_required"
        assert r.chunks_created == 0

    def test_failed_status(self) -> None:
        r = IngestionResult(
            evidence_id="ev-3",
            chunks_created=0,
            file_name="bad.pdf",
            file_size_bytes=0,
            mime_type="application/pdf",
            ingestion_status="failed",
            warnings=["parser exploded"],
        )
        assert r.ingestion_status == "failed"
        assert "parser" in r.warnings[0]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(org_id: str = "org-1") -> MagicMock:
    ev = MagicMock()
    ev.id = "evidence-abc"
    ev.organization_id = org_id
    return ev


class _FakeEmbeddingProvider:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.1] * 4


class _FakeChunkRepo:
    def __init__(self) -> None:
        self.saved: list = []
        self.deleted_evidence_ids: list[str] = []

    async def list_by_evidence(self, evidence_id: str) -> list:
        return []

    async def delete_by_evidence(self, evidence_id: str) -> None:
        self.deleted_evidence_ids.append(evidence_id)

    async def save_many(self, chunks: list) -> list:
        self.saved.extend(chunks)
        return chunks


# ---------------------------------------------------------------------------
# Pipeline: OCR required
# ---------------------------------------------------------------------------


class TestPipelineOcrRequired:
    @pytest.mark.asyncio
    async def test_ocr_required_result(self) -> None:
        parse_result = ParseResult(
            pages=[ParsedPage(page_number=1, text="")],
            warnings=["PDF appears scanned"],
            requires_ocr=True,
            parser_used="pypdf+pdfminer(failed)",
            file_type="pdf",
        )

        with patch("application.ingestion.pipeline.parse_document", return_value=parse_result):
            result = await ingest_document(
                evidence=_make_evidence(),
                content=b"fake-pdf",
                filename="scan.pdf",
                mime_type="application/pdf",
                chunk_repo=_FakeChunkRepo(),
                embedding_provider=_FakeEmbeddingProvider(),
            )

        assert result.ingestion_status == "ocr_required"
        assert result.chunks_created == 0
        assert any("scanned" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Pipeline: empty document
# ---------------------------------------------------------------------------


class TestPipelineEmptyDocument:
    @pytest.mark.asyncio
    async def test_empty_text_returns_failed(self) -> None:
        parse_result = ParseResult(
            pages=[ParsedPage(page_number=1, text="")],
            warnings=[],
            requires_ocr=False,
            parser_used="pypdf",
            file_type="pdf",
        )

        with patch("application.ingestion.pipeline.parse_document", return_value=parse_result):
            result = await ingest_document(
                evidence=_make_evidence(),
                content=b"",
                filename="empty.pdf",
                mime_type="application/pdf",
                chunk_repo=_FakeChunkRepo(),
                embedding_provider=_FakeEmbeddingProvider(),
            )

        assert result.ingestion_status == "failed"
        assert result.chunks_created == 0


# ---------------------------------------------------------------------------
# Pipeline: successful ingestion with traceability
# ---------------------------------------------------------------------------


class TestPipelineSuccessfulIngestion:
    @pytest.mark.asyncio
    async def test_chunks_created(self) -> None:
        parse_result = ParseResult(
            pages=[
                ParsedPage(
                    page_number=1,
                    text="Supply chain labor rights assessment. Workers rights are fundamental.",
                ),
                ParsedPage(
                    page_number=2,
                    text="Environmental impact assessment. Carbon emissions exceeded targets.",
                    source_section="Environment",
                ),
            ],
            warnings=[],
            requires_ocr=False,
            parser_used="pypdf",
            file_type="pdf",
        )

        repo = _FakeChunkRepo()
        with patch("application.ingestion.pipeline.parse_document", return_value=parse_result):
            result = await ingest_document(
                evidence=_make_evidence(),
                content=b"fake",
                filename="esg_report.pdf",
                mime_type="application/pdf",
                chunk_repo=repo,
                embedding_provider=_FakeEmbeddingProvider(),
            )

        assert result.ingestion_status == "ingested"
        assert result.chunks_created > 0
        assert len(repo.saved) == result.chunks_created

    @pytest.mark.asyncio
    async def test_chunks_carry_page_number(self) -> None:
        parse_result = ParseResult(
            pages=[
                ParsedPage(
                    page_number=3,
                    text="This is page three content with enough text to form a chunk.",
                ),
            ],
            warnings=[],
            requires_ocr=False,
            parser_used="pypdf",
            file_type="pdf",
        )

        repo = _FakeChunkRepo()
        with patch("application.ingestion.pipeline.parse_document", return_value=parse_result):
            await ingest_document(
                evidence=_make_evidence(),
                content=b"fake",
                filename="report.pdf",
                mime_type="application/pdf",
                chunk_repo=repo,
                embedding_provider=_FakeEmbeddingProvider(),
            )

        assert all(c.page_number == 3 for c in repo.saved)

    @pytest.mark.asyncio
    async def test_chunks_carry_source_section(self) -> None:
        parse_result = ParseResult(
            pages=[
                ParsedPage(
                    page_number=1,
                    text="Governance data for board composition metrics.",
                    source_section="Governance",
                ),
            ],
            warnings=[],
            requires_ocr=False,
            parser_used="openpyxl",
            file_type="xlsx",
        )

        repo = _FakeChunkRepo()
        with patch("application.ingestion.pipeline.parse_document", return_value=parse_result):
            await ingest_document(
                evidence=_make_evidence(),
                content=b"fake",
                filename="esg_data.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                chunk_repo=repo,
                embedding_provider=_FakeEmbeddingProvider(),
            )

        assert all(c.source_section == "Governance" for c in repo.saved)

    @pytest.mark.asyncio
    async def test_chunk_indices_are_sequential(self) -> None:
        parse_result = ParseResult(
            pages=[
                ParsedPage(
                    page_number=1, text="First page with substantial content for chunking purposes."
                ),
                ParsedPage(
                    page_number=2,
                    text="Second page with different content for the knowledge pipeline.",
                ),
            ],
            warnings=[],
            requires_ocr=False,
            parser_used="pypdf",
            file_type="pdf",
        )

        repo = _FakeChunkRepo()
        with patch("application.ingestion.pipeline.parse_document", return_value=parse_result):
            await ingest_document(
                evidence=_make_evidence(),
                content=b"fake",
                filename="report.pdf",
                mime_type="application/pdf",
                chunk_repo=repo,
                embedding_provider=_FakeEmbeddingProvider(),
            )

        indices = [c.chunk_index for c in repo.saved]
        assert indices == list(range(len(repo.saved)))


# ---------------------------------------------------------------------------
# Pipeline: force re-ingestion
# ---------------------------------------------------------------------------


class TestPipelineForceReingestion:
    @pytest.mark.asyncio
    async def test_force_deletes_existing_chunks(self) -> None:
        class _RepoWithExisting(_FakeChunkRepo):
            async def list_by_evidence(self, evidence_id: str) -> list:
                return [MagicMock(), MagicMock()]  # 2 existing chunks

        parse_result = ParseResult(
            pages=[
                ParsedPage(page_number=1, text="Fresh content after re-ingestion of the document.")
            ],
            warnings=[],
            requires_ocr=False,
            parser_used="pypdf",
            file_type="pdf",
        )

        repo = _RepoWithExisting()
        with patch("application.ingestion.pipeline.parse_document", return_value=parse_result):
            await ingest_document(
                evidence=_make_evidence(),
                content=b"fake",
                filename="updated.pdf",
                mime_type="application/pdf",
                chunk_repo=repo,
                embedding_provider=_FakeEmbeddingProvider(),
                force=True,
            )

        assert "evidence-abc" in repo.deleted_evidence_ids


# ---------------------------------------------------------------------------
# Pipeline: embedding failure handled gracefully
# ---------------------------------------------------------------------------


class TestPipelineEmbeddingFailure:
    @pytest.mark.asyncio
    async def test_embedding_error_returns_failed(self) -> None:
        class _FailingEmbedder:
            async def embed_documents(self, texts: list[str]) -> list[list[float]]:
                raise RuntimeError("embedding model unavailable")

        parse_result = ParseResult(
            pages=[
                ParsedPage(
                    page_number=1, text="Valid content that would produce chunks for embedding."
                )
            ],
            warnings=[],
            requires_ocr=False,
            parser_used="pypdf",
            file_type="pdf",
        )

        with patch("application.ingestion.pipeline.parse_document", return_value=parse_result):
            result = await ingest_document(
                evidence=_make_evidence(),
                content=b"fake",
                filename="report.pdf",
                mime_type="application/pdf",
                chunk_repo=_FakeChunkRepo(),
                embedding_provider=_FailingEmbedder(),
            )

        assert result.ingestion_status == "failed"
        assert result.chunks_created == 0
        assert any("Embedding" in w for w in result.warnings)
