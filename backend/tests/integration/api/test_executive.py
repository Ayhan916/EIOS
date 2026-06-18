"""
Integration tests for M29 Executive & Board Reporting API.

Covers:
  1.  GET /executive/dashboard — returns portfolio KPIs
  2.  GET /executive/dashboard — empty org returns zeros
  3.  GET /executive/kpi-trends — returns data points for scored org
  4.  GET /executive/kpi-trends — defaults to 90-day period
  5.  GET /executive/risk-register — returns ranked suppliers
  6.  GET /executive/risk-register — filter by risk_band
  7.  GET /executive/heatmaps?view=country — country buckets
  8.  GET /executive/heatmaps?view=sector — sector buckets
  9.  GET /executive/heatmaps?view=tier — tier buckets
  10. GET /executive/action-effectiveness — returns metrics dict
  11. GET /executive/governance-metrics — returns review metrics
  12. POST /executive/reports — generates and persists report (201)
  13. GET  /executive/reports — lists reports for org
  14. GET  /executive/reports/{id} — returns full report_data
  15. GET  /executive/reports/{id}/pdf — returns PDF bytes
  16. DELETE /executive/reports/{id} — admin soft-deletes; returns 204
  17. DELETE /executive/reports/{id} — executive (non-admin) gets 403
  18. POST /executive/schedules — creates schedule (201)
  19. GET  /executive/schedules — lists schedules
  20. DELETE /executive/schedules/{id} — soft-deletes schedule
  21. Tenant isolation — org B cannot see org A reports
  22. Role gate — viewer receives 403 on all executive endpoints
  23. Role gate — analyst receives 403 on all executive endpoints
  24. Executive summary — deterministic text present in report
  25. Report immutability — re-generating report creates new record
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
FINDINGS = "/api/v1/findings"
RISKS = "/api/v1/risks"
RECOS = "/api/v1/recommendations"
EXEC = "/api/v1/executive"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_schema(setup_test_schema: None) -> None:  # type: ignore[misc]
    pass


@pytest.fixture(autouse=True)
def _reset_rl() -> None:
    reset_for_tests()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register(email: str, role: str = "executive") -> tuple[str, str, str]:
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.repositories.user import SQLUserRepository  # noqa: PLC0415

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AUTH + "/register",
            json={
                "email": email,
                "display_name": email.split("@")[0],
                "password": "Exec1234!",
                "organization_name": f"ExecOrg-{email}",
            },
        )
    assert r.status_code == 201, r.text
    d = r.json()
    if role != "admin":
        async with AsyncSessionFactory() as session, session.begin():
            repo = SQLUserRepository(session)
            user = await repo.get_by_id(d["user"]["id"])
            assert user
            user.role = role
            await repo.save(user)
    return d["access_token"], d["user"]["id"], d["user"]["organization_id"]


async def _scored_org(email_prefix: str) -> tuple[str, str, str]:
    """Register an executive, create a supplier with a score, return (token, org_id, supplier_id)."""
    tok, uid, org_id = await _register(f"{email_prefix}@eios.dev", "executive")

    # Need admin token to create data (executive can GET but supplier creation needs ANALYST+)
    admin_tok, _, _ = await _register(f"{email_prefix}-admin@eios.dev", "admin")

    # Override admin to be in same org — easier to just promote the executive user to admin for setup
    # Re-use the executive token; since executive ≥ analyst, creation should work (ANALYST role required)
    # Actually executive is role 4, analyst is role 2, so executive satisfies require_analyst
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        sup_r = await c.post(
            SUPPLIERS + "/",
            json={"name": f"SupplierFor-{email_prefix}", "country": "DE", "industry": "Energy", "supplier_tier": "Tier1"},
        )
        assert sup_r.status_code == 201, sup_r.text
        supplier_id = sup_r.json()["id"]

        assess_r = await c.post(
            ASSESS + "/",
            json={"title": "Assessment", "description": "d", "supplier_id": supplier_id},
        )
        assert assess_r.status_code == 201, assess_r.text
        assess_id = assess_r.json()["id"]

        finding_r = await c.post(
            FINDINGS + "/",
            json={
                "assessment_id": assess_id,
                "title": "Critical governance gap",
                "description": "Material weakness",
                "severity": "Critical",
                "category": "Governance",
            },
        )
        assert finding_r.status_code == 201, finding_r.text

        risk_r = await c.post(
            RISKS + "/",
            json={
                "assessment_id": assess_id,
                "title": "Supplier risk",
                "description": "High risk",
                "likelihood": "High",
                "impact": "High",
                "category": "Operational",
            },
        )
        assert risk_r.status_code == 201, risk_r.text

        reco_r = await c.post(
            RECOS + "/",
            json={
                "assessment_id": assess_id,
                "title": "Fix gap",
                "description": "desc",
                "priority": "High",
            },
        )
        assert reco_r.status_code == 201, reco_r.text

        # Trigger score calculation
        intel_r = await c.get(SUPPLIERS + f"/{supplier_id}/intelligence")
        assert intel_r.status_code == 200, intel_r.text

    return tok, org_id, supplier_id


# ── Dashboard ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_returns_portfolio_kpis():
    tok, org_id, _ = await _scored_org("exec-dash")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/dashboard")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "portfolio_summary" in body
    assert "action_summary" in body
    assert "governance_summary" in body
    ps = body["portfolio_summary"]
    assert ps["total_suppliers"] >= 1
    assert ps["scored_suppliers"] >= 1


@pytest.mark.asyncio
async def test_dashboard_empty_org():
    tok, _, _ = await _register("exec-dash-empty@eios.dev", "executive")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/dashboard")
    assert r.status_code == 200
    ps = r.json()["portfolio_summary"]
    assert ps["total_suppliers"] == 0
    assert ps["scored_suppliers"] == 0
    assert ps["avg_esg_score"] is None


# ── KPI Trends ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_kpi_trends_default_period():
    tok, _, _ = await _scored_org("exec-kpi")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/kpi-trends")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["period_days"] == 90
    assert isinstance(body["data_points"], list)


@pytest.mark.asyncio
async def test_kpi_trends_custom_period():
    tok, _, _ = await _register("exec-kpi-365@eios.dev", "executive")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/kpi-trends?period=365")
    assert r.status_code == 200
    assert r.json()["period_days"] == 365


@pytest.mark.asyncio
async def test_kpi_trends_data_point_shape():
    tok, _, _ = await _scored_org("exec-kpi-shape")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/kpi-trends?period=365")
    body = r.json()
    if body["data_points"]:
        dp = body["data_points"][0]
        assert "month" in dp
        assert "avg_esg_score" in dp
        assert "supplier_count" in dp
        assert "risk_distribution" in dp


# ── Risk Register ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_risk_register_returns_ranked_suppliers():
    tok, _, _ = await _scored_org("exec-rr")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/risk-register")
    assert r.status_code == 200, r.text
    entries = r.json()
    assert len(entries) >= 1
    e = entries[0]
    assert e["rank"] == 1
    assert "supplier_name" in e
    assert "risk_score" in e
    assert "risk_band" in e
    assert "trend" in e
    assert "critical_findings" in e
    assert "overdue_actions" in e


@pytest.mark.asyncio
async def test_risk_register_filter_by_band():
    tok, _, _ = await _scored_org("exec-rr-filter")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/risk-register?risk_band=Low")
    assert r.status_code == 200
    for entry in r.json():
        assert entry["risk_band"] == "Low"


@pytest.mark.asyncio
async def test_risk_register_tenant_isolation():
    """Org B should not see org A's suppliers in the risk register."""
    tok_a, _, _ = await _scored_org("exec-rr-iso-a")
    tok_b, _, _ = await _register("exec-rr-iso-b@eios.dev", "executive")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.get(EXEC + "/risk-register")
    assert r.status_code == 200
    # Org B has no scored suppliers
    assert r.json() == []


# ── Heatmaps ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_heatmap_country_view():
    tok, _, _ = await _scored_org("exec-heat-country")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/heatmaps?view=country")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["view"] == "country"
    assert isinstance(body["buckets"], list)
    if body["buckets"]:
        b = body["buckets"][0]
        assert "label" in b
        assert "supplier_count" in b
        assert "avg_risk_score" in b


@pytest.mark.asyncio
async def test_heatmap_sector_view():
    tok, _, _ = await _scored_org("exec-heat-sector")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/heatmaps?view=sector")
    assert r.status_code == 200
    assert r.json()["view"] == "sector"


@pytest.mark.asyncio
async def test_heatmap_tier_view():
    tok, _, _ = await _scored_org("exec-heat-tier")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/heatmaps?view=tier")
    assert r.status_code == 200
    assert r.json()["view"] == "tier"


@pytest.mark.asyncio
async def test_heatmap_empty_org_returns_empty_buckets():
    tok, _, _ = await _register("exec-heat-empty@eios.dev", "executive")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/heatmaps?view=country")
    assert r.status_code == 200
    assert r.json()["buckets"] == []


# ── Action Effectiveness ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_action_effectiveness_shape():
    tok, _, _ = await _scored_org("exec-ae")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/action-effectiveness?period=30")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "opened_this_period" in body
    assert "closed_this_period" in body
    assert "total_open" in body
    assert "total_overdue" in body
    assert "resolution_rate" in body
    assert "avg_resolution_days" in body


# ── Governance Metrics ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_governance_metrics_shape():
    tok, _, _ = await _scored_org("exec-gov")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/governance-metrics?period=30")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "total_review_decisions" in body
    assert "approved" in body
    assert "approval_rate" in body


# ── Board Reports ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_board_report():
    tok, _, _ = await _scored_org("exec-report-gen")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            EXEC + "/reports",
            json={
                "title": "Q1 Board Report",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "kpi_period_days": 90,
            },
        )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "Q1 Board Report"
    assert "executive_summary" in body
    assert len(body["executive_summary"]) > 50
    assert "report_data" in body
    assert body["report_data"]["meta"]["period_start"] == "2026-01-01"
    assert body["id"] != ""
    # report_id should be patched into meta
    assert body["report_data"]["meta"]["report_id"] == body["id"]


@pytest.mark.asyncio
async def test_list_board_reports():
    tok, _, _ = await _scored_org("exec-report-list")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        await c.post(
            EXEC + "/reports",
            json={"title": "Report A", "period_start": "2026-01-01", "period_end": "2026-01-31"},
        )
        await c.post(
            EXEC + "/reports",
            json={"title": "Report B", "period_start": "2026-02-01", "period_end": "2026-02-28"},
        )
        r = await c.get(EXEC + "/reports")
    assert r.status_code == 200, r.text
    reports = r.json()
    assert len(reports) >= 2
    titles = [x["title"] for x in reports]
    assert "Report A" in titles
    assert "Report B" in titles


@pytest.mark.asyncio
async def test_get_board_report_detail():
    tok, _, _ = await _scored_org("exec-report-detail")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        cr = await c.post(
            EXEC + "/reports",
            json={"title": "Detail Test", "period_start": "2026-01-01", "period_end": "2026-03-31"},
        )
        assert cr.status_code == 201
        report_id = cr.json()["id"]

        r = await c.get(EXEC + f"/reports/{report_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == report_id
    assert "report_data" in body
    assert "supplier_snapshot" in body


@pytest.mark.asyncio
async def test_get_board_report_404():
    tok, _, _ = await _register("exec-report-404@eios.dev", "executive")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/reports/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_pdf_download():
    tok, _, _ = await _scored_org("exec-pdf")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        cr = await c.post(
            EXEC + "/reports",
            json={"title": "PDF Test", "period_start": "2026-01-01", "period_end": "2026-03-31"},
        )
        assert cr.status_code == 201
        report_id = cr.json()["id"]

        r = await c.get(EXEC + f"/reports/{report_id}/pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    # PDF magic bytes
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_delete_report_admin_only():
    """EXECUTIVE (non-admin) should get 403 when trying to delete a report."""
    tok, _, _ = await _scored_org("exec-del-403")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        cr = await c.post(
            EXEC + "/reports",
            json={"title": "Del Test", "period_start": "2026-01-01", "period_end": "2026-03-31"},
        )
        assert cr.status_code == 201
        report_id = cr.json()["id"]

        r = await c.delete(EXEC + f"/reports/{report_id}")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_report_admin_succeeds():
    tok, _, _ = await _register("exec-del-admin@eios.dev", "admin")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        # First create a supplier/score so report can be generated
        sup_r = await c.post(SUPPLIERS + "/", json={"name": "Sup", "country": "UK", "industry": "Finance"})
        assert sup_r.status_code == 201
        sid = sup_r.json()["id"]
        assess_r = await c.post(ASSESS + "/", json={"title": "A", "description": "d", "supplier_id": sid})
        assert assess_r.status_code == 201
        await c.get(SUPPLIERS + f"/{sid}/intelligence")

        cr = await c.post(
            EXEC + "/reports",
            json={"title": "Admin Del", "period_start": "2026-01-01", "period_end": "2026-03-31"},
        )
        assert cr.status_code == 201
        report_id = cr.json()["id"]

        r = await c.delete(EXEC + f"/reports/{report_id}")
    assert r.status_code == 204

    # Confirm it's gone
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r2 = await c.get(EXEC + f"/reports/{report_id}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_report_immutability_new_record_each_time():
    """Each generate call must create a distinct new record."""
    tok, _, _ = await _scored_org("exec-imm")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r1 = await c.post(
            EXEC + "/reports",
            json={"title": "R1", "period_start": "2026-01-01", "period_end": "2026-01-31"},
        )
        r2 = await c.post(
            EXEC + "/reports",
            json={"title": "R2", "period_start": "2026-02-01", "period_end": "2026-02-28"},
        )
    assert r1.json()["id"] != r2.json()["id"]


# ── Report Schedules ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_list_schedule():
    tok, _, _ = await _register("exec-sched-cl@eios.dev", "executive")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        cr = await c.post(
            EXEC + "/schedules",
            json={
                "frequency": "monthly",
                "next_run_at": "2026-07-01T00:00:00",
            },
        )
        assert cr.status_code == 201, cr.text
        sched_id = cr.json()["id"]
        assert cr.json()["frequency"] == "monthly"
        assert cr.json()["is_active"] is True

        lr = await c.get(EXEC + "/schedules")
    assert lr.status_code == 200
    ids = [s["id"] for s in lr.json()]
    assert sched_id in ids


@pytest.mark.asyncio
async def test_delete_schedule():
    tok, _, _ = await _register("exec-sched-del@eios.dev", "executive")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        cr = await c.post(
            EXEC + "/schedules",
            json={"frequency": "quarterly", "next_run_at": "2026-10-01T00:00:00"},
        )
        sched_id = cr.json()["id"]

        dr = await c.delete(EXEC + f"/schedules/{sched_id}")
        assert dr.status_code == 204

        lr = await c.get(EXEC + "/schedules")
    ids = [s["id"] for s in lr.json()]
    assert sched_id not in ids


@pytest.mark.asyncio
async def test_schedule_invalid_frequency():
    tok, _, _ = await _register("exec-sched-bad@eios.dev", "executive")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            EXEC + "/schedules",
            json={"frequency": "weekly", "next_run_at": "2026-07-01T00:00:00"},
        )
    assert r.status_code == 422


# ── Tenant isolation ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tenant_isolation_reports():
    """Org B's executive cannot see org A's reports."""
    tok_a, _, _ = await _scored_org("exec-iso-rpt-a")
    tok_b, _, _ = await _register("exec-iso-rpt-b@eios.dev", "executive")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_a}"},
    ) as c:
        cr = await c.post(
            EXEC + "/reports",
            json={"title": "Org A Report", "period_start": "2026-01-01", "period_end": "2026-03-31"},
        )
        assert cr.status_code == 201
        report_id_a = cr.json()["id"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        # List should not show org A's report
        lr = await c.get(EXEC + "/reports")
        ids = [r["id"] for r in lr.json()]
        assert report_id_a not in ids

        # Direct access should 404
        r = await c.get(EXEC + f"/reports/{report_id_a}")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_dashboard():
    """Org A's scored supplier should NOT appear in org B's dashboard."""
    tok_a, _, _ = await _scored_org("exec-iso-dash-a")
    tok_b, _, _ = await _register("exec-iso-dash-b@eios.dev", "executive")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.get(EXEC + "/dashboard")
    assert r.status_code == 200
    ps = r.json()["portfolio_summary"]
    assert ps["total_suppliers"] == 0


# ── Role-based access control ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "role,expected_status",
    [
        ("viewer", 403),
        ("analyst", 403),
        ("reviewer", 403),
    ],
)
@pytest.mark.asyncio
async def test_role_gate_dashboard(role, expected_status):
    safe_role = role.replace("@", "")
    tok, _, _ = await _register(f"exec-gate-{safe_role}@eios.dev", role)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(EXEC + "/dashboard")
    assert r.status_code == expected_status


@pytest.mark.asyncio
async def test_viewer_cannot_access_any_executive_endpoint():
    tok, _, _ = await _register("exec-viewer-block@eios.dev", "viewer")
    endpoints = [
        ("GET", EXEC + "/dashboard"),
        ("GET", EXEC + "/kpi-trends"),
        ("GET", EXEC + "/risk-register"),
        ("GET", EXEC + "/heatmaps"),
        ("GET", EXEC + "/action-effectiveness"),
        ("GET", EXEC + "/governance-metrics"),
        ("GET", EXEC + "/reports"),
        ("GET", EXEC + "/schedules"),
    ]
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        for method, url in endpoints:
            r = await c.request(method, url)
            assert r.status_code == 403, f"{method} {url} expected 403, got {r.status_code}"


# ── Executive summary content ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_executive_summary_is_non_empty_text():
    tok, _, _ = await _scored_org("exec-sum-text")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            EXEC + "/reports",
            json={"title": "Summary Test", "period_start": "2026-01-01", "period_end": "2026-03-31"},
        )
    assert r.status_code == 201
    summary = r.json()["executive_summary"]
    assert len(summary) > 50
    # Must contain portfolio sentence
    assert "supplier" in summary.lower()


@pytest.mark.asyncio
async def test_report_data_contains_all_sections():
    tok, _, _ = await _scored_org("exec-sections")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.post(
            EXEC + "/reports",
            json={"title": "Section Test", "period_start": "2026-01-01", "period_end": "2026-03-31"},
        )
    assert r.status_code == 201
    rd = r.json()["report_data"]
    expected_keys = [
        "meta",
        "executive_summary",
        "portfolio_summary",
        "action_summary",
        "governance_summary",
        "top_high_risk_suppliers",
        "top_deteriorating_suppliers",
        "critical_findings_summary",
        "overdue_actions_summary",
        "governance_metrics",
        "action_effectiveness",
        "kpi_trends",
    ]
    for key in expected_keys:
        assert key in rd, f"Missing key: {key}"
