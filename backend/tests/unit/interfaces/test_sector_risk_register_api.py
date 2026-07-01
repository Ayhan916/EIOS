"""Tests for CSDDD Sector Risk Register API endpoints (TASK-003 Phase 6)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from interfaces.api.routers.sector_risk_register import router


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# GET / — list sectors
# ---------------------------------------------------------------------------

class TestListSectors:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/")
        assert resp.status_code == 200

    def test_returns_list(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_calibrated_only_filter(self, client: TestClient) -> None:
        all_data = client.get("/sector-risk-register/").json()
        cal_data = client.get("/sector-risk-register/?calibrated_only=true").json()
        assert len(cal_data) <= len(all_data)
        assert len(cal_data) == 20  # exactly the 20 curated sectors

    def test_each_item_has_required_fields(self, client: TestClient) -> None:
        items = client.get("/sector-risk-register/?calibrated_only=true").json()
        required = {
            "nace_code", "nace_section", "sector_name",
            "is_calibrated", "highest_probability",
            "average_probability", "rights_above_7",
        }
        for item in items:
            assert required <= set(item.keys()), f"Missing fields in {item}"

    def test_automotive_in_list(self, client: TestClient) -> None:
        items = client.get("/sector-risk-register/?calibrated_only=true").json()
        codes = [i["nace_code"] for i in items]
        assert "29" in codes

    def test_probability_values_in_range(self, client: TestClient) -> None:
        items = client.get("/sector-risk-register/?calibrated_only=true").json()
        for item in items:
            assert 1 <= item["highest_probability"] <= 10
            assert 1.0 <= item["average_probability"] <= 10.0


# ---------------------------------------------------------------------------
# GET /scenarios/templates
# ---------------------------------------------------------------------------

class TestScenarioTemplates:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/scenarios/templates")
        assert resp.status_code == 200

    def test_returns_6_templates(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/scenarios/templates").json()
        assert len(data) == 6

    def test_each_template_has_required_fields(self, client: TestClient) -> None:
        templates = client.get("/sector-risk-register/scenarios/templates").json()
        required = {
            "scenario_type", "name", "description",
            "affected_nace_sections", "sources", "affected_rights_count",
        }
        for t in templates:
            assert required <= set(t.keys())

    def test_expected_scenario_types_present(self, client: TestClient) -> None:
        templates = client.get("/sector-risk-register/scenarios/templates").json()
        types = {t["scenario_type"] for t in templates}
        assert "geopolitical_conflict" in types
        assert "labour_unrest" in types
        assert "natural_disaster" in types
        assert "regulatory_change" in types
        assert "sanctions_escalation" in types
        assert "supply_shortage" in types

    def test_affected_rights_count_positive(self, client: TestClient) -> None:
        templates = client.get("/sector-risk-register/scenarios/templates").json()
        for t in templates:
            assert t["affected_rights_count"] > 0


# ---------------------------------------------------------------------------
# GET /{nace_code} — baseline
# ---------------------------------------------------------------------------

class TestSectorBaseline:
    def test_automotive_returns_200(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/29")
        assert resp.status_code == 200

    def test_returns_21_rights(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/29").json()
        assert len(data["rights"]) == 21

    def test_required_fields_present(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/29").json()
        assert "nace_code" in data
        assert "nace_section" in data
        assert "sector_name" in data
        assert "calibration_version" in data
        assert "is_fully_calibrated" in data
        assert "rights" in data

    def test_automotive_is_calibrated(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/29").json()
        assert data["is_fully_calibrated"] is True
        assert data["nace_section"] == "C"

    def test_all_right_scores_in_range(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/29").json()
        for right in data["rights"]:
            assert 1 <= right["probability"] <= 10, (
                f"Right {right['right_id']} has probability {right['probability']}"
            )

    def test_right_has_name_and_id(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/13").json()
        for right in data["rights"]:
            assert right["right_id"]
            assert right["right_name"]
            assert right["scenario"] is None  # no scenario in baseline

    def test_textiles_forced_labour_high(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/13").json()
        fl = next(r for r in data["rights"] if r["right_id"] == "forced_labour")
        assert fl["probability"] >= 8

    def test_four_digit_nace_accepted(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/29.10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nace_code"] == "29"

    def test_unknown_code_returns_404(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/00")
        assert resp.status_code == 404

    def test_invalid_code_returns_404(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/abc")
        assert resp.status_code == 404

    def test_logistics_sector_name(self, client: TestClient) -> None:
        data = client.get("/sector-risk-register/49").json()
        assert "transport" in data["sector_name"].lower() or "logistics" in data["sector_name"].lower()


# ---------------------------------------------------------------------------
# GET /{nace_code}/simulate
# ---------------------------------------------------------------------------

class TestSimulate:
    def test_returns_200_with_valid_inputs(self, client: TestClient) -> None:
        resp = client.get(
            "/sector-risk-register/29/simulate?scenario=geopolitical_conflict"
        )
        assert resp.status_code == 200

    def test_returns_21_rights(self, client: TestClient) -> None:
        data = client.get(
            "/sector-risk-register/29/simulate?scenario=labour_unrest"
        ).json()
        assert len(data["rights"]) == 21

    def test_each_right_has_scenario_block(self, client: TestClient) -> None:
        data = client.get(
            "/sector-risk-register/29/simulate?scenario=natural_disaster"
        ).json()
        for right in data["rights"]:
            assert right["scenario"] is not None
            sc = right["scenario"]
            assert "type" in sc
            assert "adjusted_probability" in sc
            assert "delta" in sc
            assert "factor" in sc
            assert "explanation" in sc

    def test_scenario_scores_in_range(self, client: TestClient) -> None:
        data = client.get(
            "/sector-risk-register/13/simulate?scenario=supply_shortage"
        ).json()
        for right in data["rights"]:
            adj = right["scenario"]["adjusted_probability"]
            assert 1 <= adj <= 10, (
                f"Right {right['right_id']} has adjusted_probability {adj}"
            )

    def test_summary_block_present(self, client: TestClient) -> None:
        data = client.get(
            "/sector-risk-register/29/simulate?scenario=regulatory_change"
        ).json()
        summary = data["summary"]
        assert "rights_increased" in summary
        assert "rights_above_7_baseline" in summary
        assert "rights_above_7_scenario" in summary
        assert "highest_risk_right" in summary
        assert "highest_risk_score" in summary

    def test_summary_rights_increased_non_negative(self, client: TestClient) -> None:
        data = client.get(
            "/sector-risk-register/29/simulate?scenario=geopolitical_conflict"
        ).json()
        assert data["summary"]["rights_increased"] >= 0

    def test_determinism_via_api(self, client: TestClient) -> None:
        url = "/sector-risk-register/29/simulate?scenario=sanctions_escalation"
        r1 = client.get(url).json()
        r2 = client.get(url).json()
        # scores must match (timestamps will differ)
        scores1 = {r["right_id"]: r["scenario"]["adjusted_probability"] for r in r1["rights"]}
        scores2 = {r["right_id"]: r["scenario"]["adjusted_probability"] for r in r2["rights"]}
        assert scores1 == scores2

    def test_missing_scenario_param_returns_422(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/29/simulate")
        assert resp.status_code == 422

    def test_invalid_scenario_returns_422(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/29/simulate?scenario=nuclear_war")
        assert resp.status_code == 422

    def test_unknown_nace_returns_404(self, client: TestClient) -> None:
        resp = client.get("/sector-risk-register/00/simulate?scenario=labour_unrest")
        assert resp.status_code == 404

    @pytest.mark.parametrize("scenario", [
        "geopolitical_conflict",
        "sanctions_escalation",
        "natural_disaster",
        "regulatory_change",
        "labour_unrest",
        "supply_shortage",
    ])
    def test_all_scenarios_work_for_automotive(
        self, client: TestClient, scenario: str
    ) -> None:
        resp = client.get(f"/sector-risk-register/29/simulate?scenario={scenario}")
        assert resp.status_code == 200, f"Scenario {scenario} failed: {resp.text}"
