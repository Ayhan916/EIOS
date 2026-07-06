"""
Shared fixtures for EIOS API integration tests.

Requires a running PostgreSQL instance:
  docker compose up -d

Run with:
  pytest tests/integration/ -v -m integration
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from infrastructure.persistence.models import Base

_DEFAULT_DB = "postgresql+asyncpg://eios:eios_dev@localhost:5432/eios_test_db"
TEST_DATABASE_URL = os.environ.get("DATABASE_URL", _DEFAULT_DB)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_schema() -> None:  # type: ignore[misc]
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def auth_token(setup_test_schema: None) -> str:  # type: ignore[misc]
    """Register a test user once per session and return a valid access token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post(
            "/api/v1/auth/register",
            json={
                "email": "test@eios.dev",
                "display_name": "Test User",
                "password": "test-password-secure",
                "role": "admin",
                "organization_name": "EIOS Test Org",
            },
        )
        # 201 on first run, 409 on subsequent runs (user already exists)
        if response.status_code == 409:
            login = await c.post(
                "/api/v1/auth/login",
                json={"email": "test@eios.dev", "password": "test-password-secure"},
            )
            return str(login.json()["access_token"])
        return str(response.json()["access_token"])


@pytest_asyncio.fixture(scope="session", autouse=True)
async def mock_embedding_provider(setup_test_schema: None) -> None:  # type: ignore[misc]
    """Override the FastAPI embedding provider dependency for all integration tests.

    The knowledge router uses Depends(get_embedding_provider). Since the test
    ASGI transport does not run lifespan events, the provider singleton is never
    initialised. We override the dependency with a mock that returns valid 384-d
    vectors (matching settings.embedding_dim) so knowledge-layer tests work
    without requiring sentence-transformers model weights at test time.
    """
    from unittest.mock import AsyncMock, MagicMock

    from infrastructure.embeddings.deps import get_embedding_provider

    mock_provider = MagicMock()
    mock_provider.embed_documents = AsyncMock(
        side_effect=lambda texts: [[0.1] * 384 for _ in texts]
    )
    mock_provider.embed_query = AsyncMock(return_value=[0.1] * 384)

    app.dependency_overrides[get_embedding_provider] = lambda: mock_provider
    yield
    app.dependency_overrides.pop(get_embedding_provider, None)


@pytest_asyncio.fixture
async def client(auth_token: str) -> AsyncClient:  # type: ignore[misc]
    """Authenticated httpx client for API integration tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as c:
        yield c
