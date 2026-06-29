"""Unit tests — M49 Security Validation + SOC 2 + Final Audit.

Covers:
  - SOC2 service: control catalogue, compute_readiness_score, get_eios_evidence
  - OWASP pentest readiness: OWASP_TOP_10 structure, assess_owasp_status
  - Production checklist service: PRODUCTION_CHECKLIST structure, compute_checklist_summary
  - Soc2ControlModel: columns, unique constraint
  - PentestFindingModel: columns
  - ProductionChecklistItemModel: columns
  - Rate limiter: _get_limit, window routing
  - Migration 063: revision chain
"""

from __future__ import annotations

from typing import Any


# ── SOC 2 Service ─────────────────────────────────────────────────────────────

class TestSoc2Catalogue:
    def test_catalogue_not_empty(self) -> None:
        from application.security.soc2_service import SOC2_CONTROLS
        assert len(SOC2_CONTROLS) >= 30

    def test_all_have_required_keys(self) -> None:
        from application.security.soc2_service import SOC2_CONTROLS
        for ctrl in SOC2_CONTROLS:
            assert {"control_id", "category", "control_name", "description"}.issubset(ctrl.keys())

    def test_control_ids_unique(self) -> None:
        from application.security.soc2_service import SOC2_CONTROLS
        ids = [c["control_id"] for c in SOC2_CONTROLS]
        assert len(ids) == len(set(ids))

    def test_categories_valid(self) -> None:
        from application.security.soc2_service import SOC2_CONTROLS
        valid = {"CC1", "CC2", "CC3", "CC4", "CC5", "CC6", "CC7", "CC8", "CC9", "A1", "C1"}
        for ctrl in SOC2_CONTROLS:
            assert ctrl["category"] in valid

    def test_cc6_has_most_controls(self) -> None:
        from application.security.soc2_service import SOC2_CONTROLS
        cc6 = [c for c in SOC2_CONTROLS if c["category"] == "CC6"]
        assert len(cc6) >= 5

    def test_eios_evidence_for_cc6_1(self) -> None:
        from application.security.soc2_service import get_eios_evidence
        ev = get_eios_evidence("CC6.1")
        assert ev is not None
        assert len(ev) > 20

    def test_eios_evidence_unknown_returns_none(self) -> None:
        from application.security.soc2_service import get_eios_evidence
        assert get_eios_evidence("XX9.9") is None


class TestComputeReadinessScore:
    def _controls(self, statuses: list[str]) -> list[dict[str, Any]]:
        return [
            {"organization_id": "org-1", "control_id": f"CC{i}.1",
             "category": "CC1", "control_name": f"Ctrl {i}", "status": s}
            for i, s in enumerate(statuses, 1)
        ]

    def test_all_implemented(self) -> None:
        from application.security.soc2_service import compute_readiness_score
        result = compute_readiness_score(self._controls(["Implemented"] * 5))
        assert result.overall_pct == 100.0
        assert result.implemented == 5
        assert result.not_started == 0

    def test_none_implemented(self) -> None:
        from application.security.soc2_service import compute_readiness_score
        result = compute_readiness_score(self._controls(["Not Started"] * 4))
        assert result.overall_pct == 0.0
        assert result.implemented == 0

    def test_mixed(self) -> None:
        from application.security.soc2_service import compute_readiness_score
        result = compute_readiness_score(
            self._controls(["Implemented", "In Progress", "Not Started", "Implemented"])
        )
        assert result.implemented == 2
        assert result.in_progress == 1
        assert result.overall_pct == 50.0

    def test_empty_controls(self) -> None:
        from application.security.soc2_service import compute_readiness_score
        result = compute_readiness_score([])
        assert result.total_controls == 0
        assert result.overall_pct == 0.0

    def test_gaps_list(self) -> None:
        from application.security.soc2_service import compute_readiness_score
        result = compute_readiness_score(
            self._controls(["Implemented", "Not Started", "In Progress"])
        )
        assert len(result.gaps) == 2

    def test_to_dict_keys(self) -> None:
        from application.security.soc2_service import compute_readiness_score
        d = compute_readiness_score(self._controls(["Implemented"])).to_dict()
        assert {"total_controls", "implemented", "overall_readiness_pct", "audit_ready", "gaps"}.issubset(d.keys())

    def test_audit_ready_at_80_pct(self) -> None:
        from application.security.soc2_service import compute_readiness_score
        statuses = ["Implemented"] * 8 + ["Not Started"] * 2
        result = compute_readiness_score(self._controls(statuses))
        assert result.to_dict()["audit_ready"] is True

    def test_by_category_aggregation(self) -> None:
        from application.security.soc2_service import compute_readiness_score
        controls = [
            {"organization_id": "o", "control_id": "CC1.1", "category": "CC1",
             "control_name": "C1", "status": "Implemented"},
            {"organization_id": "o", "control_id": "CC1.2", "category": "CC1",
             "control_name": "C2", "status": "Not Started"},
        ]
        result = compute_readiness_score(controls)
        assert result.by_category["CC1"]["total"] == 2
        assert result.by_category["CC1"]["implemented"] == 1


# ── OWASP Pentest Readiness ───────────────────────────────────────────────────

class TestOwaspCatalogue:
    def test_ten_categories(self) -> None:
        from application.security.pentest_readiness import OWASP_TOP_10
        assert len(OWASP_TOP_10) == 10

    def test_all_have_required_keys(self) -> None:
        from application.security.pentest_readiness import OWASP_TOP_10
        for item in OWASP_TOP_10:
            assert {"id", "name", "eios_controls", "test_cases", "status"}.issubset(item.keys())

    def test_ids_are_a01_to_a10(self) -> None:
        from application.security.pentest_readiness import OWASP_TOP_10
        ids = {c["id"] for c in OWASP_TOP_10}
        assert ids == {f"A{i:02d}" for i in range(1, 11)}

    def test_each_has_controls(self) -> None:
        from application.security.pentest_readiness import OWASP_TOP_10
        for item in OWASP_TOP_10:
            assert len(item["eios_controls"]) >= 1

    def test_each_has_test_cases(self) -> None:
        from application.security.pentest_readiness import OWASP_TOP_10
        for item in OWASP_TOP_10:
            assert len(item["test_cases"]) >= 1


class TestAssessOwaspStatus:
    def test_returns_assessment(self) -> None:
        from application.security.pentest_readiness import assess_owasp_status
        result = assess_owasp_status()
        assert result.total == 10

    def test_overall_pct_range(self) -> None:
        from application.security.pentest_readiness import assess_owasp_status
        result = assess_owasp_status()
        assert 0 <= result.overall_pct <= 100

    def test_to_dict_keys(self) -> None:
        from application.security.pentest_readiness import assess_owasp_status
        d = assess_owasp_status().to_dict()
        assert {"framework", "total_categories", "implemented", "overall_pct", "pentest_ready", "items"}.issubset(d.keys())

    def test_items_have_correct_shape(self) -> None:
        from application.security.pentest_readiness import assess_owasp_status
        items = assess_owasp_status().to_dict()["items"]
        assert len(items) == 10
        for item in items:
            assert "id" in item and "status" in item


# ── Production Checklist Service ──────────────────────────────────────────────

class TestProductionChecklist:
    def test_checklist_not_empty(self) -> None:
        from application.security.production_checklist_service import PRODUCTION_CHECKLIST
        assert len(PRODUCTION_CHECKLIST) >= 30

    def test_all_have_required_keys(self) -> None:
        from application.security.production_checklist_service import PRODUCTION_CHECKLIST
        for item in PRODUCTION_CHECKLIST:
            assert {"category", "priority", "item_name", "description"}.issubset(item.keys())

    def test_categories_cover_all_areas(self) -> None:
        from application.security.production_checklist_service import PRODUCTION_CHECKLIST
        cats = {i["category"] for i in PRODUCTION_CHECKLIST}
        assert {"Infrastructure", "Security", "Data", "Operations", "Compliance", "Testing"}.issubset(cats)

    def test_high_priority_items_exist(self) -> None:
        from application.security.production_checklist_service import PRODUCTION_CHECKLIST
        high = [i for i in PRODUCTION_CHECKLIST if i["priority"] == "HIGH"]
        assert len(high) >= 10

    def test_security_items_include_pentest(self) -> None:
        from application.security.production_checklist_service import PRODUCTION_CHECKLIST
        security_items = [i for i in PRODUCTION_CHECKLIST if i["category"] == "Security"]
        names = [i["item_name"] for i in security_items]
        assert any("pentest" in n.lower() or "Penetration" in n for n in names)


class TestComputeChecklistSummary:
    def _items(self, statuses: list[str]) -> list[dict[str, Any]]:
        return [{"category": "Security", "status": s, "priority": "HIGH"} for s in statuses]

    def test_all_complete(self) -> None:
        from application.security.production_checklist_service import compute_checklist_summary
        result = compute_checklist_summary(self._items(["Complete"] * 5))
        assert result.completion_pct == 100.0
        assert result.complete == 5

    def test_mixed(self) -> None:
        from application.security.production_checklist_service import compute_checklist_summary
        result = compute_checklist_summary(self._items(["Complete", "Pending", "N/A"]))
        assert result.complete == 1
        assert result.na == 1
        assert result.pending == 1

    def test_na_excluded_from_pct(self) -> None:
        from application.security.production_checklist_service import compute_checklist_summary
        result = compute_checklist_summary(self._items(["Complete", "N/A", "N/A"]))
        assert result.completion_pct == 100.0

    def test_ga_ready_at_90_pct(self) -> None:
        from application.security.production_checklist_service import compute_checklist_summary
        statuses = ["Complete"] * 9 + ["Pending"]
        result = compute_checklist_summary(self._items(statuses))
        assert result.to_dict()["ga_ready"] is True

    def test_to_dict_keys(self) -> None:
        from application.security.production_checklist_service import compute_checklist_summary
        d = compute_checklist_summary(self._items(["Complete"])).to_dict()
        assert {"total", "complete", "pending", "completion_pct", "ga_ready", "by_category"}.issubset(d.keys())


# ── Models ────────────────────────────────────────────────────────────────────

class TestSoc2ControlModel:
    def test_tablename(self) -> None:
        from infrastructure.persistence.models.soc2_control import Soc2ControlModel
        assert Soc2ControlModel.__tablename__ == "soc2_controls"

    def test_required_columns(self) -> None:
        from infrastructure.persistence.models.soc2_control import Soc2ControlModel
        cols = {c.key for c in Soc2ControlModel.__table__.columns}
        assert {"id", "organization_id", "control_id", "category", "control_name", "status"}.issubset(cols)

    def test_unique_constraint(self) -> None:
        from infrastructure.persistence.models.soc2_control import Soc2ControlModel
        from sqlalchemy import UniqueConstraint
        uc_names = {
            c.name for c in Soc2ControlModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        }
        assert "uq_soc2_org_control" in uc_names

    def test_status_column_has_default(self) -> None:
        from infrastructure.persistence.models.soc2_control import Soc2ControlModel
        col = Soc2ControlModel.__table__.columns["status"]
        assert col.default is not None or col.server_default is not None or not col.nullable


class TestPentestFindingModel:
    def test_tablename(self) -> None:
        from infrastructure.persistence.models.pentest_finding import PentestFindingModel
        assert PentestFindingModel.__tablename__ == "pentest_findings"

    def test_required_columns(self) -> None:
        from infrastructure.persistence.models.pentest_finding import PentestFindingModel
        cols = {c.key for c in PentestFindingModel.__table__.columns}
        assert {"id", "organization_id", "owasp_category", "title", "severity", "status", "cvss_score"}.issubset(cols)

    def test_cvss_is_float(self) -> None:
        from infrastructure.persistence.models.pentest_finding import PentestFindingModel
        import sqlalchemy as sa
        col = PentestFindingModel.__table__.columns["cvss_score"]
        assert isinstance(col.type, sa.Float)

    def test_discovered_at_nullable(self) -> None:
        from infrastructure.persistence.models.pentest_finding import PentestFindingModel
        col = PentestFindingModel.__table__.columns["discovered_at"]
        assert col.nullable is True


class TestProductionChecklistItemModel:
    def test_tablename(self) -> None:
        from infrastructure.persistence.models.production_checklist import ProductionChecklistItemModel
        assert ProductionChecklistItemModel.__tablename__ == "production_checklist_items"

    def test_required_columns(self) -> None:
        from infrastructure.persistence.models.production_checklist import ProductionChecklistItemModel
        cols = {c.key for c in ProductionChecklistItemModel.__table__.columns}
        assert {"id", "organization_id", "category", "item_name", "status", "priority"}.issubset(cols)

    def test_completed_at_nullable(self) -> None:
        from infrastructure.persistence.models.production_checklist import ProductionChecklistItemModel
        col = ProductionChecklistItemModel.__table__.columns["completed_at"]
        assert col.nullable is True


# ── Rate Limiter ──────────────────────────────────────────────────────────────

class TestRateLimiter:
    def test_login_path_gets_strictest_limit(self) -> None:
        from app.middleware.rate_limiter import _get_limit
        limit = _get_limit("/api/v1/auth/login")
        assert limit is not None
        max_req, window = limit
        assert max_req <= 10
        assert window == 60

    def test_generic_api_path_gets_limit(self) -> None:
        from app.middleware.rate_limiter import _get_limit
        limit = _get_limit("/api/v1/suppliers")
        assert limit is not None
        max_req, _ = limit
        assert max_req >= 100

    def test_health_path_not_limited(self) -> None:
        from app.middleware.rate_limiter import _get_limit
        assert _get_limit("/health") is None

    def test_metrics_path_not_limited(self) -> None:
        from app.middleware.rate_limiter import _get_limit
        assert _get_limit("/metrics") is None

    def test_unknown_path_gets_general_limit(self) -> None:
        from app.middleware.rate_limiter import _get_limit
        limit = _get_limit("/api/v1/organizations/me/settings")
        assert limit is not None


# ── Migration 063 ─────────────────────────────────────────────────────────────


def _load_m49_migration(path: str, mod_name: str):
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

    with _patch_dict(sys.modules, {"alembic": fake_alembic, "alembic.op": fake_op, "sqlalchemy": fake_sa}):
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[mod_name] = mod

    return mod


class TestMigration063:
    def _load(self):
        return _load_m49_migration(
            "alembic/versions/063_m49_security_audit.py",
            "_test_migration_063",
        )

    def test_revision(self) -> None:
        assert self._load().revision == "063"

    def test_down_revision(self) -> None:
        assert self._load().down_revision == "062"

    def test_upgrade_callable(self) -> None:
        assert callable(self._load().upgrade)

    def test_downgrade_callable(self) -> None:
        assert callable(self._load().downgrade)
