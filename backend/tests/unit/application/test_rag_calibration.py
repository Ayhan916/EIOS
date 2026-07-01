"""Tests for RAG Calibration Pipeline (TASK-003 Phase 3)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.sector_intelligence.rag_calibration import (
    CalibrationSuggestionDTO,
    SectorRiskCalibrationPipeline,
)
from domain.enums import CalibrationStatus, CSDDDRight, ConfidenceLevel


def _make_llm(response_json: dict) -> MagicMock:
    """Create a mock LLM that returns the given JSON as content."""
    from application.ports.llm import LLMResponse

    mock = MagicMock()
    mock.complete = AsyncMock(
        return_value=LLMResponse(
            content=json.dumps(response_json),
            model="llama-3.3-70b-versatile",
            provider="groq",
            input_tokens=100,
            output_tokens=50,
            stop_reason="stop",
        )
    )
    return mock


def _make_search(chunks: list[dict] | None = None) -> AsyncMock:
    """Create a mock knowledge search returning the given chunks."""

    class FakeChunk:
        def __init__(self, text: str, title: str) -> None:
            self.text = text
            self.evidence_title = title

    fake_chunks = [
        FakeChunk(c["text"], c.get("title", "Source"))
        for c in (chunks or [])
    ]
    return AsyncMock(return_value=fake_chunks)


@pytest.fixture
def default_llm_response() -> dict:
    return {
        "probability": 7,
        "confidence": "High",
        "reasoning": "Textiles sector has well-documented forced labour risks per ILO 2024.",
        "key_sources": ["ILO 2024 Textile Sector Report"],
    }


@pytest.fixture
def pipeline(default_llm_response: dict) -> SectorRiskCalibrationPipeline:
    return SectorRiskCalibrationPipeline(
        llm=_make_llm(default_llm_response),
        knowledge_search=_make_search([
            {"text": "Forced labour in textile sector is widespread.", "title": "ILO 2024"},
        ]),
    )


class TestCalibrationPipelineOutput:
    @pytest.mark.asyncio
    async def test_returns_calibration_suggestion_dto(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert isinstance(dto, CalibrationSuggestionDTO)

    @pytest.mark.asyncio
    async def test_probability_from_llm_response(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert dto.suggested_probability == 7

    @pytest.mark.asyncio
    async def test_confidence_from_llm_response(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert dto.confidence == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_nace_and_right_preserved(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        dto = await pipeline.calibrate("29", CSDDDRight.CHILD_LABOUR)
        assert dto.nace_2digit == "29"
        assert dto.csddd_right == CSDDDRight.CHILD_LABOUR

    @pytest.mark.asyncio
    async def test_status_is_pending(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert dto.status == CalibrationStatus.PENDING

    @pytest.mark.asyncio
    async def test_sources_populated(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert len(dto.sources) > 0

    @pytest.mark.asyncio
    async def test_reasoning_populated(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert dto.reasoning
        assert len(dto.reasoning) > 5

    @pytest.mark.asyncio
    async def test_id_is_uuid_string(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        import uuid
        dto = await pipeline.calibrate("29", CSDDDRight.OCCUPATIONAL_SAFETY)
        uuid.UUID(dto.id)  # raises if not valid UUID

    @pytest.mark.asyncio
    async def test_created_at_is_set(
        self, pipeline: SectorRiskCalibrationPipeline
    ) -> None:
        dto = await pipeline.calibrate("29", CSDDDRight.CHILD_LABOUR)
        assert dto.created_at
        assert "T" in dto.created_at


class TestProbabilityClamping:
    @pytest.mark.asyncio
    async def test_probability_above_10_clamped(self) -> None:
        pipeline = SectorRiskCalibrationPipeline(
            llm=_make_llm({"probability": 15, "confidence": "High", "reasoning": "x", "key_sources": []}),
            knowledge_search=_make_search(),
        )
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert dto.suggested_probability == 10

    @pytest.mark.asyncio
    async def test_probability_below_1_clamped(self) -> None:
        pipeline = SectorRiskCalibrationPipeline(
            llm=_make_llm({"probability": -5, "confidence": "Low", "reasoning": "x", "key_sources": []}),
            knowledge_search=_make_search(),
        )
        dto = await pipeline.calibrate("62", CSDDDRight.CHILD_LABOUR)
        assert dto.suggested_probability == 1


class TestLLMFailureFallback:
    @pytest.mark.asyncio
    async def test_llm_exception_returns_fallback_suggestion(self) -> None:
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=RuntimeError("API error"))
        pipeline = SectorRiskCalibrationPipeline(
            llm=llm,
            knowledge_search=_make_search(),
        )
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert isinstance(dto, CalibrationSuggestionDTO)
        assert 1 <= dto.suggested_probability <= 10
        assert dto.status == CalibrationStatus.PENDING
        assert dto.confidence == ConfidenceLevel.LOW

    @pytest.mark.asyncio
    async def test_search_exception_still_returns_suggestion(self) -> None:
        search = AsyncMock(side_effect=RuntimeError("DB unavailable"))
        pipeline = SectorRiskCalibrationPipeline(
            llm=_make_llm({"probability": 5, "confidence": "Medium", "reasoning": "ok", "key_sources": []}),
            knowledge_search=search,
        )
        dto = await pipeline.calibrate("13", CSDDDRight.FORCED_LABOUR)
        assert isinstance(dto, CalibrationSuggestionDTO)
        assert dto.suggested_probability == 5


class TestResponseParsing:
    def test_parse_clean_json(self) -> None:
        pipeline = SectorRiskCalibrationPipeline(
            llm=MagicMock(), knowledge_search=AsyncMock()
        )
        result = pipeline._parse_response(
            '{"probability": 6, "confidence": "Medium", "reasoning": "ok", "key_sources": []}'
        )
        assert result["probability"] == 6

    def test_parse_json_with_markdown_fences(self) -> None:
        pipeline = SectorRiskCalibrationPipeline(
            llm=MagicMock(), knowledge_search=AsyncMock()
        )
        result = pipeline._parse_response(
            "```json\n{\"probability\": 8, \"confidence\": \"High\", "
            "\"reasoning\": \"test\", \"key_sources\": []}\n```"
        )
        assert result["probability"] == 8

    def test_parse_json_embedded_in_text(self) -> None:
        pipeline = SectorRiskCalibrationPipeline(
            llm=MagicMock(), knowledge_search=AsyncMock()
        )
        result = pipeline._parse_response(
            'Here is my analysis: {"probability": 4, "confidence": "Low", '
            '"reasoning": "test", "key_sources": []} Based on the above...'
        )
        assert result.get("probability") == 4

    def test_parse_invalid_returns_empty_dict(self) -> None:
        pipeline = SectorRiskCalibrationPipeline(
            llm=MagicMock(), knowledge_search=AsyncMock()
        )
        result = pipeline._parse_response("This is not JSON at all.")
        assert result == {}

    def test_parse_empty_string_returns_empty_dict(self) -> None:
        pipeline = SectorRiskCalibrationPipeline(
            llm=MagicMock(), knowledge_search=AsyncMock()
        )
        result = pipeline._parse_response("")
        assert result == {}


class TestNoRAGFallback:
    @pytest.mark.asyncio
    async def test_no_chunks_uses_parametric_knowledge(self) -> None:
        """When knowledge base is empty, LLM must still be called."""
        llm = _make_llm({"probability": 6, "confidence": "Medium", "reasoning": "ok", "key_sources": []})
        pipeline = SectorRiskCalibrationPipeline(
            llm=llm,
            knowledge_search=_make_search([]),  # empty knowledge base
        )
        dto = await pipeline.calibrate("29", CSDDDRight.FORCED_LABOUR)
        assert dto.suggested_probability == 6
        llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_sources_include_parametric_fallback_note(self) -> None:
        pipeline = SectorRiskCalibrationPipeline(
            llm=_make_llm({"probability": 4, "confidence": "Low", "reasoning": "x", "key_sources": []}),
            knowledge_search=_make_search([]),
        )
        dto = await pipeline.calibrate("29", CSDDDRight.CHILD_LABOUR)
        assert any("parametric" in s.lower() or "knowledge" in s.lower() for s in dto.sources)
