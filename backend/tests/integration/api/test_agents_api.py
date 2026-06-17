"""
Integration tests for the EIOS Agents API (M6).

These tests use a mock LLM provider so no API keys are required.
They verify:
  - POST /api/v1/agents/run — runs an agent and persists the result
  - GET  /api/v1/agents/runs — lists all runs
  - GET  /api/v1/agents/runs/{id} — retrieves a single run
  - Auth is required for all routes

Requires:
  - docker compose up -d  (PostgreSQL)
  - uv run alembic upgrade head  (migration 004 creates agent_runs table)

Run with:
  pytest tests/integration/api/test_agents_api.py -v -m integration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from application.ports.llm import LLMResponse

pytestmark = pytest.mark.integration

AGENTS_BASE = "/api/v1/agents"

_MOCK_LLM_RESPONSE = LLMResponse(
    content="## Mock ESG Assessment\n\nThis is a mock agent response for testing.",
    model="mock-model",
    provider="mock",
    input_tokens=50,
    output_tokens=100,
    stop_reason="end_turn",
)


def _make_mock_provider() -> MagicMock:
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=_MOCK_LLM_RESPONSE)
    provider.model_name = MagicMock(return_value="mock-model")
    provider.provider_name = MagicMock(return_value="mock")
    return provider


async def test_run_agent_returns_201(client: AsyncClient) -> None:
    with patch(
        "interfaces.api.routers.agents.get_llm_provider", return_value=_make_mock_provider()
    ):
        response = await client.post(
            AGENTS_BASE + "/run",
            json={
                "agent_type": "research",
                "query": "What are the main ESG risks in the textile sector?",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["agent_type"] == "research"
    assert data["query"] == "What are the main ESG risks in the textile sector?"
    assert data["result_content"] is not None
    assert "Mock ESG Assessment" in data["result_content"]
    assert data["input_tokens"] == 50
    assert data["output_tokens"] == 100
    assert data["llm_provider"] == "mock"
    assert data["error"] is None
    assert "id" in data


async def test_run_agent_with_knowledge_chunks(client: AsyncClient) -> None:
    with patch(
        "interfaces.api.routers.agents.get_llm_provider", return_value=_make_mock_provider()
    ):
        response = await client.post(
            AGENTS_BASE + "/run",
            json={
                "agent_type": "retrieval",
                "query": "What are the child labour risks?",
                "knowledge_chunks": [
                    "Child labour detected in Tier-1 suppliers.",
                    "LkSG requires remediation within 90 days.",
                ],
            },
        )
    assert response.status_code == 201
    assert response.json()["agent_type"] == "retrieval"


async def test_run_agent_with_metadata(client: AsyncClient) -> None:
    with patch(
        "interfaces.api.routers.agents.get_llm_provider", return_value=_make_mock_provider()
    ):
        response = await client.post(
            AGENTS_BASE + "/run",
            json={
                "agent_type": "esg_assessment",
                "query": "Assess ESG risks for textile manufacturer",
                "metadata": {"nace_code": "C13", "sector_name": "Textiles"},
            },
        )
    assert response.status_code == 201
    assert response.json()["run_metadata"] == {"nace_code": "C13", "sector_name": "Textiles"}


async def test_run_agent_unknown_type_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        AGENTS_BASE + "/run",
        json={"agent_type": "nonexistent", "query": "test"},
    )
    assert response.status_code == 422


async def test_run_agent_empty_query_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        AGENTS_BASE + "/run",
        json={"agent_type": "research", "query": ""},
    )
    assert response.status_code == 422


async def test_list_agent_runs_returns_200(client: AsyncClient) -> None:
    with patch(
        "interfaces.api.routers.agents.get_llm_provider", return_value=_make_mock_provider()
    ):
        await client.post(
            AGENTS_BASE + "/run",
            json={"agent_type": "reasoning", "query": "Analyse ESG risk chain"},
        )

    response = await client.get(AGENTS_BASE + "/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


async def test_get_agent_run_by_id(client: AsyncClient) -> None:
    with patch(
        "interfaces.api.routers.agents.get_llm_provider", return_value=_make_mock_provider()
    ):
        create_resp = await client.post(
            AGENTS_BASE + "/run",
            json={"agent_type": "governance", "query": "Assess board governance structure"},
        )
    run_id = create_resp.json()["id"]

    response = await client.get(f"{AGENTS_BASE}/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["id"] == run_id
    assert response.json()["agent_type"] == "governance"


async def test_get_agent_run_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"{AGENTS_BASE}/runs/does-not-exist")
    assert response.status_code == 404


async def test_agents_routes_require_auth(setup_test_schema: None) -> None:
    import httpx
    from httpx import ASGITransport

    from app.main import app

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AGENTS_BASE + "/run",
            json={"agent_type": "research", "query": "test"},
        )
        assert r.status_code == 403
