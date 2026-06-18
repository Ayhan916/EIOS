"""
Integration tests for /api/v1/notifications and notification_service (M24 / M24.1).

Scenarios covered:
  1.  List isolation   — user sees only their own notifications
  2.  Mark-read authz — user cannot mark another user's notification as read
  3.  Mark-all authz  — mark-all only touches the current user's notifications
  4.  Dedupe key      — second call with same key returns None, list shows 1 item
  5.  Email pref True — send_email IS called when preference is enabled
  6.  Email pref False— send_email is NOT called when preference is disabled
  7.  Overdue dedupe  — same rec + same date → only 1 notification created
  8.  PATCH /auth/me  — preferences are saved and returned in GET /auth/me
  9.  Unknown pref key— PATCH /auth/me with unknown pref key → 422
  10. No-auth 401     — unauthenticated requests are rejected
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from infrastructure.persistence.database import AsyncSessionFactory
from application.notification_service import notify
from domain.enums import NotificationType
from shared.rate_limit import reset_for_tests

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

AUTH = "/api/v1/auth"
NOTIF = "/api/v1/notifications"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_schema(setup_test_schema: None) -> None:  # type: ignore[misc]
    pass


@pytest.fixture(autouse=True)
def _reset_rl() -> None:
    reset_for_tests()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register(email: str, org: str) -> tuple[str, str]:
    """Register a user in a fresh org. Returns (token, user_id)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AUTH + "/register",
            json={
                "email": email,
                "display_name": email.split("@")[0],
                "password": "secure-pw-notif-123",
                "organization_name": org,
            },
        )
    assert r.status_code == 201, r.text
    d = r.json()
    return d["access_token"], d["user"]["id"]


async def _get_me(token: str) -> dict:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.get(AUTH + "/me")
    assert r.status_code == 200, r.text
    return r.json()


async def _patch_me(token: str, payload: dict) -> tuple[int, dict]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.patch(AUTH + "/me", json=payload)
    return r.status_code, r.json()


async def _list_notifs(token: str) -> tuple[int, dict]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.get(NOTIF + "/")
    return r.status_code, r.json()


async def _mark_read(token: str, notif_id: str) -> int:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.patch(NOTIF + f"/{notif_id}/read")
    return r.status_code


async def _mark_all(token: str) -> int:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.patch(NOTIF + "/read-all")
    return r.status_code


async def _create_notif_direct(
    user_id: str,
    org_id: str,
    *,
    dedupe_key: str | None = None,
    notification_type: str = NotificationType.ASSESSMENT_APPROVED,
) -> str | None:
    """Insert a notification directly via the service. Returns notification id or None."""
    async with AsyncSessionFactory() as session, session.begin():
        notif = await notify(
            session=session,
            user_id=user_id,
            organization_id=org_id,
            notification_type=notification_type,
            title="Test notification",
            body="This is a test.",
            dedupe_key=dedupe_key,
        )
    return notif.id if notif else None


# ---------------------------------------------------------------------------
# Test 1: List isolation
# ---------------------------------------------------------------------------

async def test_list_notifications_isolation(setup_test_schema: None) -> None:
    """User A and User B are in different orgs. Notification for A is invisible to B."""
    tok_a, id_a = await _register("notif-iso-a@eios.dev", "Org NotifIsoA")
    tok_b, id_b = await _register("notif-iso-b@eios.dev", "Org NotifIsoB")

    me_a = await _get_me(tok_a)
    await _create_notif_direct(id_a, me_a["organization_id"])

    code, body = await _list_notifs(tok_b)
    assert code == 200
    assert body["unread_count"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# Test 2: Mark-read authorization
# ---------------------------------------------------------------------------

async def test_mark_read_authorization(setup_test_schema: None) -> None:
    """User B cannot mark User A's notification as read — must get 404."""
    tok_a, id_a = await _register("notif-authz-a@eios.dev", "Org NotifAuthzA")
    tok_b, id_b = await _register("notif-authz-b@eios.dev", "Org NotifAuthzB")

    me_a = await _get_me(tok_a)
    notif_id = await _create_notif_direct(id_a, me_a["organization_id"])
    assert notif_id is not None

    # B tries to mark A's notification — must be 404
    code = await _mark_read(tok_b, notif_id)
    assert code == 404

    # A can mark their own
    code = await _mark_read(tok_a, notif_id)
    assert code == 200


# ---------------------------------------------------------------------------
# Test 3: Mark-all authorization
# ---------------------------------------------------------------------------

async def test_mark_all_authorization(setup_test_schema: None) -> None:
    """mark-all for user B does not affect user A's unread count."""
    tok_a, id_a = await _register("notif-markall-a@eios.dev", "Org NotifMarkAllA")
    tok_b, id_b = await _register("notif-markall-b@eios.dev", "Org NotifMarkAllB")

    me_a = await _get_me(tok_a)
    me_b = await _get_me(tok_b)
    await _create_notif_direct(id_a, me_a["organization_id"], dedupe_key="markall-a-1")
    await _create_notif_direct(id_b, me_b["organization_id"], dedupe_key="markall-b-1")

    # B marks all as read
    code = await _mark_all(tok_b)
    assert code == 204

    # A's notification is still unread
    _, body_a = await _list_notifs(tok_a)
    assert body_a["unread_count"] == 1

    # B's is now read
    _, body_b = await _list_notifs(tok_b)
    assert body_b["unread_count"] == 0


# ---------------------------------------------------------------------------
# Test 4: Dedupe key prevents duplicate
# ---------------------------------------------------------------------------

async def test_dedupe_key_prevents_duplicate(setup_test_schema: None) -> None:
    """Calling notify() twice with the same dedupe_key creates exactly 1 notification."""
    tok, uid = await _register("notif-dedupe@eios.dev", "Org NotifDedupe")
    me = await _get_me(tok)
    org_id = me["organization_id"]
    key = "dedupe-test-unique-key-001"

    first = await _create_notif_direct(uid, org_id, dedupe_key=key)
    second = await _create_notif_direct(uid, org_id, dedupe_key=key)

    assert first is not None
    assert second is None  # blocked by dedupe

    _, body = await _list_notifs(tok)
    assert len(body["items"]) == 1
    assert body["unread_count"] == 1


# ---------------------------------------------------------------------------
# Test 5: Email sent when preference is True
# ---------------------------------------------------------------------------

async def test_email_sent_when_preference_enabled(setup_test_schema: None) -> None:
    """send_email is called when the matching preference key is True."""
    tok, uid = await _register("notif-email-on@eios.dev", "Org NotifEmailOn")
    me = await _get_me(tok)
    org_id = me["organization_id"]

    with patch("application.notification_service.send_email", new_callable=AsyncMock) as mock_mail:
        async with AsyncSessionFactory() as session, session.begin():
            await notify(
                session=session,
                user_id=uid,
                organization_id=org_id,
                notification_type=NotificationType.ASSESSMENT_APPROVED,
                title="Approved",
                body="Your assessment was approved.",
                user_email="notif-email-on@eios.dev",
                dedupe_key="pref-on-test-001",
            )
        mock_mail.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 6: Email skipped when preference is False
# ---------------------------------------------------------------------------

async def test_email_skipped_when_preference_disabled(setup_test_schema: None) -> None:
    """send_email is NOT called when the matching preference key is set to False."""
    tok, uid = await _register("notif-email-off@eios.dev", "Org NotifEmailOff")
    me = await _get_me(tok)
    org_id = me["organization_id"]

    # Disable the assessment_approved email preference
    code, _ = await _patch_me(tok, {"notification_preferences": {"email_assessment_approved": False}})
    assert code == 200

    with patch("application.notification_service.send_email", new_callable=AsyncMock) as mock_mail:
        async with AsyncSessionFactory() as session, session.begin():
            await notify(
                session=session,
                user_id=uid,
                organization_id=org_id,
                notification_type=NotificationType.ASSESSMENT_APPROVED,
                title="Approved",
                body="Your assessment was approved.",
                user_email="notif-email-off@eios.dev",
                dedupe_key="pref-off-test-001",
            )
        mock_mail.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 7: Overdue daily dedupe
# ---------------------------------------------------------------------------

async def test_overdue_notification_daily_dedupe(setup_test_schema: None) -> None:
    """Same rec_id + same date → second notify() call is blocked; only 1 notification exists."""
    from datetime import date
    tok, uid = await _register("notif-overdue@eios.dev", "Org NotifOverdue")
    me = await _get_me(tok)
    org_id = me["organization_id"]
    rec_id = "fake-rec-id-overdue-test"
    today_str = str(date.today())

    async with AsyncSessionFactory() as session, session.begin():
        n1 = await notify(
            session=session,
            user_id=uid,
            organization_id=org_id,
            notification_type=NotificationType.ACTION_OVERDUE,
            title="Action overdue",
            body="A recommendation is overdue.",
            entity_type="recommendation",
            entity_id=rec_id,
            dedupe_key=f"overdue:{rec_id}:{today_str}",
        )

    async with AsyncSessionFactory() as session, session.begin():
        n2 = await notify(
            session=session,
            user_id=uid,
            organization_id=org_id,
            notification_type=NotificationType.ACTION_OVERDUE,
            title="Action overdue",
            body="A recommendation is overdue.",
            entity_type="recommendation",
            entity_id=rec_id,
            dedupe_key=f"overdue:{rec_id}:{today_str}",
        )

    assert n1 is not None
    assert n2 is None

    _, body = await _list_notifs(tok)
    overdue_items = [i for i in body["items"] if i["notification_type"] == "action_overdue"]
    assert len(overdue_items) == 1


# ---------------------------------------------------------------------------
# Test 8: PATCH /auth/me saves and returns preferences
# ---------------------------------------------------------------------------

async def test_patch_me_saves_notification_preferences(setup_test_schema: None) -> None:
    """PATCH /auth/me with valid keys updates and returns the correct preferences."""
    tok, _ = await _register("notif-pref-save@eios.dev", "Org NotifPrefSave")

    code, body = await _patch_me(tok, {
        "notification_preferences": {
            "email_workflow_completed": False,
            "email_action_overdue": False,
        }
    })
    assert code == 200

    me = await _get_me(tok)
    prefs = me["notification_preferences"]
    assert prefs["email_workflow_completed"] is False
    assert prefs["email_action_overdue"] is False
    # Other keys remain at their defaults
    assert prefs["email_assessment_approved"] is True
    assert prefs["email_recommendation_assigned"] is True


# ---------------------------------------------------------------------------
# Test 9: Unknown preference key is rejected
# ---------------------------------------------------------------------------

async def test_patch_me_unknown_preference_key_rejected(setup_test_schema: None) -> None:
    """Sending an unknown key in notification_preferences must return 422."""
    tok, _ = await _register("notif-pref-unk@eios.dev", "Org NotifPrefUnk")

    code, body = await _patch_me(tok, {
        "notification_preferences": {"email_unknown_event": True}
    })
    assert code == 422, body


# ---------------------------------------------------------------------------
# Test 10: Unauthenticated requests are rejected
# ---------------------------------------------------------------------------

async def test_notifications_require_auth(setup_test_schema: None) -> None:
    """All /notifications/ endpoints require a valid Bearer token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r_list = await c.get(NOTIF + "/")
        r_read = await c.patch(NOTIF + "/fake-id/read")
        r_all = await c.patch(NOTIF + "/read-all")

    assert r_list.status_code == 403
    assert r_read.status_code == 403
    assert r_all.status_code == 403
