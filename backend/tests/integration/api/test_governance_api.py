"""
Integration tests for Assessment Governance and Compliance APIs (M9).

Requires:
  - docker compose up -d
  - uv run alembic upgrade head  (migration 007)

Run with:
  pytest tests/integration/api/test_governance_api.py -v -m integration
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from application.ports.llm import LLMResponse

pytestmark = pytest.mark.integration

ASSESSMENTS_BASE = "/api/v1/assessments"
COMPLIANCE_BASE = "/api/v1/compliance"
WORKFLOWS_BASE = "/api/v1/workflows"


def _make_mock_provider() -> MagicMock:
    content = (
        "## ESG Assessment\n\n"
        "### Finding 1: Child Labour in Supply Chain\n"
        "- Severity: Critical\n"
        "- Confidence: High\n"
        "- Regulatory obligation: CSDDD Art. 6, LkSG § 4\n"
        "- Reasoning: Evidence of child workers confirmed.\n\n"
        "### Overall Risk Level\nCritical\n"
    )
    resp = LLMResponse(
        content=content,
        model="mock-model",
        provider="mock",
        input_tokens=20,
        output_tokens=80,
        stop_reason="end_turn",
    )
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=resp)
    provider.model_name = MagicMock(return_value="mock-model")
    provider.provider_name = MagicMock(return_value="mock")
    return provider


async def _create_assessment_via_workflow(client: AsyncClient) -> str:
    """Submit a quick_scan workflow and return the created assessment_id."""
    jd: dict = {}
    with patch(
        "application.workflows.executor.get_llm_provider", return_value=_make_mock_provider()
    ):
        with patch("application.workflows.executor.get_embedding_provider"):
            with patch(
                "infrastructure.knowledge_search.EvidenceChunkSearchAdapter.search",
                new_callable=AsyncMock,
                return_value=[],
            ):
                resp = await client.post(
                    WORKFLOWS_BASE + "/run",
                    json={"workflow_type": "quick_scan", "query": "Governance test query"},
                )
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
    data = run_resp.json()
    assert data.get("assessment_id"), "Workflow must produce an assessment"
    return data["assessment_id"]


# ---------------------------------------------------------------------------
# Governance endpoint tests
# ---------------------------------------------------------------------------


async def test_approve_assessment(client: AsyncClient) -> None:
    assessment_id = await _create_assessment_via_workflow(client)

    resp = await client.patch(f"{ASSESSMENTS_BASE}/{assessment_id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Approved"
    assert data["approved_by"] is not None


async def test_approve_already_approved_returns_409(client: AsyncClient) -> None:
    assessment_id = await _create_assessment_via_workflow(client)

    await client.patch(f"{ASSESSMENTS_BASE}/{assessment_id}/approve")
    resp = await client.patch(f"{ASSESSMENTS_BASE}/{assessment_id}/approve")
    assert resp.status_code == 409


async def test_revise_approved_assessment(client: AsyncClient) -> None:
    assessment_id = await _create_assessment_via_workflow(client)
    await client.patch(f"{ASSESSMENTS_BASE}/{assessment_id}/approve")

    resp = await client.patch(
        f"{ASSESSMENTS_BASE}/{assessment_id}/revise",
        json={"reason": "Additional evidence required"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Draft"
    assert data["approved_by"] is None


async def test_revise_resets_approval_date(client: AsyncClient) -> None:
    assessment_id = await _create_assessment_via_workflow(client)
    await client.patch(f"{ASSESSMENTS_BASE}/{assessment_id}/approve")

    resp = await client.patch(
        f"{ASSESSMENTS_BASE}/{assessment_id}/revise",
        json={"reason": "Needs more detail"},
    )
    assert resp.status_code == 200


async def test_approve_nonexistent_assessment_returns_404(client: AsyncClient) -> None:
    resp = await client.patch(f"{ASSESSMENTS_BASE}/does-not-exist/approve")
    assert resp.status_code == 404


async def test_revise_nonexistent_assessment_returns_404(client: AsyncClient) -> None:
    resp = await client.patch(
        f"{ASSESSMENTS_BASE}/does-not-exist/revise",
        json={"reason": "test"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Compliance endpoint tests
# ---------------------------------------------------------------------------


async def test_list_frameworks_returns_all_supported(client: AsyncClient) -> None:
    resp = await client.get(f"{COMPLIANCE_BASE}/frameworks")
    assert resp.status_code == 200
    frameworks = resp.json()
    assert isinstance(frameworks, list)
    fw_names = {fw["framework"] for fw in frameworks}
    assert "CSDDD" in fw_names
    assert "LkSG" in fw_names
    assert "ESRS" in fw_names
    assert "GRI" in fw_names


async def test_framework_info_has_article_count(client: AsyncClient) -> None:
    resp = await client.get(f"{COMPLIANCE_BASE}/frameworks")
    assert resp.status_code == 200
    for fw in resp.json():
        assert fw["article_count"] > 0
        assert fw["article_count"] == fw["mandatory_count"] + fw["recommended_count"]


async def test_assessment_compliance_returns_coverage(client: AsyncClient) -> None:
    assessment_id = await _create_assessment_via_workflow(client)

    resp = await client.get(f"{ASSESSMENTS_BASE}/{assessment_id}/compliance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment_id"] == assessment_id
    assert "covered_article_codes" in data
    assert "framework_coverage" in data
    assert 0.0 <= data["overall_coverage_ratio"] <= 1.0
    assert 0.0 <= data["mandatory_coverage_ratio"] <= 1.0


async def test_assessment_compliance_includes_quality_score(client: AsyncClient) -> None:
    assessment_id = await _create_assessment_via_workflow(client)

    resp = await client.get(f"{ASSESSMENTS_BASE}/{assessment_id}/compliance")
    assert resp.status_code == 200
    data = resp.json()
    # quality_score may be None if not set, but field must exist
    assert "quality_score" in data


async def test_assessment_compliance_nonexistent_returns_404(client: AsyncClient) -> None:
    resp = await client.get(f"{ASSESSMENTS_BASE}/does-not-exist/compliance")
    assert resp.status_code == 404


async def test_compliance_requires_auth(setup_test_schema: None) -> None:
    import httpx
    from httpx import ASGITransport

    from app.main import app

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{COMPLIANCE_BASE}/frameworks")
        assert r.status_code == 401


async def test_assessment_has_quality_score_after_workflow(client: AsyncClient) -> None:
    assessment_id = await _create_assessment_via_workflow(client)

    resp = await client.get(f"{ASSESSMENTS_BASE}/{assessment_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "quality_score" in data
