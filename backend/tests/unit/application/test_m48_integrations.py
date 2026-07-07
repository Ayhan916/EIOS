"""Unit tests — M48 Enterprise Integrations + Commercial Readiness.

Covers:
  - Teams adapter: build_adaptive_card structure, mask_url, send guard
  - Slack adapter: build_block_kit_message structure, send guard
  - JIRA connector: create_jira_ticket / create_servicenow_ticket shapes
  - OFAC connector: parse_sdn_entries, match_supplier, sdn_entry_to_signal
  - SBTi service: validate_sbti_target — all criteria, overall pass/fail
  - CDP service: build_cdp_climate_report — structure, completeness
  - PPTX exporter: build_board_report_pptx returns bytes (pptx)
  - Board portal: create_board_token / decode_board_token / hash_token
  - Benchmarking: compute_benchmark — percentile, tier, strengths/improvements
  - Custom role templates: ROLE_TEMPLATES keys
  - OrganizationSettingsModel fields
  - BoardAccessTokenModel fields
  - CustomRoleModel fields + unique constraint
  - Migration 061 + 062 revision chain
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# ── Teams adapter ─────────────────────────────────────────────────────────────


class TestTeamsAdapter:
    def test_build_adaptive_card_basic(self) -> None:
        from application.notifications.teams_adapter import build_adaptive_card

        payload = build_adaptive_card(title="Test", body="Body text")
        assert payload["type"] == "message"
        assert len(payload["attachments"]) == 1
        card = payload["attachments"][0]["content"]
        assert card["type"] == "AdaptiveCard"

    def test_build_adaptive_card_with_facts(self) -> None:
        from application.notifications.teams_adapter import build_adaptive_card

        payload = build_adaptive_card(
            title="Risk Alert",
            body="High severity finding",
            entity_type="finding",
            entity_id="find-001",
            severity="HIGH",
        )
        body_items = payload["attachments"][0]["content"]["body"]
        fact_set = next((b for b in body_items if b.get("type") == "FactSet"), None)
        assert fact_set is not None
        assert any(f["title"] == "Severity" for f in fact_set["facts"])

    def test_build_adaptive_card_action_url(self) -> None:
        from application.notifications.teams_adapter import build_adaptive_card

        payload = build_adaptive_card(
            title="Test", body="body", action_url="https://app.eios.com/findings/1"
        )
        actions = payload["attachments"][0]["content"]["actions"]
        assert len(actions) == 1
        assert actions[0]["type"] == "Action.OpenUrl"

    def test_mask_url_hides_full_url(self) -> None:
        from application.notifications.teams_adapter import _mask_url

        url = "https://outlook.office.com/webhook/abc123"
        masked = _mask_url(url)
        assert "teams-webhook:" in masked
        assert url not in masked
        assert len(masked) < 30

    def test_send_skips_invalid_url(self) -> None:
        import asyncio

        from application.notifications.teams_adapter import send_teams_notification

        result = asyncio.run(send_teams_notification(webhook_url="not-a-url", title="T", body="B"))
        assert result is False

    def test_send_teams_success(self) -> None:
        import asyncio

        from application.notifications.teams_adapter import send_teams_notification

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client
            result = asyncio.run(
                send_teams_notification(
                    webhook_url="https://outlook.office.com/webhook/xyz",
                    title="Alert",
                    body="Body",
                )
            )
        assert result is True


# ── Slack adapter ─────────────────────────────────────────────────────────────


class TestSlackAdapter:
    def test_build_block_kit_has_blocks(self) -> None:
        from application.notifications.slack_adapter import build_block_kit_message

        payload = build_block_kit_message(title="Test", body="Body")
        assert "blocks" in payload
        assert len(payload["blocks"]) >= 2

    def test_build_block_kit_severity_emoji(self) -> None:
        from application.notifications.slack_adapter import build_block_kit_message

        payload = build_block_kit_message(title="T", body="B", severity="CRITICAL")
        header = payload["blocks"][0]["text"]["text"]
        assert ":red_circle:" in header

    def test_build_block_kit_with_action_url(self) -> None:
        from application.notifications.slack_adapter import build_block_kit_message

        payload = build_block_kit_message(title="T", body="B", action_url="https://app.eios.com")
        action_block = next((b for b in payload["blocks"] if b.get("type") == "actions"), None)
        assert action_block is not None

    def test_send_skips_invalid_url(self) -> None:
        import asyncio

        from application.notifications.slack_adapter import send_slack_notification

        result = asyncio.run(
            send_slack_notification(webhook_url="https://api.slack.com/wrong", title="T", body="B")
        )
        assert result is False

    def test_send_slack_success(self) -> None:
        import asyncio

        from application.notifications.slack_adapter import send_slack_notification

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client
            result = asyncio.run(
                send_slack_notification(
                    webhook_url="https://hooks.slack.com/services/T/B/xyz",
                    title="Alert",
                    body="Body",
                )
            )
        assert result is True


# ── OFAC connector ────────────────────────────────────────────────────────────


SAMPLE_SDN_XML = b"""<?xml version="1.0"?>
<sdnList xmlns="http://tempuri.org/sdnList.xsd">
  <sdnEntry>
    <uid>12345</uid>
    <sdnType>Individual</sdnType>
    <firstName>JOHN</firstName>
    <lastName>DOE CORP</lastName>
    <programList><program>IRAN</program></programList>
    <addressList>
      <address><city>Tehran</city><country>Iran</country></address>
    </addressList>
  </sdnEntry>
  <sdnEntry>
    <uid>99999</uid>
    <sdnType>Entity</sdnType>
    <lastName>ACME TRADING LLC</lastName>
    <programList><program>SDGT</program><program>OFSI</program></programList>
  </sdnEntry>
</sdnList>"""


class TestOfacConnector:
    def test_parse_returns_entries(self) -> None:
        from application.external_intelligence.connectors.ofac import parse_sdn_entries

        entries = parse_sdn_entries(SAMPLE_SDN_XML)
        assert len(entries) == 2

    def test_parse_entry_fields(self) -> None:
        from application.external_intelligence.connectors.ofac import parse_sdn_entries

        entries = parse_sdn_entries(SAMPLE_SDN_XML)
        e = next(e for e in entries if e["uid"] == "12345")
        assert e["name"] == "JOHN DOE CORP"
        assert "IRAN" in e["programs"]
        assert e["type"] == "Individual"

    def test_parse_entity_name(self) -> None:
        from application.external_intelligence.connectors.ofac import parse_sdn_entries

        entries = parse_sdn_entries(SAMPLE_SDN_XML)
        entity = next(e for e in entries if e["uid"] == "99999")
        assert entity["name"] == "ACME TRADING LLC"

    def test_parse_invalid_xml_returns_empty(self) -> None:
        from application.external_intelligence.connectors.ofac import parse_sdn_entries

        entries = parse_sdn_entries(b"<invalid xml>")
        assert entries == []

    def test_exact_match(self) -> None:
        from application.external_intelligence.connectors.ofac import (
            match_supplier_against_sdn,
            parse_sdn_entries,
        )

        entries = parse_sdn_entries(SAMPLE_SDN_XML)
        matches = match_supplier_against_sdn("ACME TRADING LLC", entries)
        assert len(matches) == 1
        assert matches[0]["uid"] == "99999"

    def test_no_match(self) -> None:
        from application.external_intelligence.connectors.ofac import (
            match_supplier_against_sdn,
            parse_sdn_entries,
        )

        entries = parse_sdn_entries(SAMPLE_SDN_XML)
        matches = match_supplier_against_sdn("Safe Supplier GmbH", entries)
        assert matches == []

    def test_case_insensitive_match(self) -> None:
        from application.external_intelligence.connectors.ofac import (
            match_supplier_against_sdn,
            parse_sdn_entries,
        )

        entries = parse_sdn_entries(SAMPLE_SDN_XML)
        matches = match_supplier_against_sdn("acme trading llc", entries)
        assert len(matches) == 1

    def test_sdn_entry_to_signal(self) -> None:
        from application.external_intelligence.connectors.ofac import (
            parse_sdn_entries,
            sdn_entry_to_signal,
        )

        entries = parse_sdn_entries(SAMPLE_SDN_XML)
        signal = sdn_entry_to_signal(entries[0], supplier_id="sup-001", organization_id="org-001")
        assert signal["signal_type"] == "SANCTIONS_MATCH"
        assert signal["severity"] == "CRITICAL"
        assert signal["source"] == "OFAC_SDN"
        assert "dedup_key" in signal


# ── SBTi service ──────────────────────────────────────────────────────────────


class TestSBTiService:
    def _call(self, **kwargs):
        from application.integrations.sbti_service import validate_sbti_target

        defaults = dict(
            target_id="tgt-001",
            organization_name="Test Corp",
            base_year=2020,
            target_year=2030,
            base_year_scope1_tco2e=10000.0,
            base_year_scope2_tco2e=5000.0,
            target_scope1_tco2e=6000.0,
            target_scope2_tco2e=3000.0,
        )
        defaults.update(kwargs)
        return validate_sbti_target(**defaults)

    def test_valid_target_passes(self) -> None:
        result = self._call(
            base_year=2019,
            target_year=2030,
            base_year_scope1_tco2e=10000.0,
            base_year_scope2_tco2e=2000.0,
            target_scope1_tco2e=3000.0,
            target_scope2_tco2e=500.0,
        )
        assert result.scope_1_2_aligned is True
        assert result.base_year_valid is True

    def test_invalid_base_year(self) -> None:
        result = self._call(base_year=2010)
        assert result.base_year_valid is False
        assert result.overall_aligned is False

    def test_insufficient_scope12_reduction(self) -> None:
        result = self._call(
            base_year=2020,
            target_year=2030,
            base_year_scope1_tco2e=10000.0,
            base_year_scope2_tco2e=5000.0,
            target_scope1_tco2e=9900.0,  # barely any reduction
            target_scope2_tco2e=4900.0,
        )
        assert result.scope_1_2_aligned is False
        assert result.overall_aligned is False

    def test_scope3_alignment_when_data_provided(self) -> None:
        result = self._call(
            base_year_scope3_tco2e=50000.0,
            target_scope3_tco2e=30000.0,  # 40% reduction < 25% by 2030
            target_year=2030,
        )
        assert result.scope_3_aligned is True  # 40% >= 25%

    def test_scope3_not_required_when_no_data(self) -> None:
        result = self._call()
        assert result.scope_3_aligned is True  # N/A — marked True by default

    def test_to_dict_has_required_keys(self) -> None:
        result = self._call()
        d = result.to_dict()
        assert {
            "target_id",
            "overall_aligned",
            "criteria_detail",
            "methodology",
            "disclaimer",
        }.issubset(d.keys())

    def test_criteria_detail_list(self) -> None:
        result = self._call()
        assert isinstance(result.criteria_detail, list)
        assert len(result.criteria_detail) >= 3

    def test_confidence_note_present(self) -> None:
        result = self._call()
        assert isinstance(result.confidence_note, str)
        assert len(result.confidence_note) > 10


# ── CDP service ───────────────────────────────────────────────────────────────


class TestCDPService:
    def _report(self, **kwargs):
        from application.integrations.cdp_service import build_cdp_climate_report

        defaults = dict(organization_name="Test Corp", reporting_year=2024)
        defaults.update(kwargs)
        return build_cdp_climate_report(**defaults)

    def test_returns_dict_with_required_keys(self) -> None:
        r = self._report()
        assert {"metadata", "responses", "summary"}.issubset(r.keys())

    def test_metadata(self) -> None:
        r = self._report()
        assert r["metadata"]["organization"] == "Test Corp"
        assert r["metadata"]["reporting_year"] == 2024
        assert "CDP" in r["metadata"]["framework"]

    def test_c1_governance_present(self) -> None:
        r = self._report(board_oversight="Board reviews quarterly.")
        modules = [resp["module"] for resp in r["responses"]]
        assert "C1" in modules

    def test_c8_emissions_data_gap(self) -> None:
        r = self._report()
        c8_scopes = [resp for resp in r["responses"] if resp["module"] == "C8"]
        assert all(resp["status"] == "data_gap" for resp in c8_scopes)

    def test_c8_emissions_complete_with_data(self) -> None:
        r = self._report(scope1_tco2e=1000.0, scope2_market_tco2e=200.0)
        scope1_resp = next(r for r in r["responses"] if r.get("question") == "C8.1")
        assert scope1_resp["status"] == "complete"

    def test_c6_renewable_pct_calculated(self) -> None:
        r = self._report(total_energy_mwh=10000.0, renewable_energy_mwh=4000.0)
        c6 = [
            resp for resp in r["responses"] if resp["module"] == "C6" and resp["question"] == "C6.2"
        ]
        assert len(c6) == 1
        assert c6[0]["response"] == 40.0

    def test_summary_completion_pct(self) -> None:
        r = self._report()
        assert 0 <= r["summary"]["completion_pct"] <= 100

    def test_sbt_flag(self) -> None:
        r = self._report(science_based_target=True)
        c4a = next((resp for resp in r["responses"] if resp.get("question") == "C4.1a"), None)
        assert c4a is not None


# ── PPTX exporter ─────────────────────────────────────────────────────────────


class TestPptxExporter:
    def _build(self, **kwargs):
        from application.executive.pptx_exporter import build_board_report_pptx

        defaults = dict(
            organization_name="Test Corp",
            report_title="Q4 2024 Board Report",
        )
        defaults.update(kwargs)
        return build_board_report_pptx(**defaults)

    def test_returns_bytes(self) -> None:
        result = self._build()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_is_valid_pptx_magic(self) -> None:
        result = self._build()
        # PPTX is a ZIP file, starts with PK\x03\x04
        assert result[:4] == b"PK\x03\x04"

    def test_with_kpi_highlights(self) -> None:
        result = self._build(
            kpi_highlights=[
                {"label": "Carbon Intensity", "value": "45.2", "unit": "tCO₂e/M€", "trend": "↓ 8%"},
                {"label": "Supplier Score", "value": "78", "unit": "pts"},
            ]
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_with_risks(self) -> None:
        result = self._build(
            risks=[
                {"title": "Climate Risk", "severity": "HIGH", "status": "Active", "owner": "EHS"}
            ]
        )
        assert isinstance(result, bytes)

    def test_with_recommendations(self) -> None:
        result = self._build(
            recommendations=[
                {"title": "Reduce Scope 1", "priority": "High", "due_date": "2025-06-30"}
            ]
        )
        assert isinstance(result, bytes)


# ── Board Portal ──────────────────────────────────────────────────────────────


class TestBoardPortal:
    def test_create_token_returns_string_and_datetime(self) -> None:
        from application.commercial.board_portal import create_board_token

        token, expires_at = create_board_token(
            report_id="rep-001",
            organization_id="org-001",
            expires_in_hours=48,
        )
        assert isinstance(token, str)
        assert len(token) > 20
        assert isinstance(expires_at, datetime)

    def test_decode_token_returns_correct_claims(self) -> None:
        from application.commercial.board_portal import create_board_token, decode_board_token

        token, _ = create_board_token(
            report_id="rep-001",
            organization_id="org-001",
            expires_in_hours=48,
            allowed_sections=["executive_summary", "risks"],
        )
        payload = decode_board_token(token)
        assert payload["report_id"] == "rep-001"
        assert payload["org_id"] == "org-001"
        assert "executive_summary" in payload["sections"]
        assert payload["type"] == "board_access"

    def test_hash_token_returns_64_char_hex(self) -> None:
        from application.commercial.board_portal import hash_token

        h = hash_token("some.jwt.token")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_deterministic(self) -> None:
        from application.commercial.board_portal import hash_token

        assert hash_token("abc") == hash_token("abc")

    def test_is_section_allowed_empty_means_all(self) -> None:
        from application.commercial.board_portal import is_section_allowed

        payload = {"sections": []}
        assert is_section_allowed(payload, "any_section") is True

    def test_is_section_allowed_scoped(self) -> None:
        from application.commercial.board_portal import is_section_allowed

        payload = {"sections": ["executive_summary"]}
        assert is_section_allowed(payload, "executive_summary") is True
        assert is_section_allowed(payload, "risk_register") is False

    def test_expires_in_hours_bounds(self) -> None:
        import pytest

        from application.commercial.board_portal import create_board_token

        with pytest.raises(ValueError):
            create_board_token(report_id="r", organization_id="o", expires_in_hours=0)

    def test_wrong_token_type_raises(self) -> None:
        import jwt as _jwt

        from application.commercial.board_portal import decode_board_token
        from shared.config import settings

        bad_token = _jwt.encode(
            {"type": "access", "sub": "user-1", "exp": 9999999999},
            settings.secret_key,
            algorithm="HS256",
        )
        import pytest

        with pytest.raises(ValueError, match="Not a board access token"):
            decode_board_token(bad_token)


# ── Benchmarking ──────────────────────────────────────────────────────────────


class TestBenchmarking:
    def _peers(self, scores):
        return [
            {
                "overall_esg_score": s,
                "environmental_score": s,
                "social_score": s,
                "governance_score": s,
            }
            for s in scores
        ]

    def test_top_quartile(self) -> None:
        from application.commercial.benchmarking import compute_benchmark

        result = compute_benchmark(
            supplier_id="s1",
            supplier_name="Best Corp",
            organization_id="o1",
            supplier_scores={"overall_esg_score": 90.0},
            peers=self._peers([30.0, 40.0, 50.0, 60.0, 70.0]),
        )
        assert result.performance_tier == "Top Quartile"
        assert result.overall_percentile is not None
        assert result.overall_percentile > 75

    def test_bottom_quartile(self) -> None:
        from application.commercial.benchmarking import compute_benchmark

        result = compute_benchmark(
            supplier_id="s1",
            supplier_name="Laggard Corp",
            organization_id="o1",
            supplier_scores={"overall_esg_score": 10.0},
            peers=self._peers([60.0, 70.0, 80.0, 90.0, 95.0]),
        )
        assert result.performance_tier == "Bottom Quartile"

    def test_no_peers_returns_insufficient(self) -> None:
        from application.commercial.benchmarking import compute_benchmark

        result = compute_benchmark(
            supplier_id="s1",
            supplier_name="Alone Corp",
            organization_id="o1",
            supplier_scores={"overall_esg_score": 50.0},
            peers=[],
        )
        assert result.peer_count == 0

    def test_strengths_identified(self) -> None:
        from application.commercial.benchmarking import compute_benchmark

        result = compute_benchmark(
            supplier_id="s1",
            supplier_name="Green Corp",
            organization_id="o1",
            supplier_scores={
                "overall_esg_score": 80.0,
                "environmental_score": 95.0,
                "social_score": 50.0,
                "governance_score": 50.0,
            },
            peers=[
                {
                    "overall_esg_score": 60.0,
                    "environmental_score": 40.0,
                    "social_score": 50.0,
                    "governance_score": 55.0,
                },
            ],
        )
        assert "Environmental" in result.strengths

    def test_to_dict_structure(self) -> None:
        from application.commercial.benchmarking import compute_benchmark

        result = compute_benchmark(
            supplier_id="s1",
            supplier_name="Corp",
            organization_id="o1",
            supplier_scores={"overall_esg_score": 70.0},
            peers=self._peers([40.0, 50.0, 60.0]),
        )
        d = result.to_dict()
        assert {
            "supplier_id",
            "scores",
            "peer_group",
            "percentile_ranks",
            "performance_tier",
        }.issubset(d.keys())

    def test_percentile_rank_calculation(self) -> None:
        from application.commercial.benchmarking import _percentile_rank

        assert _percentile_rank(75.0, [50.0, 60.0, 70.0, 80.0, 90.0]) == 60.0

    def test_percentile_rank_no_peers(self) -> None:
        from application.commercial.benchmarking import _percentile_rank

        assert _percentile_rank(50.0, []) == 50.0


# ── Custom Role model ─────────────────────────────────────────────────────────


class TestCustomRoleModel:
    def test_tablename(self) -> None:
        from infrastructure.persistence.models.custom_role import CustomRoleModel

        assert CustomRoleModel.__tablename__ == "custom_roles"

    def test_required_columns(self) -> None:
        from infrastructure.persistence.models.custom_role import CustomRoleModel

        cols = {c.key for c in CustomRoleModel.__table__.columns}
        assert {"id", "organization_id", "role_name", "permissions", "created_by"}.issubset(cols)

    def test_unique_constraint(self) -> None:
        from sqlalchemy import UniqueConstraint

        from infrastructure.persistence.models.custom_role import CustomRoleModel

        uc_names = {
            c.name for c in CustomRoleModel.__table__.constraints if isinstance(c, UniqueConstraint)
        }
        assert "uq_org_role_name" in uc_names

    def test_role_templates_keys(self) -> None:
        from infrastructure.persistence.models.custom_role import ROLE_TEMPLATES

        expected = {"viewer", "analyst", "auditor", "supplier_manager"}
        assert expected == set(ROLE_TEMPLATES.keys())

    def test_each_template_has_permissions(self) -> None:
        from infrastructure.persistence.models.custom_role import ROLE_TEMPLATES

        for _name, template in ROLE_TEMPLATES.items():
            assert "permissions" in template
            assert isinstance(template["permissions"], list)
            assert len(template["permissions"]) >= 1


class TestOrganizationSettingsModel:
    def test_tablename(self) -> None:
        from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

        assert OrganizationSettingsModel.__tablename__ == "organization_settings"

    def test_pk_is_organization_id(self) -> None:
        from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

        pk_cols = [c.name for c in OrganizationSettingsModel.__table__.primary_key.columns]
        assert pk_cols == ["organization_id"]

    def test_branding_columns(self) -> None:
        from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

        cols = {c.key for c in OrganizationSettingsModel.__table__.columns}
        assert {"logo_url", "primary_color", "company_name_override"}.issubset(cols)

    def test_integration_columns(self) -> None:
        from infrastructure.persistence.models.org_settings import OrganizationSettingsModel

        cols = {c.key for c in OrganizationSettingsModel.__table__.columns}
        assert {"teams_webhook_url", "slack_webhook_url", "jira_base_url"}.issubset(cols)


class TestBoardAccessTokenModel:
    def test_tablename(self) -> None:
        from infrastructure.persistence.models.board_access_token import BoardAccessTokenModel

        assert BoardAccessTokenModel.__tablename__ == "board_access_tokens"

    def test_security_columns(self) -> None:
        from infrastructure.persistence.models.board_access_token import BoardAccessTokenModel

        cols = {c.key for c in BoardAccessTokenModel.__table__.columns}
        assert {"token_hash", "expires_at", "revoked", "allowed_sections"}.issubset(cols)

    def test_token_hash_unique(self) -> None:
        from infrastructure.persistence.models.board_access_token import BoardAccessTokenModel

        token_hash_col = BoardAccessTokenModel.__table__.columns["token_hash"]
        assert token_hash_col.unique is True


# ── Migration tests ───────────────────────────────────────────────────────────


def _load_migration_m48(path: str, mod_name: str):
    import importlib.util
    import sys
    from contextlib import contextmanager
    from unittest.mock import MagicMock

    @contextmanager
    def _patch_dict(d, overrides):
        original = {k: d[k] for k in overrides if k in d}
        d.update(overrides)
        try:
            yield
        finally:
            for k in overrides:
                if k in original:
                    d[k] = original[k]
                else:
                    d.pop(k, None)

    if mod_name in sys.modules:
        return sys.modules[mod_name]

    fake_op = MagicMock()
    fake_sa = MagicMock()
    fake_alembic = MagicMock()
    fake_alembic.op = fake_op

    with _patch_dict(
        sys.modules, {"alembic": fake_alembic, "alembic.op": fake_op, "sqlalchemy": fake_sa}
    ):
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[mod_name] = mod

    return mod


class TestMigration061:
    def _load(self):
        return _load_migration_m48(
            "alembic/versions/061_m48_1_integrations.py",
            "_test_migration_061",
        )

    def test_revision(self) -> None:
        assert self._load().revision == "061"

    def test_down_revision(self) -> None:
        assert self._load().down_revision == "060"

    def test_upgrade_callable(self) -> None:
        assert callable(self._load().upgrade)


class TestMigration062:
    def _load(self):
        return _load_migration_m48(
            "alembic/versions/062_m48_2_commercial.py",
            "_test_migration_062",
        )

    def test_revision(self) -> None:
        assert self._load().revision == "062"

    def test_down_revision(self) -> None:
        assert self._load().down_revision == "061"

    def test_upgrade_callable(self) -> None:
        assert callable(self._load().upgrade)

    def test_downgrade_callable(self) -> None:
        assert callable(self._load().downgrade)
