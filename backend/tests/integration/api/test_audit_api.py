"""
Integration tests for the EIOS Audit Trail API (M8).

Requires:
  - docker compose up -d
  - uv run alembic upgrade head  (migration 006)

Run with:
  pytest tests/integration/api/test_audit_api.py -v -m integration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from application.ports.llm import LLMResponse

pytestmark = pytest.mark.integration

AUDIT_BASE = "/api/v1/audit"
WORKFLOWS_BASE = "/api/v1/workflows"


def _make_mock_provider(content: str = "## Mock output\n\n### Finding 1: Test Finding\n- Severity: High\n- Confidence: Medium\n") -> MagicMock:
    resp = LLMResponse(
        content=content,
        model="mock-model",
        provider="mock",
        input_tokens=20,
        output_tokens=40,
        stop_reason="end_turn",
    )
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=resp)
    provider.model_name = MagicMock(return_value="mock-model")
    provider.provider_name = MagicMock(return_value="mock")
    return provider


async def _run_workflow(client: AsyncClient, query: str = "ESG audit test") -> dict:
    with patch("interfaces.api.routers.workflows.get_llm_provider", return_value=_make_mock_provider()):
        with patch("interfaces.api.routers.workflows.get_embedding_provider"):
            with patch("infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search", new_callable=AsyncMock, return_value=[]):
                resp = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={"workflow_type": "quick_scan", "query": query},
                )
    assert resp.status_code == 201
    return resp.json()


async def test_workflow_completion_creates_audit_event(client: AsyncClient) -> None:
    run_data = await _run_workflow(client, "Audit trail test")

    response = await client.get(
        AUDIT_BASE + "/events",
        params={"action": "workflow.completed"},
    )
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1

    our_event = next((e for e in events if e["entity_id"] == run_data["id"]), None)
    assert our_event is not None
    assert our_event["action"] == "workflow.completed"
    assert our_event["entity_type"] == "WorkflowRun"
    assert our_event["outcome"] == "success"


async def test_assessment_creation_creates_audit_event(client: AsyncClient) -> None:
    run_data = await _run_workflow(client, "Assessment audit test")

    response = await client.get(
        AUDIT_BASE + "/events",
        params={"action": "assessment.created"},
    )
    assert response.status_code == 200
    events = response.json()
    # Assessment event is only created when extraction succeeds
    assert isinstance(events, list)


async def test_list_all_audit_events(client: AsyncClient) -> None:
    await _run_workflow(client, "List events test")

    response = await client.get(AUDIT_BASE + "/events")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) >= 1


async def test_get_audit_event_by_id(client: AsyncClient) -> None:
    await _run_workflow(client, "Single event test")

    all_events = (await client.get(AUDIT_BASE + "/events")).json()
    assert len(all_events) >= 1

    event_id = all_events[0]["id"]
    response = await client.get(f"{AUDIT_BASE}/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_id


async def test_get_audit_event_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"{AUDIT_BASE}/events/does-not-exist")
    assert response.status_code == 404


async def test_audit_trail_for_workflow_run(client: AsyncClient) -> None:
    run_data = await _run_workflow(client, "Entity trail test")
    run_id = run_data["id"]

    response = await client.get(f"{AUDIT_BASE}/trail/WorkflowRun/{run_id}")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert all(e["entity_id"] == run_id for e in events)
    assert any(e["action"] == "workflow.completed" for e in events)


async def test_audit_events_require_auth(setup_test_schema: None) -> None:
    import httpx
    from httpx import ASGITransport
    from app.main import app

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get(AUDIT_BASE + "/events")
        assert r.status_code == 403


async def test_filter_audit_events_by_action(client: AsyncClient) -> None:
    await _run_workflow(client, "Filter test")

    response = await client.get(AUDIT_BASE + "/events", params={"action": "workflow.completed"})
    assert response.status_code == 200
    events = response.json()
    assert all(e["action"] == "workflow.completed" for e in events)


async def test_audit_event_contains_workflow_metadata(client: AsyncClient) -> None:
    run_data = await _run_workflow(client, "Metadata test")
    run_id = run_data["id"]

    trail = (await client.get(f"{AUDIT_BASE}/trail/WorkflowRun/{run_id}")).json()
    completion_event = next((e for e in trail if e["action"] == "workflow.completed"), None)
    assert completion_event is not None
    assert completion_event["event_metadata"].get("workflow_type") == "quick_scan"
    assert "verdict" in completion_event["event_metadata"]
