"""M47 — Regional routing layer.

Maps an organization's `data_residency` tag (EU | US | APAC) to the correct
infrastructure resources: database session factory, S3 bucket, Celery queue.

Design:
  - Each region has a primary DB URL; falls back to the global primary when unset.
  - Session factories are created lazily and cached per region.
  - Callers always get a valid factory — never None.
  - S3 and Celery routing follow the same fallback pattern.

Usage:
    factory = region_router.get_session_factory("EU")
    async with factory() as session:
        ...

    bucket = region_router.get_s3_bucket("US")
    queue  = region_router.get_celery_queue("APAC")
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import settings

VALID_REGIONS: frozenset[str] = frozenset({"EU", "US", "APAC"})

# Celery queue names per region — workers subscribe to their regional queue
REGION_QUEUE: dict[str, str] = {
    "EU": "eios-eu",
    "US": "eios-us",
    "APAC": "eios-apac",
}

# S3 region identifiers for boto3 (used when building signed URLs)
REGION_S3_AWS_REGION: dict[str, str] = {
    "EU": "eu-west-1",
    "US": "us-east-1",
    "APAC": "ap-southeast-1",
}


def _normalize(region: str | None) -> str:
    """Return uppercased region, or instance_region if unknown/None."""
    if region and region.upper() in VALID_REGIONS:
        return region.upper()
    return settings.instance_region.upper()


@lru_cache(maxsize=4)
def _build_session_factory(db_url: str) -> async_sessionmaker[AsyncSession]:
    """Build and cache an async session factory for the given URL."""
    eng = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )
    return async_sessionmaker(eng, expire_on_commit=False, autoflush=False, autocommit=False)


def _region_db_url(region: str) -> str:
    mapping = {
        "EU": settings.region_db_eu_url,
        "US": settings.region_db_us_url,
        "APAC": settings.region_db_apac_url,
    }
    return mapping.get(region, "") or settings.database_url


class RegionRouter:
    """Stateless router — all methods are pure functions of settings + region tag."""

    def get_session_factory(self, region: str | None) -> async_sessionmaker[AsyncSession]:
        """Return the session factory for the given region.

        Falls back to the primary DB when no regional URL is configured.
        """
        r = _normalize(region)
        return _build_session_factory(_region_db_url(r))

    def get_s3_bucket(self, region: str | None) -> str:
        """Return the S3 bucket name for the given region."""
        r = _normalize(region)
        mapping = {
            "EU": settings.region_s3_bucket_eu or settings.s3_bucket,
            "US": settings.region_s3_bucket_us or settings.s3_bucket,
            "APAC": settings.region_s3_bucket_apac or settings.s3_bucket,
        }
        return mapping.get(r, settings.s3_bucket)

    def get_celery_queue(self, region: str | None) -> str:
        """Return the Celery queue name for the given region."""
        r = _normalize(region)
        return REGION_QUEUE.get(r, "eios-us")

    def get_aws_region(self, region: str | None) -> str:
        """Return the AWS region string for S3/boto3 usage."""
        r = _normalize(region)
        return REGION_S3_AWS_REGION.get(r, settings.s3_region)

    def is_local_region(self, region: str | None) -> bool:
        """True if the org's region matches the current instance's region."""
        return _normalize(region) == _normalize(settings.instance_region)

    def canonical(self, region: str | None) -> str:
        """Return the canonical (uppercased, validated) region string."""
        return _normalize(region)


region_router = RegionRouter()
