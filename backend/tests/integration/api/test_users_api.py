"""
Integration tests for /api/v1/users endpoints (M23).

Guard logic recap:
  other_active_admins = active admins in org  excluding  target AND actor
  if other_active_admins == 0 → 400 (last-admin guard fires)

This means:
  • 2 active admins  — neither can demote/deactivate the other (0 others left)
  • 3 active admins  — any one can modify another      (1 other left)
  • self-mod always blocked regardless of count         (400 "cannot modify own account")
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from shared.rate_limit import reset_for_tests

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_schema(setup_test_schema: None) -> None:  # type: ignore[misc]
    """Ensure schema is ready before any test in this module."""


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    """Clear in-process rate-limit windows before every test."""
    reset_for_tests()

AUTH = "/api/v1/auth"
USERS = "/api/v1/users"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_admin(email: str, org: str) -> tuple[str, str]:
    """Register a fresh admin in a new org. Returns (token, user_id)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AUTH + "/register",
            json={
                "email": email,
                "display_name": email.split("@")[0],
                "password": "secure-password-123",
                "role": "admin",
                "organization_name": org,
            },
        )
    assert r.status_code == 201, r.text
    return r.json()["access_token"], r.json()["user"]["id"]


async def _invite(token: str, email: str, role: str = "analyst") -> tuple[str, str]:
    """Invite a user via admin token. Returns (user_id, temp_password)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.post(
            USERS + "/invite",
            json={"email": email, "display_name": email.split("@")[0], "role": role},
        )
    assert r.status_code == 201, r.text
    return r.json()["user"]["id"], r.json()["temp_password"]


async def _login(email: str, password: str) -> str:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(AUTH + "/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _patch(token: str, user_id: str, payload: dict) -> tuple[int, dict]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.patch(USERS + f"/{user_id}", json=payload)
    return r.status_code, r.json()


# ---------------------------------------------------------------------------
# Last-admin guard: demotion
# ---------------------------------------------------------------------------

async def test_two_admins_neither_can_demote_the_other(setup_test_schema: None) -> None:
    """
    Org has exactly 2 active admins (A, B).
    other_active_admins (excl. actor + target) = 0 → guard fires → 400.
    """
    token_a, id_a = await _register_admin("lad-demote-a@eios.dev", "Org LadDemoteAB")
    id_b, pw_b = await _invite(token_a, "lad-demote-b@eios.dev", "admin")
    token_b = await _login("lad-demote-b@eios.dev", pw_b)

    # A tries to demote B → 0 others remain → 400
    code, body = await _patch(token_a, id_b, {"role": "analyst"})
    assert code == 400, body
    assert "last active admin" in body["detail"]

    # B tries to demote A → 0 others remain → 400
    code, body = await _patch(token_b, id_a, {"role": "analyst"})
    assert code == 400, body
    assert "last active admin" in body["detail"]


async def test_three_admins_one_can_demote_another(setup_test_schema: None) -> None:
    """
    Org has 3 active admins (A, B, C).
    other_active_admins (excl. actor + target) = 1 → guard does NOT fire → 200.
    """
    token_a, id_a = await _register_admin("lad-three-a@eios.dev", "Org LadThree")
    id_b, pw_b = await _invite(token_a, "lad-three-b@eios.dev", "admin")
    id_c, pw_c = await _invite(token_a, "lad-three-c@eios.dev", "admin")

    # A demotes B → C remains as other admin → should succeed
    code, body = await _patch(token_a, id_b, {"role": "analyst"})
    assert code == 200, body
    assert body["role"] == "analyst"


# ---------------------------------------------------------------------------
# Last-admin guard: deactivation
# ---------------------------------------------------------------------------

async def test_two_admins_neither_can_deactivate_the_other(setup_test_schema: None) -> None:
    """
    Org has exactly 2 active admins. Deactivating either one fires the guard.
    """
    token_a, id_a = await _register_admin("lad-deact-a@eios.dev", "Org LadDeactAB")
    id_b, pw_b = await _invite(token_a, "lad-deact-b@eios.dev", "admin")
    token_b = await _login("lad-deact-b@eios.dev", pw_b)

    # A tries to deactivate B → 400
    code, body = await _patch(token_a, id_b, {"is_active": False})
    assert code == 400, body
    assert "last active admin" in body["detail"]

    # B tries to deactivate A → 400
    code, body = await _patch(token_b, id_a, {"is_active": False})
    assert code == 400, body
    assert "last active admin" in body["detail"]


async def test_three_admins_one_can_deactivate_another(setup_test_schema: None) -> None:
    """
    Org has 3 active admins. Deactivating one is allowed (1 other remains).
    """
    token_a, _ = await _register_admin("lad-deact3-a@eios.dev", "Org LadDeact3")
    id_b, _ = await _invite(token_a, "lad-deact3-b@eios.dev", "admin")
    id_c, _ = await _invite(token_a, "lad-deact3-c@eios.dev", "admin")

    code, body = await _patch(token_a, id_b, {"is_active": False})
    assert code == 200, body
    assert body["is_active"] is False


# ---------------------------------------------------------------------------
# Guard does not fire for non-admin targets
# ---------------------------------------------------------------------------

async def test_deactivating_non_admin_always_allowed(setup_test_schema: None) -> None:
    """
    Deactivating an analyst (not admin) never triggers the last-admin guard.
    """
    token_a, _ = await _register_admin("lad-analyst-a@eios.dev", "Org LadAnalyst")
    id_b, _ = await _invite(token_a, "lad-analyst-b@eios.dev", "analyst")

    code, body = await _patch(token_a, id_b, {"is_active": False})
    assert code == 200, body
    assert body["is_active"] is False


async def test_demoting_inactive_admin_always_allowed(setup_test_schema: None) -> None:
    """
    Demoting an already-inactive admin doesn't count as removing an active admin
    (will_lose_admin requires target.is_active = True).
    """
    token_a, _ = await _register_admin("lad-inactive-a@eios.dev", "Org LadInactive")
    id_b, pw_b = await _invite(token_a, "lad-inactive-b@eios.dev", "admin")
    id_c, _ = await _invite(token_a, "lad-inactive-c@eios.dev", "admin")

    # 3 admins → deactivate B (allowed, C remains)
    await _patch(token_a, id_b, {"is_active": False})

    # Now 2 active admins (A, C). B is inactive.
    # Demoting inactive B → will_lose_admin is False (target.is_active = False) → allowed
    code, body = await _patch(token_a, id_b, {"role": "analyst"})
    assert code == 200, body
    assert body["role"] == "analyst"


# ---------------------------------------------------------------------------
# Self-modification guard
# ---------------------------------------------------------------------------

async def test_admin_cannot_modify_own_account(setup_test_schema: None) -> None:
    """Self-modification is blocked regardless of admin count."""
    token_a, id_a = await _register_admin("self-mod-a@eios.dev", "Org SelfMod")
    id_b, _ = await _invite(token_a, "self-mod-b@eios.dev", "admin")

    # A tries to demote themselves → 400 (self-mod guard, not last-admin guard)
    code, body = await _patch(token_a, id_a, {"role": "analyst"})
    assert code == 400, body
    assert "Cannot modify your own account" in body["detail"]


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------

async def test_admin_cannot_modify_user_in_other_org(setup_test_schema: None) -> None:
    """Admin from Org X cannot PATCH a user in Org Y → 404."""
    token_x, _ = await _register_admin("iso-x@eios.dev", "Org Iso X")
    token_y, id_y = await _register_admin("iso-y@eios.dev", "Org Iso Y")

    code, body = await _patch(token_x, id_y, {"role": "analyst"})
    assert code == 404, body


async def test_list_users_only_returns_own_org(setup_test_schema: None) -> None:
    """GET /users/ only returns users in the authenticated admin's org."""
    token_x, _ = await _register_admin("list-x@eios.dev", "Org List X")
    _, id_y = await _register_admin("list-y@eios.dev", "Org List Y")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_x}"},
    ) as c:
        r = await c.get(USERS + "/")
    assert r.status_code == 200
    ids = {u["id"] for u in r.json()}
    assert id_y not in ids


# ---------------------------------------------------------------------------
# Invite flow
# ---------------------------------------------------------------------------

async def test_invite_returns_usable_temp_password(setup_test_schema: None) -> None:
    """Invited user can log in with the temp_password returned once at invite time."""
    token_a, _ = await _register_admin("inv-admin-m23@eios.dev", "Org InviteM23")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_a}"},
    ) as c:
        r = await c.post(
            USERS + "/invite",
            json={"email": "inv-member-m23@eios.dev", "display_name": "Member", "role": "analyst"},
        )
    assert r.status_code == 201
    data = r.json()
    assert len(data["temp_password"]) >= 12
    assert "password_hash" not in data["user"]

    login = await _login("inv-member-m23@eios.dev", data["temp_password"])
    assert login  # non-empty token


async def test_invite_duplicate_email_returns_409(setup_test_schema: None) -> None:
    token_a, _ = await _register_admin("inv-dup-m23@eios.dev", "Org InviteDup")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_a}"},
    ) as c:
        payload = {"email": "dup-m23@eios.dev", "display_name": "Dup", "role": "analyst"}
        await c.post(USERS + "/invite", json=payload)
        r = await c.post(USERS + "/invite", json=payload)
    assert r.status_code == 409


async def test_non_admin_cannot_call_users_endpoints(setup_test_schema: None) -> None:
    """Analyst-role users get 403 on all /users/ management endpoints."""
    token_a, _ = await _register_admin("nonadmin-owner@eios.dev", "Org NonAdmin")
    id_b, pw_b = await _invite(token_a, "nonadmin-member@eios.dev", "analyst")
    token_b = await _login("nonadmin-member@eios.dev", pw_b)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_b}"},
    ) as c:
        assert (await c.get(USERS + "/")).status_code == 403
        assert (
            await c.patch(USERS + f"/{id_b}", json={"role": "admin"})
        ).status_code == 403
        assert (
            await c.post(
                USERS + "/invite",
                json={"email": "x@x.com", "display_name": "x", "role": "analyst"},
            )
        ).status_code == 403
