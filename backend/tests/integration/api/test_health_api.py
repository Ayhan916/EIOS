import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "eios-backend"


async def test_health_includes_version(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert "version" in response.json()
