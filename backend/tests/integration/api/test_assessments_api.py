import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

BASE = "/api/v1/assessments"
SECTORS_BASE = "/api/v1/sectors"
FINDINGS_BASE = "/api/v1/findings"
RISKS_BASE = "/api/v1/risks"


async def test_create_assessment(client: AsyncClient) -> None:
    response = await client.post(
        BASE + "/",
        json={"title": "NACE B ESG Assessment", "description": "Mining sector ESG due diligence"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "NACE B ESG Assessment"
    assert data["confidence"] == "High"
    assert "id" in data

    await client.delete(f"{BASE}/{data['id']}")


async def test_get_assessment_by_id(client: AsyncClient) -> None:
    create = await client.post(
        BASE + "/",
        json={"title": "Test Assessment", "description": "D", "scope": "Sector B"},
    )
    aid = create.json()["id"]

    response = await client.get(f"{BASE}/{aid}")
    assert response.status_code == 200
    assert response.json()["scope"] == "Sector B"

    await client.delete(f"{BASE}/{aid}")


async def test_get_assessment_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/does-not-exist")
    assert response.status_code == 404


async def test_list_assessments_by_sector(client: AsyncClient) -> None:
    sector = await client.post(
        SECTORS_BASE + "/", json={"name": "TestSector", "nace_code": "TS-ASSESS"}
    )
    sector_id = sector.json()["id"]

    a1 = await client.post(
        BASE + "/",
        json={"title": "A1", "description": "D", "sector_id": sector_id},
    )
    a2 = await client.post(
        BASE + "/",
        json={"title": "A2", "description": "D", "sector_id": sector_id},
    )

    response = await client.get(BASE + "/", params={"sector_id": sector_id})
    assert response.status_code == 200
    assert len(response.json()) == 2

    for aid in [a1.json()["id"], a2.json()["id"]]:
        await client.delete(f"{BASE}/{aid}")
    await client.delete(f"{SECTORS_BASE}/{sector_id}")


async def test_list_assessment_findings(client: AsyncClient) -> None:
    assessment = await client.post(BASE + "/", json={"title": "Finding Source", "description": "D"})
    aid = assessment.json()["id"]

    f1 = await client.post(
        FINDINGS_BASE + "/",
        json={"title": "F1", "description": "D", "assessment_id": aid},
    )
    f2 = await client.post(
        FINDINGS_BASE + "/",
        json={"title": "F2", "description": "D", "assessment_id": aid},
    )

    response = await client.get(f"{BASE}/{aid}/findings")
    assert response.status_code == 200
    assert len(response.json()) == 2

    for fid in [f1.json()["id"], f2.json()["id"]]:
        await client.delete(f"{FINDINGS_BASE}/{fid}")
    await client.delete(f"{BASE}/{aid}")


async def test_list_assessment_risks(client: AsyncClient) -> None:
    assessment = await client.post(BASE + "/", json={"title": "Risk Source", "description": "D"})
    aid = assessment.json()["id"]

    r1 = await client.post(
        RISKS_BASE + "/",
        json={"title": "R1", "description": "D", "assessment_id": aid},
    )

    response = await client.get(f"{BASE}/{aid}/risks")
    assert response.status_code == 200
    assert len(response.json()) == 1

    await client.delete(f"{RISKS_BASE}/{r1.json()['id']}")
    await client.delete(f"{BASE}/{aid}")


async def test_delete_assessment(client: AsyncClient) -> None:
    create = await client.post(BASE + "/", json={"title": "To Delete", "description": "D"})
    aid = create.json()["id"]

    response = await client.delete(f"{BASE}/{aid}")
    assert response.status_code == 204

    get = await client.get(f"{BASE}/{aid}")
    assert get.status_code == 404
