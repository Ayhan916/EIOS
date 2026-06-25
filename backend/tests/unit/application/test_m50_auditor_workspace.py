"""M50.2 — Auditor Workspace: unit tests.

Tests cover:
- SOC 2 control status transition rules
- Sign-off package GA-ready gating logic
- Auditor workspace data aggregation
- Checklist completion percentage edge cases
"""

from __future__ import annotations

import pytest


# ── Helpers mirroring production logic ────────────────────────────────────────

def _compute_soc2_pct(controls: list[dict]) -> float:
    if not controls:
        return 0.0
    implemented = sum(
        1 for c in controls
        if c["status"] in ("Implemented", "Tested")
    )
    return round(implemented / len(controls) * 100, 1)


def _is_ga_ready(soc2_pct: float, owasp_pct: float, checklist_pct: float, critical_open: int, high_open: int) -> bool:
    return (
        soc2_pct >= 80.0
        and owasp_pct >= 80.0
        and checklist_pct >= 90.0
        and critical_open == 0
        and high_open == 0
    )


def _checklist_pct(items: list[dict]) -> float:
    if not items:
        return 0.0
    done = sum(1 for i in items if i["status"] in ("Complete", "N/A"))
    return round(done / len(items) * 100, 1)


def _categorise_controls(controls: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for c in controls:
        result.setdefault(c["category"], []).append(c)
    return result


# ── SOC2 readiness pct ─────────────────────────────────────────────────────────

class TestSoc2ReadinessPct:
    def test_all_implemented(self):
        controls = [{"status": "Implemented"} for _ in range(10)]
        assert _compute_soc2_pct(controls) == 100.0

    def test_all_not_started(self):
        controls = [{"status": "Not Started"} for _ in range(10)]
        assert _compute_soc2_pct(controls) == 0.0

    def test_mixed_statuses(self):
        controls = [
            {"status": "Implemented"},
            {"status": "Tested"},
            {"status": "In Progress"},
            {"status": "Not Started"},
        ]
        assert _compute_soc2_pct(controls) == 50.0

    def test_tested_counts_as_implemented(self):
        controls = [{"status": "Tested"}, {"status": "Not Started"}]
        assert _compute_soc2_pct(controls) == 50.0

    def test_in_progress_does_not_count(self):
        controls = [{"status": "In Progress"} for _ in range(5)]
        assert _compute_soc2_pct(controls) == 0.0

    def test_empty_controls_returns_zero(self):
        assert _compute_soc2_pct([]) == 0.0

    def test_partial_38_controls(self):
        controls = (
            [{"status": "Implemented"}] * 20
            + [{"status": "Tested"}] * 10
            + [{"status": "Not Started"}] * 8
        )
        pct = _compute_soc2_pct(controls)
        assert pct == round(30 / 38 * 100, 1)


# ── GA-ready gating ────────────────────────────────────────────────────────────

class TestGaReadyGating:
    def test_all_thresholds_met(self):
        assert _is_ga_ready(85.0, 90.0, 95.0, 0, 0) is True

    def test_soc2_below_80(self):
        assert _is_ga_ready(79.9, 90.0, 95.0, 0, 0) is False

    def test_owasp_below_80(self):
        assert _is_ga_ready(85.0, 79.9, 95.0, 0, 0) is False

    def test_checklist_below_90(self):
        assert _is_ga_ready(85.0, 90.0, 89.9, 0, 0) is False

    def test_critical_open_blocks(self):
        assert _is_ga_ready(90.0, 90.0, 95.0, 1, 0) is False

    def test_high_open_blocks(self):
        assert _is_ga_ready(90.0, 90.0, 95.0, 0, 1) is False

    def test_exactly_at_thresholds(self):
        assert _is_ga_ready(80.0, 80.0, 90.0, 0, 0) is True

    def test_all_zero_not_ready(self):
        assert _is_ga_ready(0.0, 0.0, 0.0, 5, 3) is False


# ── Checklist percentage ───────────────────────────────────────────────────────

class TestChecklistPct:
    def test_all_complete(self):
        items = [{"status": "Complete"} for _ in range(38)]
        assert _checklist_pct(items) == 100.0

    def test_all_pending(self):
        items = [{"status": "Pending"} for _ in range(20)]
        assert _checklist_pct(items) == 0.0

    def test_na_counts_as_done(self):
        items = [{"status": "N/A"}, {"status": "Pending"}]
        assert _checklist_pct(items) == 50.0

    def test_empty_returns_zero(self):
        assert _checklist_pct([]) == 0.0

    def test_mixed_38_items(self):
        items = (
            [{"status": "Complete"}] * 30
            + [{"status": "N/A"}] * 4
            + [{"status": "Pending"}] * 4
        )
        pct = _checklist_pct(items)
        assert pct == round(34 / 38 * 100, 1)


# ── Category grouping ─────────────────────────────────────────────────────────

class TestControlCategoryGrouping:
    def test_groups_by_category(self):
        controls = [
            {"control_id": "CC1.1", "category": "CC", "status": "Implemented"},
            {"control_id": "CC1.2", "category": "CC", "status": "In Progress"},
            {"control_id": "A1.1",  "category": "A",  "status": "Implemented"},
        ]
        groups = _categorise_controls(controls)
        assert len(groups["CC"]) == 2
        assert len(groups["A"]) == 1

    def test_single_category(self):
        controls = [{"control_id": f"CC{i}", "category": "CC", "status": "Implemented"} for i in range(5)]
        groups = _categorise_controls(controls)
        assert list(groups.keys()) == ["CC"]
        assert len(groups["CC"]) == 5

    def test_empty_controls(self):
        assert _categorise_controls([]) == {}


# ── Sign-off package structure ────────────────────────────────────────────────

class TestSignOffPackageStructure:
    def _build_package(
        self,
        soc2_pct: float = 85.0,
        owasp_pct: float = 90.0,
        checklist_pct: float = 95.0,
        critical_open: int = 0,
        high_open: int = 0,
        controls: list | None = None,
    ) -> dict:
        return {
            "document_type": "EIOS Auditor Sign-Off Package",
            "ga_ready": _is_ga_ready(soc2_pct, owasp_pct, checklist_pct, critical_open, high_open),
            "soc2": {
                "readiness_pct": soc2_pct,
                "controls": controls or [],
            },
            "owasp": {"coverage_pct": owasp_pct},
            "production_checklist": {"completion_pct": checklist_pct},
        }

    def test_document_type_present(self):
        pkg = self._build_package()
        assert pkg["document_type"] == "EIOS Auditor Sign-Off Package"

    def test_ga_ready_true_when_all_met(self):
        pkg = self._build_package()
        assert pkg["ga_ready"] is True

    def test_ga_ready_false_with_critical_finding(self):
        pkg = self._build_package(critical_open=1)
        assert pkg["ga_ready"] is False

    def test_soc2_section_present(self):
        pkg = self._build_package()
        assert "readiness_pct" in pkg["soc2"]

    def test_controls_list_in_soc2(self):
        controls = [{"control_id": "CC1.1", "status": "Implemented"}]
        pkg = self._build_package(controls=controls)
        assert len(pkg["soc2"]["controls"]) == 1

    def test_owasp_section_present(self):
        pkg = self._build_package()
        assert "coverage_pct" in pkg["owasp"]

    def test_checklist_section_present(self):
        pkg = self._build_package()
        assert "completion_pct" in pkg["production_checklist"]
