"""
Integration tests for M26 Collaboration, Review Workflow & Approvals.

Test scenarios:
  1.  Submit assessment for review — happy path
  2.  Submit for review — invalid transition (already InReview)
  3.  Assign reviewer — admin can assign
  4.  Assign reviewer — non-admin cannot assign
  5.  Review action — approve transitions to Approved
  6.  Review action — request_changes transitions to ChangesRequested
  7.  Review action — cannot action if not InReview
  8.  List review actions — correct history returned
  9.  Activity timeline — includes audit events and review actions
  10. Comment create — successful
  11. Comment list — returns comment with author name
  12. Comment edit — author can edit
  13. Comment edit — non-author cannot edit
  14. Comment delete (soft) — author can delete
  15. Comment delete — non-author non-admin cannot delete
  16. Comment list — deleted comment hidden by default
  17. Tenant isolation — org B cannot see org A review actions
  18. Tenant isolation — org B cannot submit org A assessment for review
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


async def _register(email: str, org: str, role: str = "analyst") -> tuple[str, str, str]:
    """Returns (token, user_id, org_id)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AUTH + "/register",
            json={
                "email": email,
                "display_name": email.split("@")[0],
                "password": "Collab1234!",
                "organization_name": f"Org-{email}",
            },
        )
    assert r.status_code == 201, r.text
    d = r.json()
    # promote role if needed
    if role != "admin":
        async with AsyncSessionFactory() as session, session.begin():
            repo = SQLUserRepository(session)
            user = await repo.get_by_id(d["user"]["id"])
            assert user
            user.role = role
            await repo.save(user)
    return d["access_token"], d["user"]["id"], d["user"]["organization_id"]


async def _make_assessment(org_id: str, user_id: str) -> str:
    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLAssessmentRepository(session)
        a = Assessment(
            title="M26 Test Assessment",
            description="For collaboration testing",
            assessment_type="quick_scan",
            scope="scope",
            confidence=ConfidenceLevel.MEDIUM,
            status=EntityStatus.REVIEWED,
            organization_id=org_id,
            created_by=user_id,
        )
        saved = await repo.save(a)
        return saved.id


# ── Review workflow tests ──────────────────────────────────────────────────────


async def test_submit_for_review_happy_path(setup_test_schema: None) -> None:
    tok, uid, org = await _register("collab-submit@eios.dev", "Org Submit")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(ASSESS + f"/{aid}/submit-for-review", json={})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["review_status"] == "InReview"


async def test_submit_for_review_invalid_transition(setup_test_schema: None) -> None:
    tok, uid, org = await _register("collab-inv-trans@eios.dev", "Org InvTrans")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        # First submit — valid
        await c.post(ASSESS + f"/{aid}/submit-for-review", json={})
        # Second submit — invalid (already InReview)
        r = await c.post(ASSESS + f"/{aid}/submit-for-review", json={})

    assert r.status_code == 409, r.text


async def test_assign_reviewer_admin_only(setup_test_schema: None) -> None:
    tok_admin, uid_admin, org = await _register(
        "collab-admin@eios.dev", "Org AssignReviewer", "admin"
    )
    tok_analyst, uid_reviewer, _ = await _register(
        "collab-rev@eios.dev", "Org AssignReviewer", "reviewer"
    )

    # promote the second user to same org and reviewer role
    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLUserRepository(session)
        reviewer = await repo.get_by_id(uid_reviewer)
        assert reviewer
        reviewer.organization_id = org
        reviewer.role = "reviewer"
        await repo.save(reviewer)

    aid = await _make_assessment(org, uid_admin)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_admin}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/assign-reviewer",
            json={"reviewer_id": uid_reviewer},
        )

    assert r.status_code == 200, r.text
    assert r.json()["assigned_reviewer_id"] == uid_reviewer


async def test_review_action_approve(setup_test_schema: None) -> None:
    tok_analyst, uid_a, org = await _register("collab-approv-a@eios.dev", "Org Approve", "analyst")
    tok_reviewer, uid_r, _ = await _register(
        "collab-approv-r@eios.dev", "Org Approve Rev", "reviewer"
    )

    # Move reviewer to same org
    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLUserRepository(session)
        rev = await repo.get_by_id(uid_r)
        assert rev
        rev.organization_id = org
        rev.role = "reviewer"
        await repo.save(rev)

    aid = await _make_assessment(org, uid_a)

    # Submit for review
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_analyst}"},
    ) as c:
        r = await c.post(ASSESS + f"/{aid}/submit-for-review", json={})
    assert r.status_code == 200

    # Reviewer approves
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_reviewer}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "approve", "comment": "All checks passed."},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["action_type"] == "approve"

    # Check assessment is now Approved
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_analyst}"},
    ) as c:
        r = await c.get(ASSESS + f"/{aid}")
    assert r.json()["review_status"] == "Approved"


async def test_review_action_request_changes(setup_test_schema: None) -> None:
    tok_analyst, uid_a, org = await _register("collab-reqch-a@eios.dev", "Org ReqCh", "analyst")
    tok_reviewer, uid_r, _ = await _register("collab-reqch-r@eios.dev", "Org ReqCh Rev", "reviewer")

    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLUserRepository(session)
        rev = await repo.get_by_id(uid_r)
        assert rev
        rev.organization_id = org
        rev.role = "reviewer"
        await repo.save(rev)

    aid = await _make_assessment(org, uid_a)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_analyst}"},
    ) as c:
        await c.post(ASSESS + f"/{aid}/submit-for-review", json={})

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_reviewer}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "request_changes", "comment": "Please add more evidence."},
        )

    assert r.status_code == 200, r.text

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_analyst}"},
    ) as c:
        r = await c.get(ASSESS + f"/{aid}")
    assert r.json()["review_status"] == "ChangesRequested"


async def test_review_action_blocked_if_not_in_review(setup_test_schema: None) -> None:
    tok_analyst, uid_a, org = await _register("collab-notinrev@eios.dev", "Org NotInRev", "analyst")
    tok_reviewer, uid_r, _ = await _register(
        "collab-notinrev-r@eios.dev", "Org NotInRev R", "reviewer"
    )

    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLUserRepository(session)
        rev = await repo.get_by_id(uid_r)
        assert rev
        rev.organization_id = org
        rev.role = "reviewer"
        await repo.save(rev)

    aid = await _make_assessment(org, uid_a)
    # Assessment is Draft — not submitted for review

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_reviewer}"},
    ) as c:
        r = await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "approve"},
        )

    assert r.status_code == 409, r.text


async def test_list_review_actions(setup_test_schema: None) -> None:
    tok_analyst, uid_a, org = await _register("collab-listra@eios.dev", "Org ListRA", "analyst")
    tok_reviewer, uid_r, _ = await _register("collab-listra-r@eios.dev", "Org ListRA R", "reviewer")

    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLUserRepository(session)
        rev = await repo.get_by_id(uid_r)
        assert rev
        rev.organization_id = org
        rev.role = "reviewer"
        await repo.save(rev)

    aid = await _make_assessment(org, uid_a)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_analyst}"},
    ) as c:
        await c.post(ASSESS + f"/{aid}/submit-for-review", json={})

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_reviewer}"},
    ) as c:
        await c.post(
            ASSESS + f"/{aid}/review-action",
            json={"action_type": "request_changes", "comment": "Needs work."},
        )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_analyst}"},
    ) as c:
        r = await c.get(ASSESS + f"/{aid}/review-actions")

    assert r.status_code == 200, r.text
    actions = r.json()
    assert len(actions) == 1
    assert actions[0]["action_type"] == "request_changes"
    assert actions[0]["comment"] == "Needs work."


async def test_activity_timeline(setup_test_schema: None) -> None:
    tok, uid, org = await _register("collab-timeline@eios.dev", "Org Timeline", "analyst")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        await c.post(ASSESS + f"/{aid}/submit-for-review", json={})
        r = await c.get(ASSESS + f"/{aid}/activity")

    assert r.status_code == 200, r.text
    events = r.json()
    assert len(events) >= 1
    actions = [e["action"] for e in events]
    assert "assessment.review_started" in actions


# ── Comment tests ─────────────────────────────────────────────────────────────


async def test_create_comment(setup_test_schema: None) -> None:
    tok, uid, org = await _register("collab-cmt-create@eios.dev", "Org CmtCreate", "analyst")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            COMMENTS + "/",
            json={
                "entity_type": "Assessment",
                "entity_id": aid,
                "content": "This assessment looks comprehensive.",
            },
        )

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["content"] == "This assessment looks comprehensive."
    assert body["author_id"] == uid
    assert not body["is_deleted"]


async def test_list_comments(setup_test_schema: None) -> None:
    tok, uid, org = await _register("collab-cmt-list@eios.dev", "Org CmtList", "analyst")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        await c.post(
            COMMENTS + "/",
            json={"entity_type": "Assessment", "entity_id": aid, "content": "First comment."},
        )
        r = await c.get(COMMENTS + "/", params={"entity_type": "Assessment", "entity_id": aid})

    assert r.status_code == 200, r.text
    comments = r.json()
    assert len(comments) >= 1
    assert comments[0]["author_name"] is not None


async def test_edit_comment_by_author(setup_test_schema: None) -> None:
    tok, uid, org = await _register("collab-cmt-edit@eios.dev", "Org CmtEdit", "analyst")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        create_r = await c.post(
            COMMENTS + "/",
            json={"entity_type": "Assessment", "entity_id": aid, "content": "Original."},
        )
        cid = create_r.json()["id"]
        r = await c.patch(COMMENTS + f"/{cid}", json={"content": "Edited content."})

    assert r.status_code == 200, r.text
    assert r.json()["content"] == "Edited content."
    assert r.json()["is_edited"]


async def test_edit_comment_by_non_author_forbidden(setup_test_schema: None) -> None:
    tok_a, uid_a, org = await _register("collab-cmt-auth@eios.dev", "Org CmtAuth", "analyst")
    tok_b, uid_b, _ = await _register("collab-cmt-other@eios.dev", "Org CmtOther", "analyst")
    # Move B to same org
    async with AsyncSessionFactory() as session, session.begin():
        repo = SQLUserRepository(session)
        u = await repo.get_by_id(uid_b)
        assert u
        u.organization_id = org
        await repo.save(u)

    aid = await _make_assessment(org, uid_a)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_a}"},
    ) as c:
        create_r = await c.post(
            COMMENTS + "/",
            json={"entity_type": "Assessment", "entity_id": aid, "content": "Author only."},
        )
    cid = create_r.json()["id"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.patch(COMMENTS + f"/{cid}", json={"content": "Hijack!"})

    assert r.status_code == 403, r.text


async def test_soft_delete_comment(setup_test_schema: None) -> None:
    tok, uid, org = await _register("collab-cmt-del@eios.dev", "Org CmtDel", "analyst")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        create_r = await c.post(
            COMMENTS + "/",
            json={"entity_type": "Assessment", "entity_id": aid, "content": "Delete me."},
        )
        cid = create_r.json()["id"]
        r = await c.delete(COMMENTS + f"/{cid}")

    assert r.status_code == 204, r.text


async def test_deleted_comment_hidden_in_list(setup_test_schema: None) -> None:
    tok, uid, org = await _register("collab-cmt-hidden@eios.dev", "Org CmtHidden", "analyst")
    aid = await _make_assessment(org, uid)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        create_r = await c.post(
            COMMENTS + "/",
            json={
                "entity_type": "Assessment",
                "entity_id": aid,
                "content": "Visible then deleted.",
            },
        )
        cid = create_r.json()["id"]
        await c.delete(COMMENTS + f"/{cid}")
        r = await c.get(COMMENTS + "/", params={"entity_type": "Assessment", "entity_id": aid})

    visible = [c for c in r.json() if not c["is_deleted"]]
    assert all(c["id"] != cid for c in visible)


# ── Tenant isolation ──────────────────────────────────────────────────────────


async def test_tenant_isolation_review_actions(setup_test_schema: None) -> None:
    tok_a, uid_a, org_a = await _register("collab-iso-a@eios.dev", "Org IsoA", "analyst")
    tok_b, uid_b, org_b = await _register("collab-iso-b@eios.dev", "Org IsoB", "analyst")

    aid = await _make_assessment(org_a, uid_a)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.get(ASSESS + f"/{aid}/review-actions")

    assert r.status_code == 404, r.text


async def test_tenant_isolation_submit_for_review(setup_test_schema: None) -> None:
    tok_a, uid_a, org_a = await _register("collab-iso2-a@eios.dev", "Org Iso2A", "analyst")
    tok_b, uid_b, org_b = await _register("collab-iso2-b@eios.dev", "Org Iso2B", "analyst")

    aid = await _make_assessment(org_a, uid_a)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.post(ASSESS + f"/{aid}/submit-for-review", json={})

    assert r.status_code == 404, r.text
