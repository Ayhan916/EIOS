"""Unit tests for M20 Settings and production config validation."""

import pytest

from shared.config import _INSECURE_SECRET_KEY, Settings


class TestProductionValidation:
    def test_development_skips_validation(self) -> None:
        s = Settings(environment="development", secret_key=_INSECURE_SECRET_KEY)
        s.validate_production()  # must not raise

    def test_production_rejects_default_secret_key(self) -> None:
        s = Settings(environment="production", secret_key=_INSECURE_SECRET_KEY)
        with pytest.raises(RuntimeError, match="SECRET_KEY must be changed"):
            s.validate_production()

    def test_production_rejects_short_secret_key(self) -> None:
        s = Settings(environment="production", secret_key="tooshort")
        with pytest.raises(RuntimeError, match="SECRET_KEY must be at least 32"):
            s.validate_production()

    def test_production_rejects_empty_allowed_origins(self) -> None:
        s = Settings(
            environment="production",
            secret_key="a" * 64,
            allowed_origins=[],
        )
        with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS must be set"):
            s.validate_production()

    def test_production_passes_when_configured(self) -> None:
        s = Settings(
            environment="production",
            secret_key="a-very-long-and-secure-secret-key-for-testing-purposes",
            allowed_origins=["https://app.eios.io"],
        )
        s.validate_production()  # must not raise

    def test_rate_limit_defaults(self) -> None:
        s = Settings()
        assert s.rate_limit_auth_per_minute == 10
        assert s.rate_limit_api_per_minute == 120
        assert s.rate_limit_llm_per_minute == 20

    def test_db_pool_defaults(self) -> None:
        s = Settings()
        assert s.db_pool_size == 10
        assert s.db_pool_max_overflow == 20
        assert s.db_pool_timeout == 30

    def test_llm_budget_default_is_unlimited(self) -> None:
        s = Settings()
        assert s.llm_monthly_token_budget == 0

    def test_is_production_flag(self) -> None:
        s = Settings(environment="production")
        assert s.is_production
        assert not s.is_development

    def test_is_development_flag(self) -> None:
        s = Settings(environment="development")
        assert s.is_development
        assert not s.is_production
