import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

BASE = "/api/v1/corrective-action-plans"
FINDINGS_BASE = "/api/v1/findings"
ASSESSMENTS_BASE = "/api/v1/assessments"


async def _create_finding(client: AsyncClient) -> dict:
    assessment = await client.post(
        ASSESSMENTS_BASE + "/",
        json={"title": "CAP Test Assessment", "description": "Used for CAP tests"},
    )
    assert assessment.status_code == 201
    assessment_id = assessment.json()["id"]

    finding = await client.post(
        FINDINGS_BASE + "/",
        json={
            "title": "CAP Test Finding",
            "description": "Finding for CAP test",
            "severity": "High",
            "assessment_id": assessment_id,
        },
    )
    assert finding.status_code == 201
    return {"finding": finding.json(), "assessment_id": assessment_id}


async def test_create_cap(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    response = await client.post(
        BASE + "/",
        json={
            "finding_id": finding_id,
            "title": "Audit supplier labour practices",
            "description": "Conduct full audit within 90 days",
            "responsible_party": "Compliance Team",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Audit supplier labour practices"
    assert data["cap_status"] == "DRAFT"
    assert data["finding_id"] == finding_id
    assert data["is_overdue"] is False

    await client.delete(f"{BASE}/{data['id']}")


async def test_create_cap_duplicate_finding_rejected(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    r1 = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "CAP 1", "description": "First CAP"},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "CAP 2", "description": "Duplicate"},
    )
    assert r2.status_code == 409

    await client.delete(f"{BASE}/{r1.json()['id']}")


async def test_get_cap_by_id(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    created = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "Get by ID test", "description": "Detail test"},
    )
    cap_id = created.json()["id"]

    response = await client.get(f"{BASE}/{cap_id}")
    assert response.status_code == 200
    assert response.json()["id"] == cap_id

    await client.delete(f"{BASE}/{cap_id}")


async def test_get_cap_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/does-not-exist")
    assert response.status_code == 404


async def test_get_cap_by_finding(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    cap = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "By-finding test", "description": "Test"},
    )
    cap_id = cap.json()["id"]

    response = await client.get(f"{BASE}/by-finding/{finding_id}")
    assert response.status_code == 200
    assert response.json()["finding_id"] == finding_id

    await client.delete(f"{BASE}/{cap_id}")


async def test_cap_lifecycle_commit_and_start(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    cap = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "Lifecycle test", "description": "Full lifecycle"},
    )
    cap_id = cap.json()["id"]
    assert cap.json()["cap_status"] == "DRAFT"

    commit = await client.patch(f"{BASE}/{cap_id}/commit")
    assert commit.status_code == 200
    assert commit.json()["cap_status"] == "COMMITTED"

    start = await client.patch(f"{BASE}/{cap_id}/start")
    assert start.status_code == 200
    assert start.json()["cap_status"] == "IN_PROGRESS"

    await client.delete(f"{BASE}/{cap_id}")


async def test_cap_submit_evidence(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    cap = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "Evidence test", "description": "Evidence submission"},
    )
    cap_id = cap.json()["id"]

    await client.patch(f"{BASE}/{cap_id}/commit")
    await client.patch(f"{BASE}/{cap_id}/start")

    evidence = await client.patch(
        f"{BASE}/{cap_id}/submit-evidence",
        json={"evidence_note": "Completed supplier audit, all findings addressed"},
    )
    assert evidence.status_code == 200
    assert evidence.json()["cap_status"] == "EVIDENCE_SUBMITTED"
    assert "supplier audit" in evidence.json()["evidence_note"]

    await client.delete(f"{BASE}/{cap_id}")


async def test_cap_kpis(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/kpis")
    assert response.status_code == 200
    kpis = response.json()
    assert "total" in kpis
    assert "open" in kpis
    assert "overdue" in kpis
    assert "verified" in kpis
    assert "closed" in kpis
    assert "completion_rate" in kpis


async def test_cap_list_org_scoped(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    cap = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "List test CAP", "description": "For list test"},
    )
    cap_id = cap.json()["id"]

    response = await client.get(f"{BASE}/")
    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert cap_id in ids

    await client.delete(f"{BASE}/{cap_id}")


async def test_cap_list_filter_by_status(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    cap = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "Draft filter test", "description": "Status filter"},
    )
    cap_id = cap.json()["id"]

    response = await client.get(f"{BASE}/", params={"cap_status": "DRAFT"})
    assert response.status_code == 200
    statuses = {c["cap_status"] for c in response.json()}
    assert statuses <= {"DRAFT"}

    await client.delete(f"{BASE}/{cap_id}")


async def test_cap_invalid_status_transition(client: AsyncClient) -> None:
    ctx = await _create_finding(client)
    finding_id = ctx["finding"]["id"]

    cap = await client.post(
        BASE + "/",
        json={"finding_id": finding_id, "title": "Invalid transition", "description": "Test"},
    )
    cap_id = cap.json()["id"]

    # Cannot submit evidence from DRAFT (must be IN_PROGRESS first)
    response = await client.patch(
        f"{BASE}/{cap_id}/submit-evidence",
        json={"evidence_note": "Should fail"},
    )
    assert response.status_code == 400

    await client.delete(f"{BASE}/{cap_id}")
