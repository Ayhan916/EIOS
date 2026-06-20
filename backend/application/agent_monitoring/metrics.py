"""M36.2 Agent Monitoring In-Process Metrics.

Follows the same counter pattern as application/external_intelligence/metrics.py.
Counters are process-level singletons; they reset on restart.
Exposed at /metrics/prometheus via the metrics router.
"""

from __future__ import annotations


class _AgentCounters:
    """Process-level agent monitoring metrics."""

    def __init__(self) -> None:
        self.agent_runs_total: int = 0
        self.agent_runs_failed_total: int = 0
        self.agent_findings_created_total: int = 0
        self.agent_alerts_created_total: int = 0
        self.agent_drafts_created_total: int = 0
        self._runtime_sum_ms: float = 0.0
        self._runtime_count: int = 0
        self.agent_runs_deduplicated_total: int = 0  # duplicate concurrent runs blocked

    def record_run_completed(self, runtime_ms: int | None = None) -> None:
        self.agent_runs_total += 1
        if runtime_ms is not None:
            self._runtime_sum_ms += runtime_ms
            self._runtime_count += 1

    def record_run_failed(self, runtime_ms: int | None = None) -> None:
        self.agent_runs_total += 1
        self.agent_runs_failed_total += 1
        if runtime_ms is not None:
            self._runtime_sum_ms += runtime_ms
            self._runtime_count += 1

    def record_finding_created(self) -> None:
        self.agent_findings_created_total += 1

    def record_alert_created(self) -> None:
        self.agent_alerts_created_total += 1

    def record_draft_created(self) -> None:
        self.agent_drafts_created_total += 1

    def record_run_deduplicated(self) -> None:
        self.agent_runs_deduplicated_total += 1

    def avg_runtime_seconds(self) -> float:
        if self._runtime_count == 0:
            return 0.0
        return round(self._runtime_sum_ms / self._runtime_count / 1000, 3)

    def to_prometheus_lines(self, env: str) -> list[str]:
        return [
            "",
            "# HELP agent_runs_total Total agent monitoring runs (completed + failed)",
            "# TYPE agent_runs_total counter",
            f'agent_runs_total{{environment="{env}"}} {self.agent_runs_total}',
            "",
            "# HELP agent_runs_failed_total Total agent monitoring runs that failed",
            "# TYPE agent_runs_failed_total counter",
            f'agent_runs_failed_total{{environment="{env}"}} {self.agent_runs_failed_total}',
            "",
            "# HELP agent_findings_created_total Total agent findings created",
            "# TYPE agent_findings_created_total counter",
            f'agent_findings_created_total{{environment="{env}"}} {self.agent_findings_created_total}',
            "",
            "# HELP agent_alerts_created_total Total agent alerts created",
            "# TYPE agent_alerts_created_total counter",
            f'agent_alerts_created_total{{environment="{env}"}} {self.agent_alerts_created_total}',
            "",
            "# HELP agent_drafts_created_total Total recommendation drafts created",
            "# TYPE agent_drafts_created_total counter",
            f'agent_drafts_created_total{{environment="{env}"}} {self.agent_drafts_created_total}',
            "",
            "# HELP agent_runtime_seconds Average agent run duration in seconds",
            "# TYPE agent_runtime_seconds gauge",
            f'agent_runtime_seconds{{environment="{env}"}} {self.avg_runtime_seconds()}',
            "",
        ]


# Process-level singleton
agent_counters = _AgentCounters()
