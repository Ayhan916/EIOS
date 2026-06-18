"""
Integration tests for M27.1 Supplier Hardening.

Test scenarios:
  1.  Duplicate supplier name in same org → rejected (422)
  2.  Duplicate supplier name across orgs → allowed (201)
  3.  Assessment creation for archived supplier → rejected (422)
  4.  Assessment creation for active supplier → allowed (201)
  5.  Assessment creation for inactive (not yet archived) supplier → rejected (422)
  6.  Assessment creation with non-existent supplier_id → rejected (422)
  7.  Assessment creation without supplier_id → allowed (201, supplier_id=None)
  8.  Assessment creation for supplier belonging to another org → rejected (422)
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


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_schema(setup_test_schema: None) -> None:  # type: ignore[misc]
    pass


@pytest.fixture(autouse=True)
def _reset_rl() -> None:
    reset_for_tests()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(email: str, role: str = "analyst") -> tuple[str, str, str]:
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.repositories.user import SQLUserRepository  # noqa: PLC0415

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AUTH + "/register",
            json={
                "email": email,
                "display_name": email.split("@")[0],
                "password": "Harden1234!",
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


async def _create_supplier(token: str, name: str, **kwargs) -> dict:
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


async def _archive_supplier(token: str, supplier_id: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.delete(SUPPLIERS + f"/{supplier_id}")
    assert r.status_code == 204, r.text


async def _set_supplier_inactive(supplier_id: str) -> None:
    """Directly set supplier_status to Inactive without archiving, to test inactive guard."""
    from domain.enums import SupplierStatus  # noqa: PLC0415
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.repositories.supplier import SQLSupplierRepository  # noqa: PLC0415

    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLSupplierRepository(session)
        supplier = await repo.get_by_id(supplier_id)
        assert supplier
        supplier.supplier_status = SupplierStatus.INACTIVE
        await repo.save(supplier)


# ── Supplier Name Uniqueness ──────────────────────────────────────────────────


async def test_duplicate_name_same_org_rejected(setup_test_schema: None) -> None:
    """Creating two suppliers with the same name in the same org must return 422."""
    tok, _, _ = await _register("hard-dup-a@eios.dev", "analyst")
    await _create_supplier(tok, "Steel Corp GmbH")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            SUPPLIERS + "/",
            json={"name": "Steel Corp GmbH", "country": "DE", "industry": "Steel"},
        )

    assert r.status_code == 422, r.text
    assert "already exists" in r.json()["detail"].lower()


async def test_duplicate_name_across_orgs_allowed(setup_test_schema: None) -> None:
    """Same supplier name in two different organizations must be allowed."""
    tok_a, _, _ = await _register("hard-cross-a@eios.dev", "analyst")
    tok_b, _, _ = await _register("hard-cross-b@eios.dev", "analyst")

    sup_a = await _create_supplier(tok_a, "Global Timber AG")
    assert sup_a["name"] == "Global Timber AG"

    # Org B creates a supplier with the identical name — must succeed
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.post(
            SUPPLIERS + "/",
            json={"name": "Global Timber AG", "country": "CH", "industry": "Forestry"},
        )

    assert r.status_code == 201, r.text
    assert r.json()["name"] == "Global Timber AG"
    # Different org → different tenant → different supplier ID
    assert r.json()["id"] != sup_a["id"]


async def test_update_to_duplicate_name_rejected(setup_test_schema: None) -> None:
    """PATCH that renames a supplier to a name already taken in the same org must return 422."""
    tok, _, _ = await _register("hard-upd-dup@eios.dev", "analyst")
    await _create_supplier(tok, "Alpha Supplier")
    sup_b = await _create_supplier(tok, "Beta Supplier")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.patch(
            SUPPLIERS + f"/{sup_b['id']}",
            json={"name": "Alpha Supplier"},
        )

    assert r.status_code == 422, r.text
    assert "already exists" in r.json()["detail"].lower()


# ── Active Supplier Validation ────────────────────────────────────────────────


async def test_assessment_for_active_supplier_allowed(setup_test_schema: None) -> None:
    """Assessment creation with an active supplier_id must succeed."""
    tok, _, _ = await _register("hard-active-ok@eios.dev", "analyst")
    sup = await _create_supplier(tok, "Active Supplier For Assessment")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + "/",
            json={
                "title": "Assessment for Active Supplier",
                "description": "M27.1 test",
                "supplier_id": sup["id"],
            },
        )

    assert r.status_code == 201, r.text
    assert r.json()["supplier_id"] == sup["id"]


async def test_assessment_for_archived_supplier_rejected(setup_test_schema: None) -> None:
    """Assessment creation for an archived supplier must return 422."""
    tok, _, _ = await _register("hard-arch-rej@eios.dev", "analyst")
    sup = await _create_supplier(tok, "Archived Supplier")
    await _archive_supplier(tok, sup["id"])

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + "/",
            json={
                "title": "Should Fail",
                "description": "Archived supplier",
                "supplier_id": sup["id"],
            },
        )

    assert r.status_code == 422, r.text
    detail = r.json()["detail"].lower()
    assert "inactive" in detail or "archived" in detail or "cannot" in detail


async def test_assessment_for_inactive_supplier_rejected(setup_test_schema: None) -> None:
    """Assessment creation for a supplier with status Inactive must return 422."""
    tok, _, _ = await _register("hard-inact-rej@eios.dev", "analyst")
    sup = await _create_supplier(tok, "Inactive Supplier For Test")
    await _set_supplier_inactive(sup["id"])

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + "/",
            json={
                "title": "Should Fail",
                "description": "Inactive supplier",
                "supplier_id": sup["id"],
            },
        )

    assert r.status_code == 422, r.text
    assert "inactive" in r.json()["detail"].lower()


async def test_assessment_for_nonexistent_supplier_rejected(setup_test_schema: None) -> None:
    """Assessment creation with a non-existent supplier_id must return 422."""
    tok, _, _ = await _register("hard-noexist@eios.dev", "analyst")
    fake_id = "00000000-0000-0000-0000-000000000042"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + "/",
            json={"title": "Should Fail", "description": "d", "supplier_id": fake_id},
        )

    assert r.status_code == 422, r.text
    assert "not found" in r.json()["detail"].lower()


async def test_assessment_without_supplier_id_allowed(setup_test_schema: None) -> None:
    """Assessment creation without supplier_id must succeed (supplier_id remains None)."""
    tok, _, _ = await _register("hard-no-sup@eios.dev", "analyst")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + "/",
            json={"title": "No Supplier Assessment", "description": "d"},
        )

    assert r.status_code == 201, r.text
    assert r.json()["supplier_id"] is None


async def test_assessment_for_cross_tenant_supplier_rejected(setup_test_schema: None) -> None:
    """Assessment creation using another org's supplier_id must return 422 (not 404)."""
    tok_a, _, _ = await _register("hard-cross-sup-a@eios.dev", "analyst")
    tok_b, _, _ = await _register("hard-cross-sup-b@eios.dev", "analyst")
    sup_a = await _create_supplier(tok_a, "Org A Supplier")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.post(
            ASSESS + "/",
            json={
                "title": "Cross-Tenant Assessment",
                "description": "d",
                "supplier_id": sup_a["id"],
            },
        )

    assert r.status_code == 422, r.text
    assert "not found" in r.json()["detail"].lower()
