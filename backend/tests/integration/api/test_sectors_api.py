import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

BASE = "/api/v1/sectors"


async def test_create_sector(client: AsyncClient) -> None:
    response = await client.post(
        BASE + "/",
        json={"name": "Mining", "nace_code": "B", "nace_description": "Mining and quarrying"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Mining"
    assert data["nace_code"] == "B"
    assert "id" in data
    assert data["status"] == "Draft"

    # cleanup
    await client.delete(f"{BASE}/{data['id']}")


async def test_get_sector_by_id(client: AsyncClient) -> None:
    create = await client.post(BASE + "/", json={"name": "Agriculture", "nace_code": "A"})
    assert create.status_code == 201
    sector_id = create.json()["id"]

    response = await client.get(f"{BASE}/{sector_id}")
    assert response.status_code == 200
    assert response.json()["nace_code"] == "A"

    await client.delete(f"{BASE}/{sector_id}")


async def test_get_sector_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/does-not-exist")
    assert response.status_code == 404


async def test_get_sector_by_nace_code(client: AsyncClient) -> None:
    create = await client.post(BASE + "/", json={"name": "Construction", "nace_code": "F-TEST"})
    sector_id = create.json()["id"]

    response = await client.get(f"{BASE}/nace/F-TEST")
    assert response.status_code == 200
    assert response.json()["name"] == "Construction"

    await client.delete(f"{BASE}/{sector_id}")


async def test_get_sector_by_nace_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/nace/DOES-NOT-EXIST")
    assert response.status_code == 404


async def test_list_sector_children(client: AsyncClient) -> None:
    parent = await client.post(BASE + "/", json={"name": "Industry", "nace_code": "C-PARENT"})
    parent_id = parent.json()["id"]

    child1 = await client.post(
        BASE + "/",
        json={"name": "Metal", "nace_code": "C24", "parent_sector_id": parent_id},
    )
    child2 = await client.post(
        BASE + "/",
        json={"name": "Chemicals", "nace_code": "C20", "parent_sector_id": parent_id},
    )

    response = await client.get(f"{BASE}/{parent_id}/children")
    assert response.status_code == 200
    assert len(response.json()) == 2

    for child in [child1.json()["id"], child2.json()["id"]]:
        await client.delete(f"{BASE}/{child}")
    await client.delete(f"{BASE}/{parent_id}")


async def test_delete_sector(client: AsyncClient) -> None:
    create = await client.post(BASE + "/", json={"name": "Energy", "nace_code": "D-DEL"})
    sector_id = create.json()["id"]

    response = await client.delete(f"{BASE}/{sector_id}")
    assert response.status_code == 204

    get = await client.get(f"{BASE}/{sector_id}")
    assert get.status_code == 404


async def test_delete_sector_not_found(client: AsyncClient) -> None:
    response = await client.delete(f"{BASE}/does-not-exist")
    assert response.status_code == 404


async def test_create_sector_missing_required_fields(client: AsyncClient) -> None:
    response = await client.post(BASE + "/", json={"name": "Missing NACE"})
    assert response.status_code == 422
