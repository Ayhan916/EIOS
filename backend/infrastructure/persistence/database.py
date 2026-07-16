"""
EIOS Database Infrastructure

Async SQLAlchemy engine and session factory.
All database access flows through the session provided here.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_pool_max_overflow,
    pool_timeout=settings.db_pool_timeout,
)

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Sync engine for strategy services that use session.query() (legacy sync pattern).
# Uses psycopg2 instead of asyncpg.
_sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
_sync_engine = create_engine(
    _sync_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SyncSessionFactory: sessionmaker[Session] = sessionmaker(
    _sync_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session


# ── Read-only session factory (M45.3) ─────────────────────────────────────────
# When DATABASE_READONLY_URL is configured (e.g. a streaming-replication standby),
# analytics and reporting queries can be routed there to offload the primary.
# Falls back to the primary engine when not configured.
_readonly_url = (
    settings.database_readonly_url.replace("postgresql://", "postgresql+asyncpg://")
    if settings.database_readonly_url
    and not settings.database_readonly_url.startswith("postgresql+asyncpg://")
    else settings.database_readonly_url
) or settings.database_url

_readonly_engine = (
    create_async_engine(
        _readonly_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )
    if _readonly_url != settings.database_url
    else engine
)

ReadOnlyAsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _readonly_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_readonly_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session routed to the read replica (or primary if no replica configured)."""
    async with ReadOnlyAsyncSessionFactory() as session:
        yield session


# ── M47 — Regional session factory ────────────────────────────────────────────


def get_regional_session_factory(region: str | None) -> async_sessionmaker[AsyncSession]:
    """Return the session factory for the given data-residency region.

    Falls back to the global primary when no regional URL is configured.
    Import here (not at top) to avoid circular dependency with region_router
    which itself imports shared.config.
    """
    from infrastructure.routing.region_router import region_router  # noqa: PLC0415

    return region_router.get_session_factory(region)
