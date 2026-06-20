"""M39 ESG Operating System — Prometheus counters.

In-process singleton exposed at GET /metrics/prometheus.
"""

from __future__ import annotations


class _OperatingSystemCounters:
    def __init__(self) -> None:
        self.esg_objectives_total: int = 0
        self.esg_initiatives_total: int = 0
        self.esg_actions_total: int = 0
        self.esg_actions_overdue_total: int = 0
        self.esg_playbooks_total: int = 0
        self.esg_workflows_total: int = 0
        self.esg_escalations_total: int = 0
        # M39.2 — new entity counters
        self.operating_system_programs_total: int = 0
        self.operating_system_controls_total: int = 0
        self.operating_system_control_tests_total: int = 0
        self.operating_system_compliance_ops_total: int = 0
        self.operating_system_calendar_events_total: int = 0
        self.operating_system_accountability_assignments_total: int = 0

    def record_objective_created(self) -> None:
        self.esg_objectives_total += 1

    def record_initiative_created(self) -> None:
        self.esg_initiatives_total += 1

    def record_action_created(self) -> None:
        self.esg_actions_total += 1

    def record_action_overdue(self) -> None:
        self.esg_actions_overdue_total += 1

    def record_playbook_created(self) -> None:
        self.esg_playbooks_total += 1

    def record_workflow_started(self) -> None:
        self.esg_workflows_total += 1

    def record_escalation(self) -> None:
        self.esg_escalations_total += 1

    def record_program_created(self) -> None:
        self.operating_system_programs_total += 1

    def record_control_created(self) -> None:
        self.operating_system_controls_total += 1

    def record_control_test_created(self) -> None:
        self.operating_system_control_tests_total += 1

    def record_compliance_op_created(self) -> None:
        self.operating_system_compliance_ops_total += 1

    def record_calendar_event_created(self) -> None:
        self.operating_system_calendar_events_total += 1

    def record_accountability_assignment_created(self) -> None:
        self.operating_system_accountability_assignments_total += 1

    def to_prometheus_lines(self, env: str) -> list[str]:
        return [
            "",
            "# HELP esg_objectives_total Total ESG objectives created",
            "# TYPE esg_objectives_total counter",
            f'esg_objectives_total{{environment="{env}"}} {self.esg_objectives_total}',
            "",
            "# HELP esg_initiatives_total Total ESG initiatives created",
            "# TYPE esg_initiatives_total counter",
            f'esg_initiatives_total{{environment="{env}"}} {self.esg_initiatives_total}',
            "",
            "# HELP esg_actions_total Total ESG actions created",
            "# TYPE esg_actions_total counter",
            f'esg_actions_total{{environment="{env}"}} {self.esg_actions_total}',
            "",
            "# HELP esg_actions_overdue_total Total overdue ESG actions detected",
            "# TYPE esg_actions_overdue_total counter",
            f'esg_actions_overdue_total{{environment="{env}"}} {self.esg_actions_overdue_total}',
            "",
            "# HELP esg_playbooks_total Total ESG playbooks created",
            "# TYPE esg_playbooks_total counter",
            f'esg_playbooks_total{{environment="{env}"}} {self.esg_playbooks_total}',
            "",
            "# HELP esg_workflows_total Total workflow executions started",
            "# TYPE esg_workflows_total counter",
            f'esg_workflows_total{{environment="{env}"}} {self.esg_workflows_total}',
            "",
            "# HELP esg_escalations_total Total governance escalations triggered",
            "# TYPE esg_escalations_total counter",
            f'esg_escalations_total{{environment="{env}"}} {self.esg_escalations_total}',
            "",
            "# HELP operating_system_programs_total Total ESG programs created",
            "# TYPE operating_system_programs_total counter",
            f'operating_system_programs_total{{environment="{env}"}} {self.operating_system_programs_total}',
            "",
            "# HELP operating_system_controls_total Total ESG controls created",
            "# TYPE operating_system_controls_total counter",
            f'operating_system_controls_total{{environment="{env}"}} {self.operating_system_controls_total}',
            "",
            "# HELP operating_system_control_tests_total Total control tests run",
            "# TYPE operating_system_control_tests_total counter",
            f'operating_system_control_tests_total{{environment="{env}"}} {self.operating_system_control_tests_total}',
            "",
            "# HELP operating_system_compliance_ops_total Total compliance operations created",
            "# TYPE operating_system_compliance_ops_total counter",
            f'operating_system_compliance_ops_total{{environment="{env}"}} {self.operating_system_compliance_ops_total}',
            "",
            "# HELP operating_system_calendar_events_total Total governance calendar events created",
            "# TYPE operating_system_calendar_events_total counter",
            f'operating_system_calendar_events_total{{environment="{env}"}} {self.operating_system_calendar_events_total}',
            "",
            "# HELP operating_system_accountability_assignments_total Total accountability assignments created",
            "# TYPE operating_system_accountability_assignments_total counter",
            f'operating_system_accountability_assignments_total{{environment="{env}"}} {self.operating_system_accountability_assignments_total}',
            "",
        ]


os_counters = _OperatingSystemCounters()
