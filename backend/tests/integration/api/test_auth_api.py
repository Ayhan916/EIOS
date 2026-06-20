import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.integration

BASE = "/api/v1/auth"

_DEFAULT_ORG = "EIOS Test Org"


async def test_register_new_user(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post(
            BASE + "/register",
            json={
                "email": "newuser@eios.dev",
                "display_name": "New User",
                "password": "secure-password-123",
                "organization_name": _DEFAULT_ORG,
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@eios.dev"
    assert "password_hash" not in data["user"]


async def test_register_duplicate_email_returns_409(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            BASE + "/register",
            json={
                "email": "dup@eios.dev",
                "display_name": "Dup User",
                "password": "secure-password-123",
                "organization_name": _DEFAULT_ORG,
            },
        )
        response = await c.post(
            BASE + "/register",
            json={
                "email": "dup@eios.dev",
                "display_name": "Dup User",
                "password": "secure-password-123",
                "organization_name": _DEFAULT_ORG,
            },
        )
    assert response.status_code == 409


async def test_register_weak_password_returns_422(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post(
            BASE + "/register",
            json={
                "email": "weak@eios.dev",
                "display_name": "W",
                "password": "short",
                "organization_name": _DEFAULT_ORG,
            },
        )
    assert response.status_code == 422


async def test_login_valid_credentials(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            BASE + "/register",
            json={
                "email": "login@eios.dev",
                "display_name": "Login User",
                "password": "my-login-password",
                "organization_name": _DEFAULT_ORG,
            },
        )
        response = await c.post(
            BASE + "/login",
            json={"email": "login@eios.dev", "password": "my-login-password"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "login@eios.dev"


async def test_login_wrong_password_returns_401(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            BASE + "/register",
            json={
                "email": "wrongpw@eios.dev",
                "display_name": "W",
                "password": "correct-password",
                "organization_name": _DEFAULT_ORG,
            },
        )
        response = await c.post(
            BASE + "/login",
            json={"email": "wrongpw@eios.dev", "password": "wrong-password"},
        )
    assert response.status_code == 401


async def test_login_unknown_email_returns_401(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post(
            BASE + "/login",
            json={"email": "nobody@eios.dev", "password": "whatever"},
        )
    assert response.status_code == 401


async def test_get_me_with_valid_token(client: AsyncClient) -> None:
    response = await client.get(BASE + "/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@eios.dev"
    assert "password_hash" not in data


async def test_get_me_without_token_returns_401(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get(BASE + "/me")
    assert response.status_code == 401


async def test_protected_route_without_token_returns_401(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/api/v1/sectors/some-id")
    assert response.status_code == 401


async def test_protected_route_with_invalid_token_returns_401(setup_test_schema: None) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer not-a-valid-token"},
    ) as c:
        response = await c.get("/api/v1/sectors/some-id")
    assert response.status_code == 401


async def test_token_refresh(setup_test_schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        reg = await c.post(
            BASE + "/register",
            json={
                "email": "refresh@eios.dev",
                "display_name": "R",
                "password": "refresh-password-ok",
                "organization_name": _DEFAULT_ORG,
            },
        )
        if reg.status_code == 409:
            reg = await c.post(
                BASE + "/login",
                json={"email": "refresh@eios.dev", "password": "refresh-password-ok"},
            )
        refresh_token = reg.json()["refresh_token"]

        response = await c.post(BASE + "/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
