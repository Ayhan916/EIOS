"""Unit tests — M47 Regulatory Reporting.

Covers:
  - RegulatoryDeadlineModel (ORM fields, tablename)
  - ControlFrameworkMappingModel (ORM fields, unique constraint)
  - build_ixbrl() — iXBRL bytes, namespace presence, nil handling
  - build_gri_report() / build_gri_csv() — GRI structure, status mapping, completeness
  - build_tcfd_report() — four pillars, disclosures populated
  - calculate_pai() / _sum_optional() — 14 mandatory + 2 opt-in PAIs, data_available
  - stream_audit_csv() — column order, detail truncation
  - make_csv_filename() — filename construction
  - Migration 059 — revision chain, table name, ≥12 seeded deadlines
  - Migration 060 — revision chain, table name, unique constraint name
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock


# ── Model tests ───────────────────────────────────────────────────────────────


class TestRegulatoryDeadlineModel:
    def test_tablename(self) -> None:
        from infrastructure.persistence.models.regulatory_calendar import RegulatoryDeadlineModel
        assert RegulatoryDeadlineModel.__tablename__ == "regulatory_deadlines"

    def test_required_columns(self) -> None:
        from infrastructure.persistence.models.regulatory_calendar import RegulatoryDeadlineModel
        cols = {c.key for c in RegulatoryDeadlineModel.__table__.columns}
        assert {"id", "framework_code", "deadline_name", "deadline_date",
                "description", "jurisdiction", "entity_size", "is_mandatory",
                "reporting_year", "organization_id"}.issubset(cols)

    def test_organization_id_nullable(self) -> None:
        from infrastructure.persistence.models.regulatory_calendar import RegulatoryDeadlineModel
        col = RegulatoryDeadlineModel.__table__.columns["organization_id"]
        assert col.nullable is True

    def test_is_mandatory_not_nullable(self) -> None:
        from infrastructure.persistence.models.regulatory_calendar import RegulatoryDeadlineModel
        col = RegulatoryDeadlineModel.__table__.columns["is_mandatory"]
        assert col.nullable is False

    def test_three_indexes_defined(self) -> None:
        from infrastructure.persistence.models.regulatory_calendar import RegulatoryDeadlineModel
        index_names = {idx.name for idx in RegulatoryDeadlineModel.__table__.indexes}
        assert "ix_reg_deadline_jurisdiction" in index_names
        assert "ix_reg_deadline_framework" in index_names
        assert "ix_reg_deadline_date" in index_names


class TestControlFrameworkMappingModel:
    def test_tablename(self) -> None:
        from infrastructure.persistence.models.framework_mapping import ControlFrameworkMappingModel
        assert ControlFrameworkMappingModel.__tablename__ == "control_framework_mappings"

    def test_required_columns(self) -> None:
        from infrastructure.persistence.models.framework_mapping import ControlFrameworkMappingModel
        cols = {c.key for c in ControlFrameworkMappingModel.__table__.columns}
        assert {"id", "control_id", "framework_code", "framework_control_id",
                "framework_control_name", "mapping_type", "notes",
                "organization_id", "created_by"}.issubset(cols)

    def test_unique_constraint_name(self) -> None:
        from infrastructure.persistence.models.framework_mapping import ControlFrameworkMappingModel
        from sqlalchemy import UniqueConstraint
        constraints = {
            c.name
            for c in ControlFrameworkMappingModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        }
        assert "uq_ctrl_fw_mapping" in constraints

    def test_unique_constraint_columns(self) -> None:
        from infrastructure.persistence.models.framework_mapping import ControlFrameworkMappingModel
        from sqlalchemy import UniqueConstraint
        uq = next(
            c for c in ControlFrameworkMappingModel.__table__.constraints
            if isinstance(c, UniqueConstraint) and c.name == "uq_ctrl_fw_mapping"
        )
        col_names = {col.name for col in uq.columns}
        assert col_names == {"control_id", "framework_code", "framework_control_id"}

    def test_notes_nullable(self) -> None:
        from infrastructure.persistence.models.framework_mapping import ControlFrameworkMappingModel
        col = ControlFrameworkMappingModel.__table__.columns["notes"]
        assert col.nullable is True

    def test_mapping_type_not_nullable(self) -> None:
        from infrastructure.persistence.models.framework_mapping import ControlFrameworkMappingModel
        col = ControlFrameworkMappingModel.__table__.columns["mapping_type"]
        assert col.nullable is False


# ── iXBRL tests ───────────────────────────────────────────────────────────────


class TestBuildIxbrl:
    def _build(self, **kwargs):
        from application.reporting.xbrl_exporter import build_ixbrl
        defaults = dict(
            organization_name="Test Corp",
            organization_id="org-001",
            reporting_period_start=date(2024, 1, 1),
            reporting_period_end=date(2024, 12, 31),
        )
        defaults.update(kwargs)
        return build_ixbrl(**defaults)

    def test_returns_bytes(self) -> None:
        result = self._build()
        assert isinstance(result, bytes)

    def test_utf8_html(self) -> None:
        result = self._build()
        text = result.decode("utf-8")
        assert "<html" in text

    def test_xbrl_namespace_present(self) -> None:
        result = self._build()
        text = result.decode("utf-8")
        assert "http://www.xbrl.org/2013/inlineXBRL" in text

    def test_efrag_esrs_namespace_present(self) -> None:
        result = self._build()
        text = result.decode("utf-8")
        assert "xbrl.efrag.org/taxonomy/esrs/e1/2023" in text

    def test_e1_data_rendered(self) -> None:
        result = self._build(esrs_e1={"scope1_tco2e": 1000.0, "scope2_market_tco2e": 200.0})
        text = result.decode("utf-8")
        assert "1000.0" in text
        assert "GrossScope1GHGEmissions" in text

    def test_nil_for_missing_e1_value(self) -> None:
        result = self._build(esrs_e1={"scope1_tco2e": None})
        text = result.decode("utf-8")
        assert "N/A" in text

    def test_e2_section_rendered(self) -> None:
        result = self._build(esrs_e2={"emissions_to_air_tonnes": 50.0})
        text = result.decode("utf-8")
        assert "ESRS-E2" in text or "EmissionsToAir" in text

    def test_s1_section_rendered(self) -> None:
        result = self._build(esrs_s1={"employee_headcount": 250})
        text = result.decode("utf-8")
        assert "TotalNumberOfEmployees" in text or "250" in text

    def test_no_sections_when_all_none(self) -> None:
        result = self._build(esrs_e1=None, esrs_e2=None, esrs_s1=None)
        text = result.decode("utf-8")
        assert "CSRD/ESRS Sustainability Report" in text

    def test_compute_document_hash_returns_hex(self) -> None:
        from application.reporting.xbrl_exporter import compute_document_hash
        content = b"test content"
        h = compute_document_hash(content)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_compute_document_hash_deterministic(self) -> None:
        from application.reporting.xbrl_exporter import compute_document_hash
        content = b"same content"
        assert compute_document_hash(content) == compute_document_hash(content)


# ── GRI tests ─────────────────────────────────────────────────────────────────


class TestBuildGriReport:
    def _report(self, **kwargs):
        from application.reporting.gri_exporter import build_gri_report
        defaults = dict(
            organization_name="Test Corp",
            reporting_year=2024,
            disclosures=[],
        )
        defaults.update(kwargs)
        return build_gri_report(**defaults)

    def test_metadata_keys(self) -> None:
        r = self._report()
        assert r["metadata"]["framework"] == "GRI Standards 2021"
        assert r["metadata"]["reporting_year"] == 2024
        assert r["metadata"]["organization"] == "Test Corp"

    def test_gri_2_disclosure_always_present(self) -> None:
        r = self._report()
        assert "GRI 2" in r["disclosures_by_standard"]

    def test_gri_305_from_emissions(self) -> None:
        r = self._report(emissions={"scope1": 1000.0, "scope2_market": 200.0, "scope3": None})
        assert "GRI 305" in r["disclosures_by_standard"]
        disc = r["disclosures_by_standard"]["GRI 305"]
        ids = [d["disclosure_id"] for d in disc]
        assert "305-1" in ids
        assert "305-2" in ids

    def test_completeness_pct_calculation(self) -> None:
        r = self._report(emissions={"scope1": 1000.0, "scope2_market": 200.0, "scope3": 50.0})
        assert r["summary"]["completeness_pct"] >= 0
        assert r["summary"]["completeness_pct"] <= 100

    def test_scope3_partial_when_missing(self) -> None:
        r = self._report(emissions={"scope1": 1000.0, "scope3": None})
        disc = r["disclosures_by_standard"]["GRI 305"]
        scope3 = next(d for d in disc if d["disclosure_id"] == "305-3")
        assert scope3["status"] == "partial"

    def test_workforce_gri_401_and_405(self) -> None:
        r = self._report(workforce={"turnover_pct": 12.0, "pay_gap_pct": 8.5})
        assert "GRI 401" in r["disclosures_by_standard"]
        assert "GRI 405" in r["disclosures_by_standard"]

    def test_summary_counts(self) -> None:
        r = self._report(emissions={"scope1": 100.0})
        summary = r["summary"]
        assert summary["total_disclosures"] == summary["reported"] + summary["partial"] + summary["omitted"]


class TestBuildGriCsv:
    def test_csv_has_header(self) -> None:
        from application.reporting.gri_exporter import build_gri_report, build_gri_csv
        report = build_gri_report(
            organization_name="Corp", reporting_year=2024, disclosures=[]
        )
        csv_str = build_gri_csv(report)
        assert csv_str.startswith("standard_code,")

    def test_csv_contains_gri_code(self) -> None:
        from application.reporting.gri_exporter import build_gri_report, build_gri_csv
        report = build_gri_report(
            organization_name="Corp", reporting_year=2024,
            disclosures=[],
            emissions={"scope1": 500.0},
        )
        csv_str = build_gri_csv(report)
        assert "GRI 305" in csv_str


class TestGriStatusMapping:
    def test_completed_maps_to_reported(self) -> None:
        from application.reporting.gri_exporter import _map_status
        assert _map_status("Completed") == "reported"

    def test_in_progress_maps_to_partial(self) -> None:
        from application.reporting.gri_exporter import _map_status
        assert _map_status("In Progress") == "partial"

    def test_not_started_maps_to_omitted(self) -> None:
        from application.reporting.gri_exporter import _map_status
        assert _map_status("Not Started") == "omitted"

    def test_unknown_maps_to_omitted(self) -> None:
        from application.reporting.gri_exporter import _map_status
        assert _map_status("Unknown Status") == "omitted"

    def test_approved_maps_to_reported(self) -> None:
        from application.reporting.gri_exporter import _map_status
        assert _map_status("Approved") == "reported"


# ── TCFD tests ────────────────────────────────────────────────────────────────


class TestBuildTcfdReport:
    def _report(self, **kwargs):
        from application.reporting.tcfd_exporter import build_tcfd_report
        defaults = dict(organization_name="Test Corp", reporting_year=2024)
        defaults.update(kwargs)
        return build_tcfd_report(**defaults)

    def test_four_pillars_present(self) -> None:
        r = self._report()
        pillar_codes = {p["code"] for p in r["pillars"]}
        assert pillar_codes == {"governance", "strategy", "risk_management", "metrics_targets"}

    def test_metadata_keys(self) -> None:
        r = self._report()
        assert r["metadata"]["organization"] == "Test Corp"
        assert r["metadata"]["reporting_year"] == 2024
        assert r["metadata"]["framework"] == "TCFD 2023"

    def test_governance_pillar_has_disclosures(self) -> None:
        r = self._report(
            board_oversight_narrative="Board reviews quarterly.",
            management_role_narrative="CRO leads climate strategy.",
        )
        gov = next(p for p in r["pillars"] if p["code"] == "governance")
        assert len(gov["disclosures"]) >= 2

    def test_strategy_pillar_with_risks(self) -> None:
        r = self._report(
            climate_risks=[{"title": "Flood risk", "type": "physical",
                            "time_horizon": "medium", "description": "..."}]
        )
        strat = next(p for p in r["pillars"] if p["code"] == "strategy")
        assert strat is not None

    def test_metrics_pillar_with_emissions(self) -> None:
        r = self._report(emissions={"scope1": 1000.0, "scope2_market": 200.0, "scope3": 50.0})
        metrics = next(p for p in r["pillars"] if p["code"] == "metrics_targets")
        assert metrics is not None

    def test_completeness_in_summary(self) -> None:
        r = self._report(
            board_oversight_narrative="Present",
            management_role_narrative="Present",
        )
        assert "completeness_pct" in r["summary"]

    def test_summary_has_completeness_pct(self) -> None:
        r = self._report(
            board_oversight_narrative="Present",
            management_role_narrative="Present",
        )
        assert "completeness_pct" in r["summary"]
        assert r["summary"]["completeness_pct"] >= 0


# ── SFDR PAI tests ────────────────────────────────────────────────────────────


class TestCalculatePai:
    def _pai(self, **kwargs):
        from application.reporting.sfdr_pai import calculate_pai
        defaults = dict(
            organization_name="Test Corp",
            reference_period_start="2024-01-01",
            reference_period_end="2024-12-31",
        )
        defaults.update(kwargs)
        return calculate_pai(**defaults)

    def test_returns_dict_with_required_keys(self) -> None:
        r = self._pai()
        assert {"metadata", "mandatory_pais", "optional_pais", "summary"}.issubset(r.keys())

    def test_exactly_14_mandatory_pais(self) -> None:
        r = self._pai()
        assert len(r["mandatory_pais"]) == 14

    def test_exactly_2_optional_pais(self) -> None:
        r = self._pai()
        assert len(r["optional_pais"]) == 2

    def test_all_mandatory_pais_have_data_available_field(self) -> None:
        r = self._pai()
        for pai in r["mandatory_pais"]:
            assert "data_available" in pai

    def test_data_unavailable_when_no_inputs(self) -> None:
        r = self._pai()
        assert r["mandatory_pais"][0]["data_available"] is False

    def test_ghg_pai_available_with_scope_data(self) -> None:
        r = self._pai(scope1_tco2e=1000.0, scope2_tco2e=200.0, scope3_tco2e=50.0)
        ghg_pai = r["mandatory_pais"][0]
        assert ghg_pai["data_available"] is True
        assert ghg_pai["value"] == 1250.0

    def test_carbon_footprint_calculated(self) -> None:
        r = self._pai(
            scope1_tco2e=1000.0, scope2_tco2e=0.0, scope3_tco2e=0.0,
            enterprise_value_eur=10_000_000.0,
        )
        footprint_pai = r["mandatory_pais"][1]
        assert footprint_pai["data_available"] is True
        assert footprint_pai["value"] is not None

    def test_carbon_footprint_absent_without_enterprise_value(self) -> None:
        r = self._pai(scope1_tco2e=1000.0)
        footprint_pai = r["mandatory_pais"][1]
        assert footprint_pai["data_available"] is False

    def test_all_pais_have_explanation(self) -> None:
        r = self._pai()
        for pai in r["mandatory_pais"]:
            assert isinstance(pai["explanation"], str)
            assert len(pai["explanation"]) > 0

    def test_summary_total_is_14(self) -> None:
        r = self._pai()
        assert r["summary"]["mandatory_indicators_total"] == 14

    def test_metadata_organization(self) -> None:
        r = self._pai()
        assert r["metadata"]["organization"] == "Test Corp"

    def test_metadata_framework(self) -> None:
        r = self._pai()
        assert "SFDR" in r["metadata"]["framework"]

    def test_optional_pais_not_mandatory(self) -> None:
        r = self._pai(water_usage_m3=5000.0, waste_tonnes=10.0)
        for pai in r["optional_pais"]:
            assert pai.get("data_available") is True


class TestSumOptional:
    def test_all_none_returns_none(self) -> None:
        from application.reporting.sfdr_pai import _sum_optional
        assert _sum_optional(None, None, None) is None

    def test_some_none_sums_available(self) -> None:
        from application.reporting.sfdr_pai import _sum_optional
        assert _sum_optional(100.0, None, 50.0) == 150.0

    def test_all_values_sums_all(self) -> None:
        from application.reporting.sfdr_pai import _sum_optional
        assert _sum_optional(10.0, 20.0, 30.0) == 60.0

    def test_single_value(self) -> None:
        from application.reporting.sfdr_pai import _sum_optional
        assert _sum_optional(42.0) == 42.0


# ── Audit CSV tests ───────────────────────────────────────────────────────────


class TestStreamAuditCsv:
    def test_header_columns(self) -> None:
        from application.reporting.audit_exporter import stream_audit_csv
        csv_str = stream_audit_csv([])
        header = csv_str.strip().split("\n")[0]
        assert "timestamp" in header
        assert "action" in header
        assert "actor_email" in header
        assert "entity_type" in header
        assert "outcome" in header

    def test_single_event_row(self) -> None:
        from application.reporting.audit_exporter import stream_audit_csv
        events = [{
            "created_at": "2024-01-15T10:00:00",
            "action": "RISK_CREATED",
            "actor_email": "user@example.com",
            "actor_id": "user-001",
            "entity_type": "risk",
            "entity_id": "risk-001",
            "outcome": "success",
            "detail": "Created risk",
        }]
        csv_str = stream_audit_csv(events)
        lines = csv_str.strip().split("\n")
        assert len(lines) == 2
        assert "RISK_CREATED" in lines[1]

    def test_detail_truncated_at_1000_chars(self) -> None:
        from application.reporting.audit_exporter import stream_audit_csv
        long_detail = "x" * 1200
        events = [{"detail": long_detail, "created_at": None}]
        csv_str = stream_audit_csv(events)
        assert "x" * 1001 not in csv_str
        assert "…" in csv_str

    def test_detail_not_truncated_when_short(self) -> None:
        from application.reporting.audit_exporter import stream_audit_csv
        short_detail = "short detail"
        events = [{"detail": short_detail, "created_at": None}]
        csv_str = stream_audit_csv(events)
        assert short_detail in csv_str

    def test_empty_events_returns_header_only(self) -> None:
        from application.reporting.audit_exporter import stream_audit_csv
        csv_str = stream_audit_csv([])
        lines = [l for l in csv_str.strip().split("\n") if l]
        assert len(lines) == 1

    def test_datetime_object_converted_to_iso(self) -> None:
        from datetime import datetime
        from application.reporting.audit_exporter import stream_audit_csv
        dt = datetime(2024, 6, 15, 12, 0, 0)
        events = [{"created_at": dt, "action": "TEST"}]
        csv_str = stream_audit_csv(events)
        assert "2024-06-15T12:00:00" in csv_str

    def test_missing_detail_defaults_to_empty(self) -> None:
        from application.reporting.audit_exporter import stream_audit_csv
        events = [{"created_at": None, "action": "ACT"}]
        csv_str = stream_audit_csv(events)
        assert "ACT" in csv_str


class TestMakeCsvFilename:
    def test_basic_filename(self) -> None:
        from application.reporting.audit_exporter import make_csv_filename
        fn = make_csv_filename("2024-01-01", "2024-12-31", "risk")
        assert fn == "eios_audit_trail_risk_2024-01-01_2024-12-31.csv"

    def test_no_entity_type(self) -> None:
        from application.reporting.audit_exporter import make_csv_filename
        fn = make_csv_filename("2024-01-01", "2024-12-31", None)
        assert fn == "eios_audit_trail_2024-01-01_2024-12-31.csv"

    def test_no_dates(self) -> None:
        from application.reporting.audit_exporter import make_csv_filename
        fn = make_csv_filename(None, None, None)
        assert fn == "eios_audit_trail.csv"

    def test_entity_type_lowercased(self) -> None:
        from application.reporting.audit_exporter import make_csv_filename
        fn = make_csv_filename(None, None, "Risk")
        assert "risk" in fn

    def test_ends_with_csv(self) -> None:
        from application.reporting.audit_exporter import make_csv_filename
        fn = make_csv_filename("2024-01-01", "2024-12-31", "finding")
        assert fn.endswith(".csv")


# ── Migration tests ───────────────────────────────────────────────────────────


def _load_migration(path: str, mod_name: str):
    import importlib.util
    import sys
    from unittest.mock import MagicMock

    if mod_name in sys.modules:
        return sys.modules[mod_name]

    fake_op = MagicMock()
    fake_sa = MagicMock()
    fake_alembic = MagicMock()
    fake_alembic.op = fake_op

    with _patch_dict(sys.modules, {"alembic": fake_alembic, "alembic.op": fake_op, "sqlalchemy": fake_sa}):
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[mod_name] = mod
    return mod


from contextlib import contextmanager


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


class TestMigration059:
    def _load(self):
        return _load_migration(
            "alembic/versions/059_m47_regulatory_calendar.py",
            "_test_migration_059",
        )

    def test_revision(self) -> None:
        mod = self._load()
        assert mod.revision == "059"

    def test_down_revision(self) -> None:
        mod = self._load()
        assert mod.down_revision == "058"

    def test_deadlines_list_at_least_12(self) -> None:
        mod = self._load()
        assert len(mod._DEADLINES) >= 12

    def test_csrd_deadline_present(self) -> None:
        mod = self._load()
        frameworks = [row[0] for row in mod._DEADLINES]
        assert "CSRD" in frameworks

    def test_sfdr_deadline_present(self) -> None:
        mod = self._load()
        frameworks = [row[0] for row in mod._DEADLINES]
        assert "SFDR" in frameworks


class TestMigration060:
    def _load(self):
        return _load_migration(
            "alembic/versions/060_m47_1_framework_mapping.py",
            "_test_migration_060",
        )

    def test_revision(self) -> None:
        mod = self._load()
        assert mod.revision == "060"

    def test_down_revision(self) -> None:
        mod = self._load()
        assert mod.down_revision == "059"

    def test_upgrade_function_exists(self) -> None:
        mod = self._load()
        assert callable(mod.upgrade)

    def test_downgrade_function_exists(self) -> None:
        mod = self._load()
        assert callable(mod.downgrade)
