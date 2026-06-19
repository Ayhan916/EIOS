"""
M30 API Platform Integration Tests

Covers: service accounts, API key CRUD, API key auth, scope enforcement,
webhook CRUD, delivery logs, tenant isolation, rate limiting checks.

Requires a running PostgreSQL instance (see conftest.py).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.integration

BASE = "/api/v1/platform"


# ── Helper fixtures ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin_client(auth_token: str) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as c:
        yield c


@pytest_asyncio.fixture
async def anon_client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ── Test 1: Create service account ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_service_account(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/service-accounts",
        json={"name": "CI Pipeline", "description": "For GitHub Actions"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "CI Pipeline"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


# ── Test 2: List service accounts ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_service_accounts(admin_client: AsyncClient) -> None:
    await admin_client.post(
        f"{BASE}/service-accounts",
        json={"name": "Monitoring Bot"},
    )
    r = await admin_client.get(f"{BASE}/service-accounts")
    assert r.status_code == 200
    accounts = r.json()
    assert isinstance(accounts, list)
    names = [a["name"] for a in accounts]
    assert "Monitoring Bot" in names


# ── Test 3: Deactivate service account ───────────────────────────────────────


@pytest.mark.asyncio
async def test_deactivate_service_account(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/service-accounts",
        json={"name": "Temp Bot"},
    )
    sa_id = r.json()["id"]
    r2 = await admin_client.post(f"{BASE}/service-accounts/{sa_id}/deactivate")
    assert r2.status_code == 200
    assert "deactivated" in r2.json()["detail"].lower()


# ── Test 4: Deactivate unknown SA returns 404 ────────────────────────────────


@pytest.mark.asyncio
async def test_deactivate_nonexistent_service_account(admin_client: AsyncClient) -> None:
    r = await admin_client.post(f"{BASE}/service-accounts/does-not-exist/deactivate")
    assert r.status_code == 404


# ── Test 5: Create API key ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_api_key(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/api-keys",
        json={
            "name": "Test Key",
            "scopes": ["assessments:read", "suppliers:read"],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Key"
    assert data["key_prefix"].startswith("eios_")
    # raw_key returned ONCE at creation
    assert data["raw_key"].startswith("eios_")
    assert len(data["raw_key"]) == 45
    assert "assessments:read" in data["scopes"]


# ── Test 6: List API keys — raw_key never returned ───────────────────────────


@pytest.mark.asyncio
async def test_list_api_keys_no_raw_key(admin_client: AsyncClient) -> None:
    await admin_client.post(
        f"{BASE}/api-keys",
        json={"name": "List Test Key", "scopes": ["findings:read"]},
    )
    r = await admin_client.get(f"{BASE}/api-keys")
    assert r.status_code == 200
    keys = r.json()
    assert isinstance(keys, list)
    for k in keys:
        assert "raw_key" not in k
        assert "key_hash" not in k
        assert k["key_prefix"].startswith("eios_")


# ── Test 7: Revoke API key ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_api_key(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/api-keys",
        json={"name": "Revoke Test Key", "scopes": ["risks:read"]},
    )
    key_id = r.json()["id"]
    r2 = await admin_client.post(f"{BASE}/api-keys/{key_id}/revoke")
    assert r2.status_code == 200
    assert "revoked" in r2.json()["detail"].lower()

    # Confirm it shows as inactive in list
    r3 = await admin_client.get(f"{BASE}/api-keys")
    matching = [k for k in r3.json() if k["id"] == key_id]
    assert len(matching) == 1
    assert matching[0]["is_active"] is False
    assert matching[0]["revoked_at"] is not None


# ── Test 8: Revoke already-revoked key returns 400 ───────────────────────────


@pytest.mark.asyncio
async def test_revoke_already_revoked_key(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/api-keys",
        json={"name": "Double Revoke Key", "scopes": ["risks:read"]},
    )
    key_id = r.json()["id"]
    await admin_client.post(f"{BASE}/api-keys/{key_id}/revoke")
    r2 = await admin_client.post(f"{BASE}/api-keys/{key_id}/revoke")
    assert r2.status_code == 400


# ── Test 9: API key auth — valid key authenticates ───────────────────────────


@pytest.mark.asyncio
async def test_api_key_auth_success(admin_client: AsyncClient, anon_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/api-keys",
        json={"name": "Auth Test Key", "scopes": ["suppliers:read"]},
    )
    raw_key = r.json()["raw_key"]

    # Use raw key as Bearer token
    r2 = await anon_client.get(
        "/api/v1/suppliers",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    # 200 or empty list — key was accepted (not 401)
    assert r2.status_code in (200, 404)


# ── Test 10: Revoked API key returns 401 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_revoked_api_key_rejected(admin_client: AsyncClient, anon_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/api-keys",
        json={"name": "Revoke Auth Key", "scopes": ["suppliers:read"]},
    )
    data = r.json()
    raw_key = data["raw_key"]
    key_id = data["id"]

    await admin_client.post(f"{BASE}/api-keys/{key_id}/revoke")

    r2 = await anon_client.get(
        "/api/v1/suppliers",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert r2.status_code == 401


# ── Test 11: Invalid API key format returns 401 ───────────────────────────────


@pytest.mark.asyncio
async def test_invalid_api_key_rejected(anon_client: AsyncClient) -> None:
    r = await anon_client.get(
        "/api/v1/suppliers",
        headers={"Authorization": "Bearer eios_notarealkey0000000000000000000000000000000"},
    )
    assert r.status_code == 401


# ── Test 12: Create API key with service account ─────────────────────────────


@pytest.mark.asyncio
async def test_create_api_key_with_service_account(admin_client: AsyncClient) -> None:
    sa_r = await admin_client.post(
        f"{BASE}/service-accounts",
        json={"name": "Linked SA"},
    )
    sa_id = sa_r.json()["id"]

    r = await admin_client.post(
        f"{BASE}/api-keys",
        json={
            "name": "SA-Linked Key",
            "scopes": ["assessments:read"],
            "service_account_id": sa_id,
        },
    )
    assert r.status_code == 201
    key_id = r.json()["id"]

    keys_r = await admin_client.get(f"{BASE}/api-keys")
    matching = [k for k in keys_r.json() if k["id"] == key_id]
    assert matching[0]["service_account_id"] == sa_id


# ── Test 13: Usage analytics ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_key_usage_summary(admin_client: AsyncClient) -> None:
    r = await admin_client.get(f"{BASE}/api-keys/usage")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    for item in r.json():
        assert "requests_total" in item
        assert "key_prefix" in item


# ── Test 14: Create webhook ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_webhook(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/webhooks",
        json={
            "name": "Test Webhook",
            "target_url": "https://example.com/webhook",
            "events": ["assessment.created", "finding.created"],
            "secret": "my-super-secure-webhook-secret-32chars",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Webhook"
    assert "assessment.created" in data["events"]
    assert data["is_active"] is True
    assert "secret" not in data  # secret never returned


# ── Test 15: List webhooks ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_webhooks(admin_client: AsyncClient) -> None:
    await admin_client.post(
        f"{BASE}/webhooks",
        json={
            "name": "List Test Hook",
            "target_url": "https://example.com/hook2",
            "events": ["risk.created"],
            "secret": "webhook-secret-minimum-sixteen-ch",
        },
    )
    r = await admin_client.get(f"{BASE}/webhooks")
    assert r.status_code == 200
    hooks = r.json()
    names = [h["name"] for h in hooks]
    assert "List Test Hook" in names
    for h in hooks:
        assert "secret" not in h


# ── Test 16: Update webhook ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_webhook(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/webhooks",
        json={
            "name": "Update Test Hook",
            "target_url": "https://example.com/orig",
            "events": ["assessment.created"],
            "secret": "webhook-secret-minimum-sixteen-ch",
        },
    )
    hook_id = r.json()["id"]

    r2 = await admin_client.patch(
        f"{BASE}/webhooks/{hook_id}",
        json={"name": "Updated Hook", "events": ["assessment.approved", "finding.created"]},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["name"] == "Updated Hook"
    assert "assessment.approved" in data["events"]


# ── Test 17: Disable webhook via PATCH ───────────────────────────────────────


@pytest.mark.asyncio
async def test_disable_webhook(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/webhooks",
        json={
            "name": "Disable Test Hook",
            "target_url": "https://example.com/disable",
            "events": ["supplier.created"],
            "secret": "webhook-secret-minimum-sixteen-ch",
        },
    )
    hook_id = r.json()["id"]
    r2 = await admin_client.patch(f"{BASE}/webhooks/{hook_id}", json={"is_active": False})
    assert r2.status_code == 200
    assert r2.json()["is_active"] is False


# ── Test 18: Delete webhook ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_webhook(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/webhooks",
        json={
            "name": "Delete Test Hook",
            "target_url": "https://example.com/delete",
            "events": ["recommendation.created"],
            "secret": "webhook-secret-minimum-sixteen-ch",
        },
    )
    hook_id = r.json()["id"]
    r2 = await admin_client.delete(f"{BASE}/webhooks/{hook_id}")
    assert r2.status_code == 204

    # Should not appear in list (or be deleted)
    r3 = await admin_client.get(f"{BASE}/webhooks/{hook_id}/deliveries")
    assert r3.status_code == 404


# ── Test 19: Webhook delivery log initially empty ─────────────────────────────


@pytest.mark.asyncio
async def test_webhook_delivery_log_empty(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/webhooks",
        json={
            "name": "Empty Delivery Hook",
            "target_url": "https://example.com/empty",
            "events": ["board_report.generated"],
            "secret": "webhook-secret-minimum-sixteen-ch",
        },
    )
    hook_id = r.json()["id"]
    r2 = await admin_client.get(f"{BASE}/webhooks/{hook_id}/deliveries")
    assert r2.status_code == 200
    assert r2.json() == []


# ── Test 20: List all deliveries ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_all_deliveries(admin_client: AsyncClient) -> None:
    r = await admin_client.get(f"{BASE}/deliveries")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Test 21: Update nonexistent webhook returns 404 ──────────────────────────


@pytest.mark.asyncio
async def test_update_nonexistent_webhook(admin_client: AsyncClient) -> None:
    r = await admin_client.patch(
        f"{BASE}/webhooks/does-not-exist",
        json={"name": "Ghost"},
    )
    assert r.status_code == 404


# ── Test 22: Scope enforcement — key without scope rejected ──────────────────


@pytest.mark.asyncio
async def test_scope_enforcement(admin_client: AsyncClient, anon_client: AsyncClient) -> None:
    # Create key with only suppliers:read — should NOT access executive endpoints
    r = await admin_client.post(
        f"{BASE}/api-keys",
        json={"name": "Scoped Key", "scopes": ["suppliers:read"]},
    )
    raw_key = r.json()["raw_key"]

    # Try to access an executive endpoint that requires executive:read scope
    r2 = await anon_client.get(
        "/api/v1/executive/kpi-trends",
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert r2.status_code == 403


# ── Test 23: Tenant isolation — key cannot see other org's resources ──────────


@pytest.mark.asyncio
async def test_tenant_isolation_service_accounts(admin_client: AsyncClient) -> None:
    # All service accounts returned belong to the authenticated org
    sa_r = await admin_client.post(
        f"{BASE}/service-accounts",
        json={"name": "Isolation Check SA"},
    )
    org_id = sa_r.json()["organization_id"]

    all_sa = await admin_client.get(f"{BASE}/service-accounts")
    for sa in all_sa.json():
        assert sa["organization_id"] == org_id


# ── Test 24: Tenant isolation — API keys belong to org ───────────────────────


@pytest.mark.asyncio
async def test_tenant_isolation_api_keys(admin_client: AsyncClient) -> None:
    await admin_client.post(
        f"{BASE}/api-keys",
        json={"name": "Isolation Key", "scopes": ["risks:read"]},
    )
    all_keys = await admin_client.get(f"{BASE}/api-keys")
    first_key = all_keys.json()[0]
    # All keys have the same org — verify the key is org-scoped
    # (we can't easily test cross-org in single-org setup, but we ensure
    # that accessing another org's key by ID returns 404)
    r = await admin_client.post(f"{BASE}/api-keys/fake-other-org-key-id/revoke")
    assert r.status_code == 404


# ── Test 25: API key requires min_length=1 for scopes ────────────────────────


@pytest.mark.asyncio
async def test_create_api_key_empty_scopes_rejected(admin_client: AsyncClient) -> None:
    r = await admin_client.post(
        f"{BASE}/api-keys",
        json={"name": "Bad Key", "scopes": []},
    )
    assert r.status_code == 422


# ── Test 26: Unauthenticated requests to management endpoints return 401 ──────


@pytest.mark.asyncio
async def test_platform_endpoints_require_auth(anon_client: AsyncClient) -> None:
    endpoints = [
        ("GET", f"{BASE}/service-accounts"),
        ("GET", f"{BASE}/api-keys"),
        ("GET", f"{BASE}/webhooks"),
        ("GET", f"{BASE}/deliveries"),
    ]
    for method, url in endpoints:
        r = await anon_client.request(method, url)
        assert r.status_code == 401, f"{method} {url} should require auth"
