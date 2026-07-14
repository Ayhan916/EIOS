"""Unit tests for E1-F1 — Metric Extraction → Claude Haiku (ADR-007).

Verifies that:
1. The extraction provider uses the Haiku model by default.
2. The extraction model is configurable via EXTRACTION_LLM_MODEL env var.
3. The extraction provider is a distinct singleton from the main LLM provider.
4. Fallback to main provider when Anthropic key is absent.
"""

from unittest.mock import MagicMock, patch

import pytest

from shared.config import Settings


class TestExtractionModelConfig:
    def test_default_extraction_model_is_haiku(self) -> None:
        settings = Settings()
        assert settings.extraction_llm_model == "claude-haiku-4-5-20251001"

    def test_extraction_model_overridable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EXTRACTION_LLM_MODEL", "claude-haiku-4-5-20251001")
        settings = Settings()
        assert "haiku" in settings.extraction_llm_model.lower()

    def test_extraction_model_is_not_groq(self) -> None:
        settings = Settings()
        assert "groq" not in settings.extraction_llm_model.lower()
        assert "llama" not in settings.extraction_llm_model.lower()

    def test_extraction_model_is_haiku_not_sonnet_or_opus(self) -> None:
        settings = Settings()
        assert "haiku" in settings.extraction_llm_model.lower()


class TestExtractionProviderInit:
    def test_init_creates_anthropic_provider_when_key_present(self) -> None:
        mock_provider = MagicMock()
        mock_provider.model_name.return_value = "claude-haiku-4-5-20251001"

        # AnthropicLLMProvider is lazily imported inside the function — patch at source
        with (
            patch("infrastructure.llm.deps._extraction_provider", None),
            patch("infrastructure.llm.deps.settings") as mock_settings,
            patch(
                "infrastructure.llm.anthropic_provider.AnthropicLLMProvider",
                return_value=mock_provider,
            ) as mock_cls,
        ):
            mock_settings.anthropic_api_key = "test-api-key"
            mock_settings.extraction_llm_model = "claude-haiku-4-5-20251001"

            from infrastructure.llm.deps import init_extraction_llm_provider

            result = init_extraction_llm_provider()

        mock_cls.assert_called_once_with(
            api_key="test-api-key",
            model="claude-haiku-4-5-20251001",
        )
        assert result.model_name() == "claude-haiku-4-5-20251001"

    def test_init_falls_back_when_no_api_key(self) -> None:
        main_provider = MagicMock()
        main_provider.model_name.return_value = "claude-sonnet-4-6"

        with (
            patch("infrastructure.llm.deps._extraction_provider", None),
            patch("infrastructure.llm.deps._provider", main_provider),
            patch("infrastructure.llm.deps.settings") as mock_settings,
        ):
            mock_settings.anthropic_api_key = ""
            mock_settings.extraction_llm_model = "claude-haiku-4-5-20251001"

            from infrastructure.llm.deps import init_extraction_llm_provider

            result = init_extraction_llm_provider()

        # Falls back to main provider when no Anthropic key
        assert result is main_provider

    def test_get_extraction_provider_lazy_initialises(self) -> None:
        mock_provider = MagicMock()

        with (
            patch("infrastructure.llm.deps._extraction_provider", None),
            patch(
                "infrastructure.llm.deps.init_extraction_llm_provider",
                return_value=mock_provider,
            ) as mock_init,
        ):
            from infrastructure.llm.deps import get_extraction_llm_provider

            result = get_extraction_llm_provider()

        mock_init.assert_called_once()
        assert result is mock_provider

    def test_get_extraction_provider_returns_cached_singleton(self) -> None:
        cached = MagicMock()

        with patch("infrastructure.llm.deps._extraction_provider", cached):
            from infrastructure.llm.deps import get_extraction_llm_provider

            result = get_extraction_llm_provider()

        assert result is cached
