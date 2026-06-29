"""M50.1 — Workflow Action Buttons: unit tests.

Tests cover:
- Notification entity href mapping logic
- KPI measurement recording validation
- SBTi validation request field constraints
- OFAC per-supplier scan result shape
"""

from __future__ import annotations

from datetime import datetime, UTC


# ── Notification entity href mapping ─────────────────────────────────────────

def entity_href(entity_type: str | None, entity_id: str | None) -> str | None:
    if not entity_type or not entity_id:
        return None
    t = entity_type.lower()
    if t in ("supplier", "supplier_user"):
        return f"/suppliers/{entity_id}"
    if t == "assessment":
        return f"/assessments/{entity_id}"
    if t == "finding":
        return "/findings"
    if t == "recommendation":
        return "/recommendations"
    if t == "risk":
        return "/executive"
    if t == "kpi":
        return "/sustainability/kpis"
    return None


class TestNotificationEntityHref:
    def test_supplier_links_to_supplier_page(self):
        assert entity_href("supplier", "abc-123") == "/suppliers/abc-123"

    def test_supplier_user_links_to_supplier_page(self):
        assert entity_href("supplier_user", "def-456") == "/suppliers/def-456"

    def test_assessment_links_to_assessment_detail(self):
        assert entity_href("assessment", "ghi-789") == "/assessments/ghi-789"

    def test_finding_links_to_findings_list(self):
        assert entity_href("finding", "anything") == "/findings"

    def test_recommendation_links_to_recommendations_list(self):
        assert entity_href("recommendation", "anything") == "/recommendations"

    def test_risk_links_to_executive(self):
        assert entity_href("risk", "anything") == "/executive"

    def test_kpi_links_to_kpi_page(self):
        assert entity_href("kpi", "anything") == "/sustainability/kpis"

    def test_none_type_returns_none(self):
        assert entity_href(None, "some-id") is None

    def test_none_id_returns_none(self):
        assert entity_href("supplier", None) is None

    def test_both_none_returns_none(self):
        assert entity_href(None, None) is None

    def test_unknown_type_returns_none(self):
        assert entity_href("invoice", "xyz") is None

    def test_case_insensitive(self):
        assert entity_href("SUPPLIER", "abc") == "/suppliers/abc"
        assert entity_href("Assessment", "def") == "/assessments/def"


# ── KPI Measurement validation logic ─────────────────────────────────────────

def _validate_measurement(
    measured_value: float,
    period_start: str,
    period_end: str,
) -> list[str]:
    errors = []
    if measured_value < 0:
        errors.append("measured_value must be >= 0")
    try:
        start = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
        end = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
        if end <= start:
            errors.append("period_end must be after period_start")
    except ValueError:
        errors.append("invalid date format")
    return errors


class TestKpiMeasurementValidation:
    def test_valid_measurement_passes(self):
        errs = _validate_measurement(42.5, "2026-06-01T00:00:00Z", "2026-06-30T00:00:00Z")
        assert errs == []

    def test_negative_value_fails(self):
        errs = _validate_measurement(-1.0, "2026-06-01T00:00:00Z", "2026-06-30T00:00:00Z")
        assert "measured_value must be >= 0" in errs

    def test_end_before_start_fails(self):
        errs = _validate_measurement(10.0, "2026-06-30T00:00:00Z", "2026-06-01T00:00:00Z")
        assert any("period_end" in e for e in errs)

    def test_zero_value_passes(self):
        errs = _validate_measurement(0.0, "2026-06-01T00:00:00Z", "2026-06-30T00:00:00Z")
        assert errs == []

    def test_large_value_passes(self):
        errs = _validate_measurement(999_999.99, "2026-01-01T00:00:00Z", "2026-12-31T00:00:00Z")
        assert errs == []


# ── SBTi validation request fields ───────────────────────────────────────────

def _validate_sbti_request(
    base_year: int,
    target_year: int,
    base_year_scope1: float,
    base_year_scope2: float,
    target_scope1: float,
    target_scope2: float,
) -> list[str]:
    errors = []
    if not (2010 <= base_year <= 2023):
        errors.append("base_year must be 2010–2023")
    if not (2025 <= target_year <= 2050):
        errors.append("target_year must be 2025–2050")
    if base_year_scope1 < 0 or base_year_scope2 < 0:
        errors.append("baseline emissions must be >= 0")
    if target_scope1 < 0 or target_scope2 < 0:
        errors.append("target emissions must be >= 0")
    return errors


class TestSBTiValidationRequest:
    def test_valid_request(self):
        assert _validate_sbti_request(2019, 2030, 5000, 2000, 2500, 1000) == []

    def test_base_year_too_early(self):
        errs = _validate_sbti_request(2005, 2030, 1000, 500, 500, 250)
        assert any("base_year" in e for e in errs)

    def test_target_year_too_late(self):
        errs = _validate_sbti_request(2019, 2055, 1000, 500, 500, 250)
        assert any("target_year" in e for e in errs)

    def test_negative_baseline_fails(self):
        errs = _validate_sbti_request(2019, 2030, -100, 500, 500, 250)
        assert any("baseline" in e for e in errs)

    def test_negative_target_fails(self):
        errs = _validate_sbti_request(2019, 2030, 1000, 500, -50, 250)
        assert any("target" in e for e in errs)

    def test_zero_emissions_valid(self):
        assert _validate_sbti_request(2020, 2040, 0, 0, 0, 0) == []


# ── OFAC per-supplier result shape ───────────────────────────────────────────

def _ofac_result(supplier_name: str, hits: list[dict]) -> dict:
    matches = [
        {
            "sdn_uid": h["uid"],
            "sdn_name": h["name"],
            "sdn_type": h["type"],
            "programs": h.get("programs", [])[:3],
        }
        for h in hits
    ]
    return {
        "scan_timestamp": datetime.now(UTC).isoformat(),
        "supplier_name": supplier_name,
        "sdn_entries_checked": 100,
        "matches_found": len(matches),
        "matches": matches[:20],
        "fuzzy": False,
    }


class TestOfacPerSupplierResult:
    def test_no_matches_result_shape(self):
        r = _ofac_result("Acme Corp", [])
        assert r["matches_found"] == 0
        assert r["matches"] == []
        assert "scan_timestamp" in r
        assert r["supplier_name"] == "Acme Corp"

    def test_with_match_result_shape(self):
        hit = {"uid": "12345", "name": "ACME CORPORATION", "type": "Entity", "programs": ["IRAN"]}
        r = _ofac_result("Acme Corp", [hit])
        assert r["matches_found"] == 1
        assert r["matches"][0]["sdn_name"] == "ACME CORPORATION"
        assert r["matches"][0]["programs"] == ["IRAN"]

    def test_programs_capped_at_3(self):
        hit = {"uid": "1", "name": "X", "type": "Entity", "programs": ["A", "B", "C", "D", "E"]}
        r = _ofac_result("X", [hit])
        assert len(r["matches"][0]["programs"]) == 3

    def test_matches_capped_at_20(self):
        hits = [{"uid": str(i), "name": f"Entity {i}", "type": "Entity", "programs": []} for i in range(25)]
        r = _ofac_result("Big Corp", hits)
        assert len(r["matches"]) == 20

    def test_fuzzy_flag_included(self):
        r = _ofac_result("Corp", [])
        assert "fuzzy" in r
