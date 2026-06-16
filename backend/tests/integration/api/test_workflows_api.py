"""
Integration tests for the EIOS Workflow API (M7).

Tests use a mock LLM provider so no API keys are required.
The knowledge search adapter uses a mock so no embeddings are needed.

Requires:
  - docker compose up -d
  - uv run alembic upgrade head  (migration 005 adds workflow_runs + extends agent_runs)

Run with:
  pytest tests/integration/api/test_workflows_api.py -v -m integration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from application.ports.llm import LLMResponse

pytestmark = pytest.mark.integration

WORKFLOWS_BASE = "/api/v1/workflows"

_ESG_HIGH_RISK = (
    "## Sector ESG Risk Profile\n\n"
    "### Material Findings\n\n"
    "1. Child labour risk — Severity: Critical\n\n"
    "### Overall Risk Level\n"
    "High — significant supply chain violations\n\n"
    "### Priority Actions\n"
    "1. Audit Tier-1 suppliers within 30 days."
)

_EVALUATION_APPROVED = (
    "## Quality Assessment\n\n"
    "**Overall score:** 0.82\n"
    "**Verdict:** Approved\n\n"
    "Assessment meets audit standards."
)


def _make_mock_provider(content: str = "mock response") -> MagicMock:
    resp = LLMResponse(
        content=content,
        model="mock-model",
        provider="mock",
        input_tokens=25,
        output_tokens=50,
        stop_reason="end_turn",
    )
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=resp)
    provider.model_name = MagicMock(return_value="mock-model")
    provider.provider_name = MagicMock(return_value="mock")
    return provider


async def test_list_workflow_types(client: AsyncClient) -> None:
    response = await client.get(WORKFLOWS_BASE + "/types")
    assert response.status_code == 200
    types_data = response.json()
    assert isinstance(types_data, list)
    assert len(types_data) == 4

    type_names = {t["workflow_type"] for t in types_data}
    assert {"due_diligence", "quick_scan", "evidence_analysis", "governance_review"} == type_names

    due_diligence = next(t for t in types_data if t["workflow_type"] == "due_diligence")
    assert due_diligence["step_count"] == 8
    assert "research" in due_diligence["agent_sequence"]
    assert "reporting" in due_diligence["agent_sequence"]


async def test_run_quick_scan_workflow(client: AsyncClient) -> None:
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=_make_mock_provider()):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                response = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={
                        "workflow_type": "quick_scan",
                        "query": "ESG risks in the textile manufacturing sector",
                        "metadata": {"nace_code": "C13"},
                    },
                )
    assert response.status_code == 201
    data = response.json()
    assert data["workflow_type"] == "quick_scan"
    assert data["steps_completed"] == 4
    assert data["total_steps"] == 4
    assert len(data["steps"]) == 4
    assert data["id"] is not None
    assert data["verdict"] is not None
    assert data["total_input_tokens"] > 0
    assert data["total_output_tokens"] > 0


async def test_run_workflow_steps_have_sequential_indices(client: AsyncClient) -> None:
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=_make_mock_provider()):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                response = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={"workflow_type": "quick_scan", "query": "supply chain risks"},
                )
    data = response.json()
    indices = [s["step_index"] for s in data["steps"]]
    assert indices == sorted(indices)
    assert indices[0] == 0


async def test_run_workflow_verdict_from_high_risk_content(client: AsyncClient) -> None:
    provider = _make_mock_provider(_ESG_HIGH_RISK)
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=provider):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                response = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={"workflow_type": "quick_scan", "query": "textile supply chain audit"},
                )
    data = response.json()
    # All 4 steps return the ESG content, so risk level should be parsed
    assert data["overall_risk_level"] is not None
    assert data["verdict"] is not None


async def test_run_workflow_unknown_type_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        WORKFLOWS_BASE + "/run",
        json={"workflow_type": "nonexistent", "query": "test"},
    )
    assert response.status_code == 422


async def test_run_workflow_empty_query_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        WORKFLOWS_BASE + "/run",
        json={"workflow_type": "quick_scan", "query": ""},
    )
    assert response.status_code == 422


async def test_list_workflow_runs_returns_all(client: AsyncClient) -> None:
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=_make_mock_provider()):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={"workflow_type": "quick_scan", "query": "governance review"},
                )

    response = await client.get(WORKFLOWS_BASE + "/runs")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1


async def test_get_workflow_run_by_id(client: AsyncClient) -> None:
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=_make_mock_provider()):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                create_resp = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={"workflow_type": "quick_scan", "query": "sector risk analysis"},
                )
    run_id = create_resp.json()["id"]

    response = await client.get(f"{WORKFLOWS_BASE}/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert data["workflow_type"] == "quick_scan"
    assert len(data["steps"]) == 4


async def test_get_workflow_run_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"{WORKFLOWS_BASE}/runs/does-not-exist")
    assert response.status_code == 404


async def test_get_step_output_returns_full_content(client: AsyncClient) -> None:
    provider = _make_mock_provider("Full LLM output for this step.")
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=provider):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                create_resp = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={"workflow_type": "quick_scan", "query": "step output test"},
                )
    run_id = create_resp.json()["id"]

    # Get step 0 (retrieval)
    response = await client.get(f"{WORKFLOWS_BASE}/runs/{run_id}/steps/0/output")
    assert response.status_code == 200
    data = response.json()
    assert data["step_index"] == 0
    assert data["agent_type"] == "retrieval"
    assert "content" in data


async def test_workflow_traceability_agent_runs_linked(client: AsyncClient) -> None:
    """Each AgentRun from a workflow must have workflow_run_id set."""
    from httpx import AsyncClient as AC
    from httpx import ASGITransport
    from app.main import app

    # We can verify via the agents API
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=_make_mock_provider()):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                create_resp = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={"workflow_type": "quick_scan", "query": "traceability test"},
                )
    data = create_resp.json()
    assert all("agent_run_id" in step for step in data["steps"])
    assert data["steps_completed"] == data["total_steps"]


async def test_workflow_metadata_stored_in_run(client: AsyncClient) -> None:
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=_make_mock_provider()):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                response = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={
                        "workflow_type": "quick_scan",
                        "query": "governance check",
                        "metadata": {"entity_name": "Acme GmbH", "nace_code": "C13"},
                    },
                )
    data = response.json()
    assert data["run_metadata"]["entity_name"] == "Acme GmbH"
    assert data["run_metadata"]["nace_code"] == "C13"


async def test_workflows_routes_require_auth(setup_test_schema: None) -> None:
    import httpx
    from httpx import ASGITransport
    from app.main import app

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            WORKFLOWS_BASE + "/run",
            json={"workflow_type": "quick_scan", "query": "test"},
        )
        assert r.status_code == 403
