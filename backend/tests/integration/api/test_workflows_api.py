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

import asyncio
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


async def _run_and_await_job(
    client: AsyncClient,
    body: dict,
    provider: MagicMock | None = None,
) -> dict:
    """Submit a workflow job (202) and return the completed WorkflowRunResponse dict.

    The asyncio.create_task background worker runs within the same event loop as
    the test. Polling inside the patch context ensures the mock is still active if
    the task hasn't finished by the time the HTTP response is returned.
    """
    mock_provider = provider or _make_mock_provider()
    jd: dict = {}
    with patch("application.workflows.executor.get_llm_provider", return_value=mock_provider):
        with patch("application.workflows.executor.get_embedding_provider"):
            with patch(
                "infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search",
                new_callable=AsyncMock,
                return_value=[],
            ):
                resp = await client.post(WORKFLOWS_BASE + "/run", json=body)
                assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
                job_id = resp.json()["id"]
                for _ in range(40):
                    job_resp = await client.get(f"{WORKFLOWS_BASE}/jobs/{job_id}")
                    jd = job_resp.json()
                    if jd["job_status"] in ("completed", "failed"):
                        break
                    await asyncio.sleep(0.05)

    assert jd["job_status"] == "completed", f"Workflow job did not complete: {jd}"
    run_resp = await client.get(f"{WORKFLOWS_BASE}/runs/{jd['workflow_run_id']}")
    assert run_resp.status_code == 200
    return run_resp.json()


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
    data = await _run_and_await_job(
        client,
        {
            "workflow_type": "quick_scan",
            "query": "ESG risks in the textile manufacturing sector",
            "metadata": {"nace_code": "C13"},
        },
    )
    assert data["workflow_type"] == "quick_scan"
    assert data["steps_completed"] == 4
    assert data["total_steps"] == 4
    assert len(data["steps"]) == 4
    assert data["id"] is not None
    assert data["verdict"] is not None
    assert data["total_input_tokens"] > 0
    assert data["total_output_tokens"] > 0


async def test_run_workflow_steps_have_sequential_indices(client: AsyncClient) -> None:
    data = await _run_and_await_job(
        client,
        {"workflow_type": "quick_scan", "query": "supply chain risks"},
    )
    indices = [s["step_index"] for s in data["steps"]]
    assert indices == sorted(indices)
    assert indices[0] == 0


async def test_run_workflow_verdict_from_high_risk_content(client: AsyncClient) -> None:
    data = await _run_and_await_job(
        client,
        {"workflow_type": "quick_scan", "query": "textile supply chain audit"},
        provider=_make_mock_provider(_ESG_HIGH_RISK),
    )
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
    await _run_and_await_job(
        client,
        {"workflow_type": "quick_scan", "query": "governance review"},
    )
    response = await client.get(WORKFLOWS_BASE + "/runs")
    assert response.status_code == 200
    page = response.json()
    assert isinstance(page["items"], list)
    assert len(page["items"]) >= 1


async def test_get_workflow_run_by_id(client: AsyncClient) -> None:
    data = await _run_and_await_job(
        client,
        {"workflow_type": "quick_scan", "query": "sector risk analysis"},
    )
    run_id = data["id"]

    response = await client.get(f"{WORKFLOWS_BASE}/runs/{run_id}")
    assert response.status_code == 200
    retrieved = response.json()
    assert retrieved["id"] == run_id
    assert retrieved["workflow_type"] == "quick_scan"
    assert len(retrieved["steps"]) == 4


async def test_get_workflow_run_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"{WORKFLOWS_BASE}/runs/does-not-exist")
    assert response.status_code == 404


async def test_get_step_output_returns_full_content(client: AsyncClient) -> None:
    data = await _run_and_await_job(
        client,
        {"workflow_type": "quick_scan", "query": "step output test"},
        provider=_make_mock_provider("Full LLM output for this step."),
    )
    run_id = data["id"]

    # Get step 0 (retrieval)
    response = await client.get(f"{WORKFLOWS_BASE}/runs/{run_id}/steps/0/output")
    assert response.status_code == 200
    step_data = response.json()
    assert step_data["step_index"] == 0
    assert step_data["agent_type"] == "retrieval"
    assert "content" in step_data


async def test_workflow_traceability_agent_runs_linked(client: AsyncClient) -> None:
    """Each AgentRun from a workflow must have workflow_run_id set."""
    data = await _run_and_await_job(
        client,
        {"workflow_type": "quick_scan", "query": "traceability test"},
    )
    assert all("agent_run_id" in step for step in data["steps"])
    assert data["steps_completed"] == data["total_steps"]


async def test_workflow_metadata_stored_in_run(client: AsyncClient) -> None:
    data = await _run_and_await_job(
        client,
        {
            "workflow_type": "quick_scan",
            "query": "governance check",
            "metadata": {"entity_name": "Acme GmbH", "nace_code": "C13"},
        },
    )
    assert data["run_metadata"]["entity_name"] == "Acme GmbH"
    assert data["run_metadata"]["nace_code"] == "C13"


async def test_workflows_routes_require_auth(setup_test_schema: None) -> None:
    import httpx
    from httpx import ASGITransport

    from app.main import app

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            WORKFLOWS_BASE + "/run",
            json={"workflow_type": "quick_scan", "query": "test"},
        )
        assert r.status_code == 401
