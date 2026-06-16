import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

BASE = "/api/v1/risks"
SECTORS_BASE = "/api/v1/sectors"


async def test_create_risk(client: AsyncClient) -> None:
    response = await client.post(
        BASE + "/",
        json={
            "title": "Supply Chain Labour Risk",
            "description": "Elevated risk in Tier-1 suppliers",
            "risk_level": "High",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Supply Chain Labour Risk"
    assert data["risk_level"] == "High"
    assert data["confidence"] == "Medium"

    await client.delete(f"{BASE}/{data['id']}")


async def test_risk_probability_impact_persists(client: AsyncClient) -> None:
    response = await client.post(
        BASE + "/",
        json={
            "title": "Quantified Risk",
            "description": "D",
            "probability": 0.7,
            "impact": 0.9,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["probability"] == pytest.approx(0.7)
    assert data["impact"] == pytest.approx(0.9)

    await client.delete(f"{BASE}/{data['id']}")


async def test_list_risks_by_sector(client: AsyncClient) -> None:
    sector = await client.post(
        SECTORS_BASE + "/", json={"name": "RiskTestSector", "nace_code": "RT-RISK"}
    )
    sector_id = sector.json()["id"]

    r1 = await client.post(
        BASE + "/",
        json={"title": "R1", "description": "D", "sector_id": sector_id},
    )
    r2 = await client.post(
        BASE + "/",
        json={"title": "R2", "description": "D", "sector_id": sector_id},
    )
    r3 = await client.post(
        BASE + "/",
        json={"title": "R3", "description": "D", "sector_id": "other"},
    )

    response = await client.get(BASE + "/", params={"sector_id": sector_id})
    assert response.status_code == 200
    assert len(response.json()) == 2

    for rid in [r1.json()["id"], r2.json()["id"], r3.json()["id"]]:
        await client.delete(f"{BASE}/{rid}")
    await client.delete(f"{SECTORS_BASE}/{sector_id}")


async def test_get_risk_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/does-not-exist")
    assert response.status_code == 404


async def test_probability_out_of_range(client: AsyncClient) -> None:
    response = await client.post(
        BASE + "/",
        json={"title": "T", "description": "D", "probability": 1.5},
    )
    assert response.status_code == 422
