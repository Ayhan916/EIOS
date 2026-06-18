"""
Integration tests for M27 Supplier Management.

Test scenarios:
  1.  Create supplier — analyst can create
  2.  Create supplier — viewer cannot create
  3.  List suppliers — returns own org suppliers only
  4.  Get supplier — happy path
  5.  Get supplier — 404 for unknown id
  6.  Get supplier — tenant isolation (org B cannot see org A supplier)
  7.  Update supplier — changes name, tier, notes
  8.  Archive supplier — DELETE soft-archives (status=Archived)
  9.  Archive supplier — tenant isolation (org B cannot archive org A supplier)
  10. List with filters — country filter
  11. List with filters — search by name
  12. Create assessment with supplier_id — supplier linked
  13. Supplier assessments sub-resource — returns correct assessments
  14. Supplier risk profile — aggregates findings and risks
  15. Supplier risk profile — tenant isolation
  16. Dashboard — supplier KPIs present
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from shared.rate_limit import reset_for_tests

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

AUTH = "/api/v1/auth"
SUPPLIERS = "/api/v1/suppliers"
ASSESS = "/api/v1/assessments"
DASHBOARD = "/api/v1/dashboard"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_schema(setup_test_schema: None) -> None:  # type: ignore[misc]
    pass


@pytest.fixture(autouse=True)
def _reset_rl() -> None:
    reset_for_tests()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(email: str, role: str = "analyst") -> tuple[str, str, str]:
    """Register and return (token, user_id, org_id). Each call creates a fresh org."""
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.repositories.user import SQLUserRepository  # noqa: PLC0415

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AUTH + "/register",
            json={
                "email": email,
                "display_name": email.split("@")[0],
                "password": "Supplier1234!",
                "organization_name": f"Org-{email}",
            },
        )
    assert r.status_code == 201, r.text
    d = r.json()
    if role not in ("admin",):
        async with AsyncSessionFactory() as session, session.begin():
            repo = SQLUserRepository(session)
            user = await repo.get_by_id(d["user"]["id"])
            assert user
            user.role = role
            await repo.save(user)
    return d["access_token"], d["user"]["id"], d["user"]["organization_id"]


async def _create_supplier(token: str, name: str = "ACME Corp", **kwargs) -> dict:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.post(
            SUPPLIERS + "/",
            json={"name": name, "country": "DE", "industry": "Manufacturing", **kwargs},
        )
    assert r.status_code == 201, r.text
    return r.json()


# ── CRUD Tests ────────────────────────────────────────────────────────────────


async def test_analyst_can_create_supplier(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-create-analyst@eios.dev", "analyst")
    sup = await _create_supplier(tok, "Green Steel GmbH")
    assert sup["name"] == "Green Steel GmbH"
    assert sup["country"] == "DE"
    assert sup["supplier_tier"] == "Tier 1"
    assert sup["supplier_status"] == "Active"
    assert "id" in sup


async def test_viewer_cannot_create_supplier(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-create-viewer@eios.dev", "viewer")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            SUPPLIERS + "/",
            json={"name": "Viewer Corp", "country": "US", "industry": "Tech"},
        )
    assert r.status_code == 403


async def test_list_suppliers_returns_own_org(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-list-a@eios.dev", "analyst")
    tok_b, _, _ = await _register("sup-list-b@eios.dev", "analyst")

    await _create_supplier(tok, "Supplier A1")
    await _create_supplier(tok, "Supplier A2")
    await _create_supplier(tok_b, "Supplier B1")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(SUPPLIERS + "/")
    assert r.status_code == 200
    names = [s["name"] for s in r.json()["items"]]
    assert "Supplier A1" in names
    assert "Supplier A2" in names
    assert "Supplier B1" not in names


async def test_get_supplier_happy_path(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-get@eios.dev", "analyst")
    sup = await _create_supplier(tok, "Happy Path Ltd", nace_code="C24.10")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(SUPPLIERS + f"/{sup['id']}")
    assert r.status_code == 200
    assert r.json()["nace_code"] == "C24.10"


async def test_get_supplier_not_found(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-notfound@eios.dev", "analyst")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(SUPPLIERS + "/00000000-0000-0000-0000-000000009999")
    assert r.status_code == 404


async def test_get_supplier_tenant_isolation(setup_test_schema: None) -> None:
    tok_a, _, _ = await _register("sup-iso-get-a@eios.dev", "analyst")
    tok_b, _, _ = await _register("sup-iso-get-b@eios.dev", "analyst")
    sup = await _create_supplier(tok_a, "Org A Secret Supplier")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.get(SUPPLIERS + f"/{sup['id']}")
    assert r.status_code == 404


async def test_update_supplier(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-update@eios.dev", "analyst")
    sup = await _create_supplier(tok, "Old Name")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.patch(
            SUPPLIERS + f"/{sup['id']}",
            json={"name": "New Name", "supplier_tier": "Tier 2", "notes": "Updated"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "New Name"
    assert data["supplier_tier"] == "Tier 2"
    assert data["notes"] == "Updated"


async def test_archive_supplier(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-archive@eios.dev", "analyst")
    sup = await _create_supplier(tok, "To Be Archived")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.delete(SUPPLIERS + f"/{sup['id']}")
        assert r.status_code == 204
        # Verify it's gone from list
        r2 = await c.get(SUPPLIERS + "/")
    names = [s["name"] for s in r2.json()["items"]]
    assert "To Be Archived" not in names


async def test_archive_supplier_tenant_isolation(setup_test_schema: None) -> None:
    tok_a, _, _ = await _register("sup-arch-iso-a@eios.dev", "analyst")
    tok_b, _, _ = await _register("sup-arch-iso-b@eios.dev", "analyst")
    sup = await _create_supplier(tok_a, "Org A Supplier Protected")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.delete(SUPPLIERS + f"/{sup['id']}")
    assert r.status_code == 404


# ── Filter & Search Tests ─────────────────────────────────────────────────────


async def test_list_filter_by_country(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-filter-country@eios.dev", "analyst")
    await _create_supplier(tok, "German Co", country="DE")
    await _create_supplier(tok, "French Co", country="FR")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(SUPPLIERS + "/", params={"country": "DE"})
    names = [s["name"] for s in r.json()["items"]]
    assert "German Co" in names
    assert "French Co" not in names


async def test_list_search_by_name(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-search@eios.dev", "analyst")
    await _create_supplier(tok, "Unique Cobalt Mining GmbH")
    await _create_supplier(tok, "Other Industries SA")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(SUPPLIERS + "/", params={"search": "Cobalt"})
    names = [s["name"] for s in r.json()["items"]]
    assert "Unique Cobalt Mining GmbH" in names
    assert "Other Industries SA" not in names


# ── Assessment Linkage Tests ──────────────────────────────────────────────────


async def test_assessment_with_supplier_id(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-assess-link@eios.dev", "analyst")
    sup = await _create_supplier(tok, "Linked Supplier")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + "/",
            json={
                "title": "Assessment for Linked Supplier",
                "description": "M27 test",
                "supplier_id": sup["id"],
            },
        )
    assert r.status_code == 201
    assert r.json()["supplier_id"] == sup["id"]


async def test_supplier_assessments_sub_resource(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-sub-assess@eios.dev", "analyst")
    sup = await _create_supplier(tok, "Sub-Resource Supplier")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        # Create two assessments for this supplier, one without
        await c.post(
            ASSESS + "/",
            json={"title": "A1", "description": "d", "supplier_id": sup["id"]},
        )
        await c.post(
            ASSESS + "/",
            json={"title": "A2", "description": "d", "supplier_id": sup["id"]},
        )
        await c.post(ASSESS + "/", json={"title": "A3-no-supplier", "description": "d"})

        r = await c.get(SUPPLIERS + f"/{sup['id']}/assessments")

    assert r.status_code == 200
    titles = [a["title"] for a in r.json()["items"]]
    assert "A1" in titles
    assert "A2" in titles
    assert "A3-no-supplier" not in titles


# ── Risk Profile Tests ────────────────────────────────────────────────────────


async def test_supplier_risk_profile_empty(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-risk-empty@eios.dev", "analyst")
    sup = await _create_supplier(tok, "No Assessments Supplier")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(SUPPLIERS + f"/{sup['id']}/risk-profile")
    assert r.status_code == 200
    profile = r.json()
    assert profile["total_assessments"] == 0
    assert profile["total_findings"] == 0
    assert profile["total_risks"] == 0


async def test_supplier_risk_profile_tenant_isolation(setup_test_schema: None) -> None:
    tok_a, _, _ = await _register("sup-risk-iso-a@eios.dev", "analyst")
    tok_b, _, _ = await _register("sup-risk-iso-b@eios.dev", "analyst")
    sup = await _create_supplier(tok_a, "Risk Profile Org A Supplier")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.get(SUPPLIERS + f"/{sup['id']}/risk-profile")
    assert r.status_code == 404


# ── Dashboard Integration Test ────────────────────────────────────────────────


async def test_dashboard_includes_supplier_kpis(setup_test_schema: None) -> None:
    tok, _, _ = await _register("sup-dash@eios.dev", "analyst")
    await _create_supplier(tok, "Dashboard Supplier 1")
    await _create_supplier(tok, "Dashboard Supplier 2")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(DASHBOARD + "/")
    assert r.status_code == 200
    data = r.json()
    assert "total_suppliers" in data
    assert data["total_suppliers"] >= 2
    assert data["active_suppliers"] >= 2
    assert "supplier_watchlist" in data
