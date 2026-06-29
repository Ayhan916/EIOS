"""
EIOS Backend Configuration

Single source of truth for all runtime configuration.
Values are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://eios:eios_dev@localhost:5432/eios_db"
    redis_url: str = "redis://localhost:6379/0"
    # Dedicated noeviction Redis for JWT blacklist (DB=1 of same dev instance).
    # Production: point to a separate Redis instance with maxmemory-policy=noeviction.
    redis_blacklist_url: str = "redis://localhost:6379/1"

    # Read replica — optional separate read-only database for analytics/reporting queries.
    # Leave empty (default) to route all reads to the primary database.
    # Production: set to a streaming-replication standby URL.
    database_readonly_url: str = ""
    secret_key: str = _INSECURE_SECRET_KEY
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    mfa_session_expire_minutes: int = 5
    external_audit_token_expire_hours: int = 72

    # Celery — background task processing
    celery_broker_url: str = "redis://localhost:6379/2"
    celery_result_backend: str = "redis://localhost:6379/2"

    # S3 object storage for document uploads
    s3_enabled: bool = False
    s3_bucket: str = "eios-documents"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str = ""          # empty = AWS S3; set to MinIO URL for local dev
    aws_access_key_id: str = ""        # empty = use IAM role / instance profile
    aws_secret_access_key: str = ""
    s3_presigned_url_expire_seconds: int = 3600

    # CORS — comma-separated list of allowed origins in production
    # Example: ALLOWED_ORIGINS=https://app.eios.io,https://api.eios.io
    allowed_origins: list[str] = []

    # Rate limiting (requests per minute, per IP)
    rate_limit_auth_per_minute: int = 10
    rate_limit_api_per_minute: int = 120
    rate_limit_llm_per_minute: int = 20

    # LLM spend guard — max tokens per org per calendar month (0 = unlimited)
    llm_monthly_token_budget: int = 0

    # Database connection pool
    db_pool_size: int = 10
    db_pool_max_overflow: int = 20
    db_pool_timeout: int = 30

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
    groq_api_key: str = ""

    # Webhook secret encryption key (Fernet, base64url-encoded 32-byte key)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Leave empty to store secrets in plaintext (acceptable for development).
    webhook_secret_key: str = ""

    # SMTP email — leave smtp_host empty to disable email sending
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@eios.io"
    smtp_tls: bool = True
    app_base_url: str = "https://app.eios.io"

    # ── M28 — Apache Kafka Event Bus ──────────────────────────────────────────
    # Internal broker address (service-to-service inside Docker network).
    # For local dev outside Docker: use localhost:9094
    kafka_bootstrap_servers: str = "localhost:9094"
    kafka_supplier_topic: str = "eios.supplier.events"
    kafka_material_topic: str = "eios.material.events"
    kafka_product_topic: str = "eios.product.events"
    kafka_enabled: bool = True

    # ── M47 — Multi-Region Data Residency ─────────────────────────────────────
    # The region this instance is deployed in. Used to detect cross-region access.
    # Valid values: EU | US | APAC
    instance_region: str = "US"

    # Per-region primary database URLs. Leave empty to fall back to database_url.
    region_db_eu_url: str = ""
    region_db_us_url: str = ""
    region_db_apac_url: str = ""

    # Per-region S3 buckets. Leave empty to fall back to s3_bucket.
    region_s3_bucket_eu: str = ""
    region_s3_bucket_us: str = ""
    region_s3_bucket_apac: str = ""

    # When True, cross-region requests return HTTP 451 (Unavailable for Legal Reasons).
    # When False (default), cross-region access is logged but allowed (advisory mode).
    region_enforcement_strict: bool = False

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def validate_production(self) -> None:
        """Raise on misconfiguration that would be unsafe in production."""
        if not self.is_production:
            return
        errors: list[str] = []
        if self.secret_key == _INSECURE_SECRET_KEY:
            errors.append("SECRET_KEY must be changed from the default value")
        if not self.secret_key or len(self.secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters")
        if not self.allowed_origins:
            errors.append(
                "ALLOWED_ORIGINS must be set to one or more trusted origins "
                "(e.g. https://app.eios.io). Wildcard '*' is not permitted in production."
            )
        if self.redis_url == "redis://localhost:6379/0":
            errors.append("REDIS_URL must be set to a production Redis instance")
        if self.redis_blacklist_url == "redis://localhost:6379/1":
            errors.append(
                "REDIS_BLACKLIST_URL must point to a dedicated noeviction Redis instance. "
                "Token revocation is a security control — eviction must be disabled."
            )
        if errors:
            raise RuntimeError(
                "Production configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )


settings = Settings()
