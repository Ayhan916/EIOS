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

_DEFAULT_DB = "postgresql+asyncpg://eios:eios_dev@localhost:5432/eios_db"
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


@pytest_asyncio.fixture
async def client(auth_token: str) -> AsyncClient:  # type: ignore[misc]
    """Authenticated httpx client for API integration tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as c:
        yield c
