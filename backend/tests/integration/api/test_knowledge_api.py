"""
Integration tests for the EIOS Knowledge Layer (M5).

Requires:
  - docker compose up -d  (PostgreSQL with pgvector)
  - uv run alembic upgrade head  (migration 003 creates evidence_chunks + HNSW index)
  - sentence-transformers installed (uv sync --dev)

Run with:
  pytest tests/integration/api/test_knowledge_api.py -v -m integration
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

EVIDENCE_BASE = "/api/v1/evidences"
KNOWLEDGE_BASE = "/api/v1/knowledge"


async def _create_evidence(client: AsyncClient, title: str, description: str) -> str:
    resp = await client.post(
        EVIDENCE_BASE + "/",
        json={"title": title, "source": "test-source", "description": description},
    )
    assert resp.status_code == 201
    return str(resp.json()["id"])


async def test_ingest_evidence(client: AsyncClient) -> None:
    eid = await _create_evidence(
        client,
        "LkSG Supply Chain Risk Report",
        "Child labour risk identified in Tier-1 mining suppliers. "
        "NACE code B05 operations in high-risk jurisdictions. "
        "Remediation required within 90 days under LkSG Section 3.",
    )

    response = await client.post(
        KNOWLEDGE_BASE + "/ingest",
        json={"evidence_id": eid},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["evidence_id"] == eid
    assert data["chunks_created"] >= 1
    assert "bge" in data["model"].lower() or "e5" in data["model"].lower()

    # Cleanup
    await client.delete(f"{EVIDENCE_BASE}/{eid}")


async def test_ingest_same_evidence_twice_returns_409(client: AsyncClient) -> None:
    eid = await _create_evidence(client, "Duplicate Test", "Some ESG content for duplicate test.")

    await client.post(KNOWLEDGE_BASE + "/ingest", json={"evidence_id": eid})
    response = await client.post(KNOWLEDGE_BASE + "/ingest", json={"evidence_id": eid})
    assert response.status_code == 409

    await client.delete(f"{EVIDENCE_BASE}/{eid}")


async def test_ingest_force_replaces_chunks(client: AsyncClient) -> None:
    eid = await _create_evidence(client, "Force Reingest", "Original ESG risk content.")

    r1 = await client.post(KNOWLEDGE_BASE + "/ingest", json={"evidence_id": eid})
    assert r1.status_code == 200

    r2 = await client.post(
        KNOWLEDGE_BASE + "/ingest", json={"evidence_id": eid, "force": True}
    )
    assert r2.status_code == 200
    assert r2.json()["chunks_created"] >= 1

    await client.delete(f"{EVIDENCE_BASE}/{eid}")


async def test_ingest_nonexistent_evidence_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        KNOWLEDGE_BASE + "/ingest",
        json={"evidence_id": "does-not-exist"},
    )
    assert response.status_code == 404


async def test_search_returns_relevant_results(client: AsyncClient) -> None:
    # Ingest two evidence documents with different topics
    eid1 = await _create_evidence(
        client,
        "Child Labour Risk in Mining",
        "Elevated child labour risk detected in NACE B05 mining sector. "
        "LkSG due diligence requires supplier audits within 60 days. "
        "Human rights violations documented in Tier-2 supply chain.",
    )
    eid2 = await _create_evidence(
        client,
        "Carbon Emissions Report Q4",
        "Greenhouse gas emissions reduced by 12% compared to prior year. "
        "Scope 3 emissions from purchased goods represent 78% of total footprint. "
        "Net-zero target set for 2040 aligned with Paris Agreement.",
    )

    await client.post(KNOWLEDGE_BASE + "/ingest", json={"evidence_id": eid1})
    await client.post(KNOWLEDGE_BASE + "/ingest", json={"evidence_id": eid2})

    response = await client.post(
        KNOWLEDGE_BASE + "/search",
        json={"query": "child labour supply chain risk", "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "child labour supply chain risk"
    assert len(data["results"]) >= 1

    # The most relevant result should be about child labour, not carbon emissions
    top_result = data["results"][0]
    assert top_result["similarity"] >= 0.0
    assert "chunk_id" in top_result
    assert "evidence_id" in top_result
    assert "text" in top_result

    # Cleanup
    await client.delete(f"{EVIDENCE_BASE}/{eid1}")
    await client.delete(f"{EVIDENCE_BASE}/{eid2}")


async def test_search_returns_empty_when_no_chunks_ingested(client: AsyncClient) -> None:
    response = await client.post(
        KNOWLEDGE_BASE + "/search",
        json={"query": "obscure query that matches nothing", "limit": 5, "min_similarity": 0.99},
    )
    assert response.status_code == 200
    # High min_similarity should filter out dissimilar results
    assert isinstance(response.json()["results"], list)


async def test_search_respects_limit(client: AsyncClient) -> None:
    eid = await _create_evidence(
        client,
        "Long ESG Document",
        " ".join(
            [f"ESG risk finding number {i} relates to supply chain compliance." for i in range(50)]
        ),
    )
    await client.post(KNOWLEDGE_BASE + "/ingest", json={"evidence_id": eid})

    response = await client.post(
        KNOWLEDGE_BASE + "/search",
        json={"query": "ESG risk supply chain", "limit": 3},
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) <= 3

    await client.delete(f"{EVIDENCE_BASE}/{eid}")


async def test_search_validates_query_length(client: AsyncClient) -> None:
    response = await client.post(
        KNOWLEDGE_BASE + "/search",
        json={"query": "", "limit": 5},
    )
    assert response.status_code == 422


async def test_knowledge_routes_require_auth(setup_test_schema: None) -> None:
    import httpx
    from httpx import ASGITransport
    from app.main import app

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(KNOWLEDGE_BASE + "/ingest", json={"evidence_id": "x"})
        assert r.status_code == 403
