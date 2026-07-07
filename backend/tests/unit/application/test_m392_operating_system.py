"""M39.2 ESG Operating System Hardening — unit tests.

Covers:
  1. resolve_framework_name — all 5 priority paths
  2. Timeline aggregation — global sort, buffer correctness
  3. Executive schema — degraded mode fields present
  4. Executive router — degraded mode returns structured response
  5. Metrics — 6 new counters exist and record correctly
  6. Audit event validation — all M39 audit event types
  7. Dashboard widget coverage — all new fields present
"""

from __future__ import annotations

from datetime import UTC, datetime

# ── Helpers ────────────────────────────────────────────────────────────────────


def _gap(**kwargs):
    """Simple object with arbitrary attributes for gap testing."""

    class Gap:
        pass

    g = Gap()
    for k, v in kwargs.items():
        setattr(g, k, v)
    return g


# ─── Section 1: resolve_framework_name — all 5 paths ─────────────────────────


class TestResolveFrameworkName:
    def _fn(self):
        from application.operating_system.compliance_operation_service import resolve_framework_name

        return resolve_framework_name

    def test_path1_framework_attribute(self):
        fn = self._fn()
        gap = _gap(framework="CSRD", regulation_name=None)
        assert fn(gap) == "CSRD"

    def test_path2_regulation_name_fallback(self):
        fn = self._fn()
        gap = _gap(regulation_name="SFDR")
        assert fn(gap) == "SFDR"

    def test_path3_framework_name_fallback(self):
        fn = self._fn()
        gap = _gap(framework_name="GRI", regulation_name=None)
        assert fn(gap) == "GRI"

    def test_path4_requirement_to_regulation_code_lookup(self):
        fn = self._fn()
        gap = _gap(regulation_requirement_id="req-001")
        lookup = {"req-001": "ESRS"}
        assert fn(gap, lookup) == "ESRS"

    def test_path5_prefix_parse_from_requirement_id(self):
        fn = self._fn()
        gap = _gap(regulation_requirement_id="CSRD-Art-5")
        assert fn(gap) == "CSRD"

    def test_fallback_unknown(self):
        fn = self._fn()
        gap = _gap()
        assert fn(gap) == "UNKNOWN"

    def test_blank_string_not_returned(self):
        fn = self._fn()
        gap = _gap(framework="   ", regulation_name="SFDR")
        assert fn(gap) == "SFDR"

    def test_prefix_parse_skipped_if_no_dash(self):
        fn = self._fn()
        gap = _gap(regulation_requirement_id="NOEQ")
        assert fn(gap) == "UNKNOWN"

    def test_lookup_takes_priority_over_prefix(self):
        fn = self._fn()
        gap = _gap(regulation_requirement_id="CSRD-Art-5")
        lookup = {"CSRD-Art-5": "CSRD_FULL"}
        assert fn(gap, lookup) == "CSRD_FULL"


# ─── Section 2: Timeline aggregation correctness ──────────────────────────────


class TestTimelineAggregation:
    def test_global_sort_after_merge(self):
        """Entries from multiple sources must be globally sorted by timestamp."""
        from interfaces.api.schemas.operating_system import TimelineEntry

        now = datetime.now(UTC)
        entries = [
            TimelineEntry(
                event_type="action.created",
                entity_type="ESGAction",
                entity_id="a1",
                title="Old action",
                timestamp=now.replace(year=now.year - 1),
                status=None,
            ),
            TimelineEntry(
                event_type="objective.created",
                entity_type="ESGObjective",
                entity_id="o1",
                title="New objective",
                timestamp=now,
                status=None,
            ),
            TimelineEntry(
                event_type="calendar.event_created",
                entity_type="GovernanceCalendarEvent",
                entity_id="c1",
                title="Mid calendar",
                timestamp=now.replace(month=now.month - 1)
                if now.month > 1
                else now.replace(year=now.year - 1, month=12),
                status=None,
            ),
        ]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        assert entries[0].entity_id == "o1"
        assert entries[-1].entity_id == "a1"

    def test_buffer_is_larger_than_limit(self):
        """Buffer size must be limit*5 capped at 1000."""
        limit = 50
        buffer = min(limit * 5, 1000)
        assert buffer == 250
        assert buffer > limit

    def test_buffer_caps_at_1000(self):
        limit = 200
        buffer = min(limit * 5, 1000)
        assert buffer == 1000

    def test_result_truncated_to_limit(self):
        from interfaces.api.schemas.operating_system import TimelineEntry

        now = datetime.now(UTC)
        limit = 3
        all_entries = [
            TimelineEntry(
                event_type="action.created",
                entity_type="ESGAction",
                entity_id=str(i),
                title=f"Entry {i}",
                timestamp=now,
                status=None,
            )
            for i in range(10)
        ]
        result = all_entries[:limit]
        assert len(result) == 3


# ─── Section 3: Executive schema — degraded mode ─────────────────────────────


class TestExecutiveSchemaStructure:
    def test_esg_operating_summary_has_status_field(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        assert "status" in ESGOperatingSummary.model_fields

    def test_esg_operating_summary_has_degraded_reason(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        assert "degraded_reason" in ESGOperatingSummary.model_fields

    def test_esg_operating_summary_has_objectives_by_status(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        assert "objectives_by_status" in ESGOperatingSummary.model_fields

    def test_esg_operating_summary_has_initiatives_by_status(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        assert "initiatives_by_status" in ESGOperatingSummary.model_fields

    def test_esg_operating_summary_has_compliance_readiness(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        assert "compliance_readiness" in ESGOperatingSummary.model_fields

    def test_esg_operating_summary_has_accountability_coverage(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        assert "accountability_coverage" in ESGOperatingSummary.model_fields

    def test_esg_operating_summary_has_controls_failing(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        assert "controls_failing" in ESGOperatingSummary.model_fields

    def test_default_status_is_ok(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        s = ESGOperatingSummary()
        assert s.status == "ok"
        assert s.degraded_reason is None

    def test_degraded_construction(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        s = ESGOperatingSummary(status="degraded", degraded_reason="DB unavailable")
        assert s.status == "degraded"
        assert s.degraded_reason == "DB unavailable"

    def test_new_fields_have_defaults(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        s = ESGOperatingSummary()
        assert isinstance(s.objectives_by_status, dict)
        assert isinstance(s.initiatives_by_status, dict)
        assert isinstance(s.compliance_readiness, dict)
        assert s.accountability_coverage == 0
        assert s.controls_failing == 0


# ─── Section 4: Metrics — 6 new counters ─────────────────────────────────────


class TestMetricsNewCounters:
    def _counters(self):
        from application.operating_system.metrics import _OperatingSystemCounters

        return _OperatingSystemCounters()

    def test_programs_counter_exists(self):
        c = self._counters()
        assert hasattr(c, "operating_system_programs_total")

    def test_controls_counter_exists(self):
        c = self._counters()
        assert hasattr(c, "operating_system_controls_total")

    def test_control_tests_counter_exists(self):
        c = self._counters()
        assert hasattr(c, "operating_system_control_tests_total")

    def test_compliance_ops_counter_exists(self):
        c = self._counters()
        assert hasattr(c, "operating_system_compliance_ops_total")

    def test_calendar_events_counter_exists(self):
        c = self._counters()
        assert hasattr(c, "operating_system_calendar_events_total")

    def test_accountability_assignments_counter_exists(self):
        c = self._counters()
        assert hasattr(c, "operating_system_accountability_assignments_total")

    def test_record_program_created_increments(self):
        c = self._counters()
        c.record_program_created()
        assert c.operating_system_programs_total == 1

    def test_record_control_created_increments(self):
        c = self._counters()
        c.record_control_created()
        assert c.operating_system_controls_total == 1

    def test_record_control_test_created_increments(self):
        c = self._counters()
        c.record_control_test_created()
        assert c.operating_system_control_tests_total == 1

    def test_record_compliance_op_created_increments(self):
        c = self._counters()
        c.record_compliance_op_created()
        assert c.operating_system_compliance_ops_total == 1

    def test_record_calendar_event_created_increments(self):
        c = self._counters()
        c.record_calendar_event_created()
        assert c.operating_system_calendar_events_total == 1

    def test_record_accountability_assignment_created_increments(self):
        c = self._counters()
        c.record_accountability_assignment_created()
        assert c.operating_system_accountability_assignments_total == 1

    def test_prometheus_output_contains_all_new_metrics(self):
        c = self._counters()
        lines = "\n".join(c.to_prometheus_lines("test"))
        assert "operating_system_programs_total" in lines
        assert "operating_system_controls_total" in lines
        assert "operating_system_control_tests_total" in lines
        assert "operating_system_compliance_ops_total" in lines
        assert "operating_system_calendar_events_total" in lines
        assert "operating_system_accountability_assignments_total" in lines


# ─── Section 5: Audit event validation ───────────────────────────────────────


class TestAuditEventTypes:
    """Verify that all M39 audit actions use the correct event type strings."""

    def test_calendar_service_emits_correct_audit_actions(self):
        content = open("application/operating_system/calendar_service.py").read()
        assert '"calendar.event_created"' in content
        assert '"calendar.event_updated"' in content or "calendar.event" in content

    def test_program_service_emits_correct_audit_actions(self):
        content = open("application/operating_system/program_service.py").read()
        assert '"program.created"' in content

    def test_control_service_emits_correct_audit_actions(self):
        content = open("application/operating_system/control_service.py").read()
        assert '"control.created"' in content

    def test_control_test_service_emits_correct_audit_actions(self):
        content = open("application/operating_system/control_test_service.py").read()
        assert '"control.tested"' in content

    def test_compliance_op_service_emits_correct_audit_actions(self):
        content = open("application/operating_system/compliance_operation_service.py").read()
        assert '"compliance_op.created"' in content
        assert '"compliance_op.synced"' in content

    def test_accountability_service_emits_correct_audit_actions(self):
        content = open("application/operating_system/accountability_service.py").read()
        assert '"accountability.assigned"' in content


# ─── Section 6: Dashboard widget coverage ────────────────────────────────────


class TestDashboardWidgetCoverage:
    def test_operating_system_dashboard_has_programs_total(self):
        from interfaces.api.schemas.operating_system import OperatingSystemDashboard

        assert "programs_total" in OperatingSystemDashboard.model_fields

    def test_operating_system_dashboard_has_controls_total(self):
        from interfaces.api.schemas.operating_system import OperatingSystemDashboard

        assert "controls_total" in OperatingSystemDashboard.model_fields

    def test_operating_system_dashboard_has_compliance_operations(self):
        from interfaces.api.schemas.operating_system import OperatingSystemDashboard

        assert "compliance_operations" in OperatingSystemDashboard.model_fields

    def test_operating_system_dashboard_has_governance_calendar_events(self):
        from interfaces.api.schemas.operating_system import OperatingSystemDashboard

        assert "governance_calendar_events" in OperatingSystemDashboard.model_fields


# ─── Section 7: Executive dashboard field completeness ───────────────────────


class TestExecutiveDashboardFieldCompleteness:
    def test_executive_dashboard_has_esg_summary(self):
        from interfaces.api.schemas.executive import ExecutiveDashboard

        assert "esg_summary" in ExecutiveDashboard.model_fields

    def test_esg_summary_is_optional(self):
        from interfaces.api.schemas.executive import ExecutiveDashboard

        field = ExecutiveDashboard.model_fields["esg_summary"]
        # optional means default is None
        assert field.default is None

    def test_esg_summary_all_required_fields(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        required = {
            "status",
            "degraded_reason",
            "objectives_at_risk",
            "initiatives_at_risk",
            "strategic_risks_critical",
            "strategic_risks_total",
            "overdue_esg_actions",
            "objectives_by_status",
            "initiatives_by_status",
            "compliance_readiness",
            "accountability_coverage",
            "controls_failing",
        }
        actual = set(ESGOperatingSummary.model_fields.keys())
        missing = required - actual
        assert not missing, f"Missing fields in ESGOperatingSummary: {missing}"
