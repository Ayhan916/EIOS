"""
EIOS Backend Configuration

Single source of truth for all runtime configuration.
Values are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://eios:eios_dev@localhost:5432/eios_db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # Embedding — default: BGE-small (384 dims, fast CPU, strong English retrieval)
    # Production recommendation: intfloat/multilingual-e5-large (1024 dims, multilingual ESG)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    embedding_chunk_size: int = 512
    embedding_chunk_overlap: int = 50
    # Document ingestion
    max_upload_size_mb: int = 50
    # LLM provider — default: anthropic; options: anthropic, openai
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 4096
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
