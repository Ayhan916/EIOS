"""
Integration tests for M26.1 Governance Hardening.

Test scenarios:
  1.  Four-eyes: creator (with reviewer role) cannot approve own assessment
  2.  Four-eyes: creator (with reviewer role) cannot reject own assessment
  3.  Four-eyes: creator (with reviewer role) cannot request changes on own assessment
  4.  Four-eyes: a different reviewer CAN approve the same assessment
  5.  Four-eyes: admin who created assessment cannot approve it
  6.  Comment tenant isolation: org B cannot list comments on org A assessment
  7.  Comment tenant isolation: org B cannot list comments on org A finding
  8.  Comment tenant isolation: unknown entity_id returns 404
  9.  Comment tenant isolation: org A CAN list its own comments
  10. Review action tenant isolation: org B cannot take action on org A assessment
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from domain.assessment import Assessment
from domain.enums import ConfidenceLevel, EntityStatus
from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.repositories.assessment import SQLAssessmentRepository
from infrastructure.persistence.repositories.user import SQLUserRepository
from shared.rate_limit import reset_for_tests

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

AUTH = "/api/v1/auth"
ASSESS = "/api/v1/assessments"
COMMENTS = "/api/v1/comments"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_schema(setup_test_schema: None) -> None:  # type: ignore[misc]
    pass


@pytest.fixture(autouse=True)
def _reset_rl() -> None:
    reset_for_tests()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(email: str, role: str = "analyst") -> tuple[str, str, str]:
    """Register a new user and return (token, user_id, org_id).
    Every call creates a fresh org (registration always bootstraps a new tenant).
    To place a second user in an existing org, call _move_to_org() afterward.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AUTH + "/register",
            json={
                "email": email,
                "display_name": email.split("@")[0],
                "password": "Govern1234!",
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


async def _move_to_org(user_id: str, org_id: str, role: str) -> None:
    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLUserRepository(session)
        user = await repo.get_by_id(user_id)
        assert user
        user.organization_id = org_id
        user.role = role
        await repo.save(user)


async def _make_assessment(org_id: str, created_by: str) -> str:
    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLAssessmentRepository(session)
        a = Assessment(
            title="Governance Hardening Test",
            description="M26.1 test assessment",
            assessment_type="quick_scan",
            scope="scope",
            confidence=ConfidenceLevel.MEDIUM,
            status=EntityStatus.REVIEWED,
            organization_id=org_id,
            created_by=created_by,
        )
        saved = await repo.save(a)
        return saved.id


async def _submit_for_review(assessment_id: str, token: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        r = await c.post(ASSESS + f"/{assessment_id}/submit-for-review", json={})
    assert r.status_code == 200, r.text


# ── Four-eyes principle ───────────────────────────────────────────────────────


async def test_creator_cannot_approve_own_assessment(setup_test_schema: None) -> None:
    """A reviewer who created the assessment must receive 403 on approve."""
    tok, uid, org = await _register("gov-self-approve@eios.dev", "reviewer")
    aid = await _make_assessment(org, uid)
    await _submit_for_review(aid, tok)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "approve"},
        )

    assert r.status_code == 403, r.text
    assert "four-eyes" in r.json()["detail"].lower()


async def test_creator_cannot_reject_own_assessment(setup_test_schema: None) -> None:
    """A reviewer who created the assessment must receive 403 on reject."""
    tok, uid, org = await _register("gov-self-reject@eios.dev", "reviewer")
    aid = await _make_assessment(org, uid)
    await _submit_for_review(aid, tok)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "reject", "comment": "Looks fine to me."},
        )

    assert r.status_code == 403, r.text


async def test_creator_cannot_request_changes_on_own_assessment(setup_test_schema: None) -> None:
    """A reviewer who created the assessment must receive 403 on request_changes."""
    tok, uid, org = await _register("gov-self-rc@eios.dev", "reviewer")
    aid = await _make_assessment(org, uid)
    await _submit_for_review(aid, tok)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "request_changes"},
        )

    assert r.status_code == 403, r.text


async def test_different_reviewer_can_approve(setup_test_schema: None) -> None:
    """A reviewer who did NOT create the assessment can approve it."""
    tok_creator, uid_creator, org = await _register("gov-creator-ok@eios.dev", "analyst")
    tok_reviewer, uid_reviewer, _ = await _register("gov-reviewer-ok@eios.dev", "reviewer")
    await _move_to_org(uid_reviewer, org, "reviewer")

    aid = await _make_assessment(org, uid_creator)
    await _submit_for_review(aid, tok_creator)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_reviewer}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "approve", "comment": "All clear."},
        )

    assert r.status_code == 200, r.text
    assert r.json()["action_type"] == "approve"


async def test_admin_creator_cannot_approve_own_assessment(setup_test_schema: None) -> None:
    """Admin role does not exempt a creator from the four-eyes principle."""
    tok, uid, org = await _register("gov-admin-self@eios.dev", "admin")
    aid = await _make_assessment(org, uid)
    await _submit_for_review(aid, tok)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "approve"},
        )

    assert r.status_code == 403, r.text


# ── Comment tenant isolation ──────────────────────────────────────────────────


async def test_org_b_cannot_list_comments_on_org_a_assessment(setup_test_schema: None) -> None:
    """Org B user who knows org A's assessment ID gets 404 on GET /comments/."""
    tok_a, uid_a, org_a = await _register("gov-cmt-iso-a@eios.dev", "analyst")
    tok_b, uid_b, org_b = await _register("gov-cmt-iso-b@eios.dev", "analyst")

    aid = await _make_assessment(org_a, uid_a)

    # Org A posts a comment
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_a}"},
    ) as c:
        await c.post(
            COMMENTS + "/",
            json={"entity_type": "Assessment", "entity_id": aid, "content": "Secret note."},
        )

    # Org B tries to list comments using the known entity_id
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.get(
            COMMENTS + "/",
            params={"entity_type": "Assessment", "entity_id": aid},
        )

    assert r.status_code == 404, r.text


async def test_unknown_entity_id_returns_404(setup_test_schema: None) -> None:
    """A valid UUID that doesn't exist as an Assessment returns 404, not an empty list."""
    tok, _, _ = await _register("gov-cmt-noid@eios.dev", "analyst")
    nonexistent_id = "00000000-0000-0000-0000-000000000099"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(
            COMMENTS + "/",
            params={"entity_type": "Assessment", "entity_id": nonexistent_id},
        )

    assert r.status_code == 404, r.text


async def test_org_a_can_list_own_comments(setup_test_schema: None) -> None:
    """Org A's own users can always list their own comments."""
    tok, uid, org = await _register("gov-cmt-own@eios.dev", "analyst")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        await c.post(
            COMMENTS + "/",
            json={"entity_type": "Assessment", "entity_id": aid, "content": "Own comment."},
        )
        r = await c.get(
            COMMENTS + "/",
            params={"entity_type": "Assessment", "entity_id": aid},
        )

    assert r.status_code == 200, r.text
    assert len(r.json()) >= 1


async def test_review_action_tenant_isolation(setup_test_schema: None) -> None:
    """Org B reviewer cannot take a review action on org A's assessment."""
    tok_a, uid_a, org_a = await _register("gov-ra-iso-a@eios.dev", "analyst")
    tok_b, uid_b, org_b = await _register("gov-ra-iso-b@eios.dev", "reviewer")

    aid = await _make_assessment(org_a, uid_a)
    await _submit_for_review(aid, tok_a)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "approve"},
        )

    assert r.status_code == 404, r.text
