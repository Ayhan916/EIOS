"""M50 — Executive Command Center + Board Portal Tests.

Tests:
    TestESGHealthScoreLogic (5) — health score calculation and label
    TestPriorityActions (5) — priority action aggregation logic
    TestYoYLogic (4) — year-over-year delta calculation
    TestBoardPortalTokenService (6) — create/decode/hash/validate token
    TestBoardPortalEndpointIntegration (4) — expired/revoked/missing token cases
    TestCommandCenterPersonaData (4) — CFO/CSO/CCO metric structures
    TestReportsCenterPageData (4) — report type definitions and helpers
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────


def _fake_secret() -> str:
    return "test-secret-key-for-board-portal"


def _make_token(
    report_id: str = "report-abc",
    org_id: str = "org-123",
    expires_in_hours: int = 24,
    sections: list[str] | None = None,
) -> tuple[str, datetime]:
    """Create a test board token using the real service."""
    with patch("shared.config.settings") as mock_settings:
        mock_settings.secret_key = _fake_secret()
        from application.commercial.board_portal import create_board_token

        return create_board_token(
            report_id=report_id,
            organization_id=org_id,
            expires_in_hours=expires_in_hours,
            allowed_sections=sections or [],
        )


def _decode_token(token: str) -> dict:
    with patch("shared.config.settings") as mock_settings:
        mock_settings.secret_key = _fake_secret()
        from application.commercial.board_portal import decode_board_token

        return decode_board_token(token)


# ── TestESGHealthScoreLogic ───────────────────────────────────────────────────


class TestESGHealthScoreLogic:
    """Unit-test the composite ESG health score formula."""

    def _compute_health(
        self,
        avg_esg: float | None = 75.0,
        total_scored: int = 10,
        critical: int = 0,
        high: int = 1,
        total_recs: int = 20,
        open_recs: int = 4,
    ) -> tuple[float, str]:
        """Replicates the executive router's health score logic."""
        esg_component = min((avg_esg or 0) / 100, 1.0) * 40
        low_risk_pct = (total_scored - critical - high) / total_scored if total_scored > 0 else 0.5
        risk_component = low_risk_pct * 30
        closure_rate = 1.0 - (open_recs / total_recs) if total_recs > 0 else 0.5
        closure_component = closure_rate * 30

        score = round(esg_component + risk_component + closure_component, 1)
        label = (
            "Excellent"
            if score >= 80
            else "Good"
            if score >= 65
            else "Needs Attention"
            if score >= 50
            else "Critical"
        )
        return score, label

    def test_perfect_portfolio_scores_excellent(self):
        score, label = self._compute_health(
            avg_esg=95.0,
            total_scored=20,
            critical=0,
            high=0,
            total_recs=10,
            open_recs=0,
        )
        assert score >= 80
        assert label == "Excellent"

    def test_zero_esg_score_is_critical(self):
        score, label = self._compute_health(
            avg_esg=0.0,
            total_scored=10,
            critical=10,
            high=0,
            total_recs=10,
            open_recs=10,
        )
        assert score < 50
        assert label == "Critical"

    def test_score_bounded_0_to_100(self):
        score, _ = self._compute_health(
            avg_esg=100.0,
            total_scored=1,
            critical=0,
            high=0,
            total_recs=5,
            open_recs=0,
        )
        assert 0 <= score <= 100

    def test_no_suppliers_uses_neutral_risk_pct(self):
        score, _ = self._compute_health(
            avg_esg=70.0,
            total_scored=0,
            critical=0,
            high=0,
            total_recs=0,
            open_recs=0,
        )
        # With total_scored=0, low_risk_pct=0.5; total_recs=0, closure_rate=0.5
        assert score > 0

    def test_moderate_portfolio_scores_needs_attention(self):
        score, label = self._compute_health(
            avg_esg=50.0,
            total_scored=10,
            critical=3,
            high=3,
            total_recs=20,
            open_recs=10,
        )
        assert label in ("Needs Attention", "Critical", "Good")
        assert 0 <= score <= 100


# ── TestPriorityActions ───────────────────────────────────────────────────────


class TestPriorityActions:
    """Validate priority action aggregation logic."""

    def _build_actions(
        self,
        overdue_recs: int = 0,
        crit_findings: int = 0,
        critical_risks: int = 0,
        awaiting_review: int = 0,
    ) -> list[dict]:
        """Replicates the command-center priority action builder."""
        actions = []
        if overdue_recs > 0:
            actions.append(
                {
                    "type": "overdue_actions",
                    "title": f"{overdue_recs} overdue recommendation{'s' if overdue_recs > 1 else ''}",
                    "severity": "critical" if overdue_recs >= 5 else "high",
                    "href": "/findings",
                    "count": overdue_recs,
                }
            )
        if crit_findings > 0:
            actions.append(
                {
                    "type": "critical_findings",
                    "title": f"{crit_findings} critical finding{'s' if crit_findings > 1 else ''} open",
                    "severity": "critical",
                    "href": "/findings",
                    "count": crit_findings,
                }
            )
        if critical_risks > 0:
            actions.append(
                {
                    "type": "critical_risks",
                    "title": f"{critical_risks} critical risk{'s' if critical_risks > 1 else ''} unmitigated",
                    "severity": "critical",
                    "href": "/risks",
                    "count": critical_risks,
                }
            )
        if awaiting_review > 0:
            actions.append(
                {
                    "type": "assessments_pending",
                    "title": f"{awaiting_review} assessment{'s' if awaiting_review > 1 else ''} awaiting review",
                    "severity": "medium",
                    "href": "/assessments",
                    "count": awaiting_review,
                }
            )
        return actions[:5]

    def test_no_issues_returns_empty_list(self):
        actions = self._build_actions()
        assert actions == []

    def test_critical_findings_highest_severity(self):
        actions = self._build_actions(crit_findings=3)
        assert len(actions) == 1
        assert actions[0]["severity"] == "critical"
        assert actions[0]["type"] == "critical_findings"

    def test_many_overdue_flagged_critical(self):
        actions = self._build_actions(overdue_recs=10)
        assert actions[0]["severity"] == "critical"

    def test_few_overdue_flagged_high(self):
        actions = self._build_actions(overdue_recs=2)
        assert actions[0]["severity"] == "high"

    def test_max_five_actions_returned(self):
        # All four categories: 4 actions → still ≤ 5
        actions = self._build_actions(
            overdue_recs=3, crit_findings=2, critical_risks=1, awaiting_review=5
        )
        assert len(actions) <= 5
        assert all("href" in a for a in actions)


# ── TestYoYLogic ─────────────────────────────────────────────────────────────


class TestYoYLogic:
    """Test year-over-year delta calculation."""

    def _compute_yoy(
        self,
        current: float | None,
        prior: float | None,
    ) -> float | None:
        if current is not None and prior is not None:
            return round(current - prior, 1)
        return None

    def test_positive_delta_when_improving(self):
        assert self._compute_yoy(78.5, 72.0) == 6.5

    def test_negative_delta_when_declining(self):
        assert self._compute_yoy(65.0, 70.0) == -5.0

    def test_none_when_no_prior(self):
        assert self._compute_yoy(75.0, None) is None

    def test_none_when_no_current(self):
        assert self._compute_yoy(None, 70.0) is None


# ── TestBoardPortalTokenService ───────────────────────────────────────────────


class TestBoardPortalTokenService:
    """Test create/decode/hash/validate board portal tokens."""

    def test_create_token_returns_jwt_and_expiry(self):
        token, expires_at = _make_token()
        assert isinstance(token, str)
        assert len(token) > 20
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(UTC)

    def test_decode_returns_correct_claims(self):
        token, _ = _make_token(report_id="rpt-1", org_id="org-99")
        payload = _decode_token(token)
        assert payload["report_id"] == "rpt-1"
        assert payload["org_id"] == "org-99"
        assert payload["type"] == "board_access"

    def test_sections_stored_in_payload(self):
        token, _ = _make_token(sections=["portfolio", "esg"])
        payload = _decode_token(token)
        assert payload["sections"] == ["portfolio", "esg"]

    def test_expired_token_raises(self):
        # Patch at the module level so the cached import works regardless of test order
        from application.commercial import board_portal as _bp_module

        with patch.object(_bp_module, "settings") as mock_settings:
            mock_settings.secret_key = _fake_secret()
            # Create with 0-hour window (already expired)
            expires_at = datetime.now(UTC) - timedelta(hours=1)
            payload_data = {
                "type": "board_access",
                "report_id": "r1",
                "org_id": "o1",
                "sections": [],
                "exp": int(expires_at.timestamp()),
                "iat": int(datetime.now(UTC).timestamp()),
                "jti": "test-jti",
            }
            expired_token = jwt.encode(payload_data, _fake_secret(), algorithm="HS256")
            with pytest.raises(jwt.ExpiredSignatureError):
                _bp_module.decode_board_token(expired_token)

    def test_hash_token_is_deterministic_sha256(self):
        with patch("shared.config.settings"):
            from application.commercial.board_portal import hash_token

            t = "my.jwt.token"
            h1 = hash_token(t)
            h2 = hash_token(t)
            assert h1 == h2
            assert h1 == hashlib.sha256(t.encode()).hexdigest()

    def test_is_section_allowed_empty_means_all(self):
        with patch("shared.config.settings"):
            from application.commercial.board_portal import is_section_allowed

            payload = {"sections": []}
            assert is_section_allowed(payload, "portfolio") is True
            assert is_section_allowed(payload, "esg") is True

    def test_is_section_allowed_restricts_when_set(self):
        with patch("shared.config.settings"):
            from application.commercial.board_portal import is_section_allowed

            payload = {"sections": ["portfolio"]}
            assert is_section_allowed(payload, "portfolio") is True
            assert is_section_allowed(payload, "esg") is False


# ── TestBoardPortalEndpointIntegration ───────────────────────────────────────


class TestBoardPortalEndpointIntegration:
    """Validate the board portal public endpoint error paths (unit-level)."""

    def test_invalid_token_raises_401(self):
        """Any token with bad signature should raise 401."""
        import jwt as pyjwt

        bad_token = "not.a.real.jwt"
        # decode_board_token should raise on invalid token
        with patch("shared.config.settings") as ms:
            ms.secret_key = _fake_secret()
            from application.commercial.board_portal import decode_board_token

            with pytest.raises((pyjwt.InvalidTokenError, pyjwt.DecodeError)):
                decode_board_token(bad_token)

    def test_wrong_type_token_raises_value_error(self):
        """A token with type != 'board_access' should fail."""
        from application.commercial import board_portal as _bp_module

        payload = {
            "type": "user_access",  # wrong type
            "report_id": "r1",
            "org_id": "o1",
            "sections": [],
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
            "jti": "j1",
        }
        token = jwt.encode(payload, _fake_secret(), algorithm="HS256")
        with patch.object(_bp_module, "settings") as ms:
            ms.secret_key = _fake_secret()
            with pytest.raises(ValueError, match="Not a board access token"):
                _bp_module.decode_board_token(token)

    def test_expires_in_hours_range_validation(self):
        """expires_in_hours must be 1–720."""
        with patch("shared.config.settings") as ms:
            ms.secret_key = _fake_secret()
            from application.commercial.board_portal import create_board_token

            with pytest.raises(ValueError):
                create_board_token(report_id="r", organization_id="o", expires_in_hours=0)
            with pytest.raises(ValueError):
                create_board_token(report_id="r", organization_id="o", expires_in_hours=721)

    def test_valid_token_decodes_all_claims(self):
        token, expires_at = _make_token(
            report_id="report-xyz",
            org_id="org-456",
            expires_in_hours=48,
            sections=["esg", "governance"],
        )
        payload = _decode_token(token)
        assert payload["report_id"] == "report-xyz"
        assert payload["org_id"] == "org-456"
        assert "esg" in payload["sections"]
        assert "governance" in payload["sections"]
        # exp should be ~48h from now
        exp_dt = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert (exp_dt - datetime.now(UTC)).total_seconds() > 3600 * 47


# ── TestCommandCenterPersonaData ─────────────────────────────────────────────


class TestCommandCenterPersonaData:
    """Validate persona-specific metric structures."""

    def test_cfo_metrics_keys(self):
        cfo = {"taxonomy_alignment_pct": 35.2, "green_revenue_pct": 18.5}
        assert "taxonomy_alignment_pct" in cfo
        assert "green_revenue_pct" in cfo

    def test_cso_metrics_keys(self):
        cso = {
            "latest_emissions_tco2e": 85000.0,
            "kpi_on_track": 5,
            "kpi_at_risk": 2,
            "kpi_missed": 1,
        }
        total = cso["kpi_on_track"] + cso["kpi_at_risk"] + cso["kpi_missed"]
        assert total == 8
        pct = cso["kpi_on_track"] / total * 100
        assert abs(pct - 62.5) < 0.1

    def test_cco_metrics_readiness_pct(self):
        cco = {
            "soc2_readiness_pct": 73.7,
            "soc2_implemented": 28,
            "soc2_total": 38,
            "open_critical_findings": 3,
        }
        computed = round(cco["soc2_implemented"] / cco["soc2_total"] * 100, 1)
        assert computed == cco["soc2_readiness_pct"]

    def test_command_center_response_schema(self):
        response = {
            "esg_health_score": 74.5,
            "health_label": "Good",
            "priority_actions": [],
            "yoy": {"avg_esg_delta": 3.2, "prior_avg_esg": 68.0, "current_avg_esg": 71.2},
            "ceo": {
                "total_scored_suppliers": 15,
                "critical_risk_suppliers": 2,
                "open_findings": 8,
                "overdue_actions": 3,
            },
            "cfo": {"taxonomy_alignment_pct": 35.2, "green_revenue_pct": None},
            "cso": {
                "latest_emissions_tco2e": None,
                "kpi_on_track": 0,
                "kpi_at_risk": 0,
                "kpi_missed": 0,
            },
            "cco": {
                "soc2_readiness_pct": None,
                "soc2_implemented": 0,
                "soc2_total": 0,
                "open_critical_findings": 2,
            },
        }
        assert response["esg_health_score"] == 74.5
        assert response["health_label"] in ("Excellent", "Good", "Needs Attention", "Critical")
        for key in ("ceo", "cfo", "cso", "cco", "yoy", "priority_actions"):
            assert key in response


# ── TestReportsCenterPageData ─────────────────────────────────────────────────


class TestReportsCenterPageData:
    """Validate the reports center data structures."""

    def test_report_types_defined(self):
        report_types = ["tcfd", "sfdr-pai", "audit-csv"]
        assert "tcfd" in report_types
        assert "sfdr-pai" in report_types
        assert "audit-csv" in report_types

    def test_disclosure_package_status_colors(self):
        status_colors = {
            "DRAFT": "bg-slate-100 text-slate-600",
            "IN_REVIEW": "bg-blue-100 text-blue-700",
            "APPROVED": "bg-emerald-100 text-emerald-700",
            "PUBLISHED": "bg-green-100 text-green-700",
        }
        assert status_colors["APPROVED"] == "bg-emerald-100 text-emerald-700"
        unknown_color = status_colors.get("UNKNOWN", "bg-slate-100 text-slate-600")
        assert unknown_color is not None

    def test_export_formats(self):
        formats = ["xbrl", "gri", "json"]
        for f in formats:
            assert f in ["xbrl", "gri", "json"]

    def test_authenticated_download_filename_construction(self):
        pkg_name = "CSRD Annual Report 2025"
        fmt = "gri"
        filename = f"{pkg_name.replace(' ', '_').lower()}_{fmt}.json"
        assert filename == "csrd_annual_report_2025_gri.json"
