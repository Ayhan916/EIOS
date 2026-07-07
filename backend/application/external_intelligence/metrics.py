"""M34.1 External Intelligence Metrics.

Extends the existing EIOS in-process counter pattern with M34.1 counters.
All M34.1 metrics are exposed at /metrics and /metrics/prometheus.
"""

from __future__ import annotations


class _ExtCounters:
    """Process-level M34.1 intelligence metrics."""

    def __init__(self) -> None:
        # Dataset refresh
        self.dataset_refresh_total: int = 0
        self.dataset_refresh_failed_total: int = 0
        # Per-connector totals (keyed by connector_name)
        self._connector_refresh: dict[str, int] = {}
        self._connector_failures: dict[str, int] = {}
        self._connector_runtime_sum: dict[str, float] = {}
        self._connector_runtime_count: dict[str, int] = {}
        # Sanctions signals
        self.sanctions_updates_total: int = 0
        # Benchmark refresh
        self.benchmark_refresh_total: int = 0
        # Validation
        self.dataset_validation_failures: int = 0
        self.dataset_quarantined_total: int = 0

    def record_dataset_refresh(self, connector_name: str, *, success: bool) -> None:
        self.dataset_refresh_total += 1
        if not success:
            self.dataset_refresh_failed_total += 1
        self._connector_refresh[connector_name] = self._connector_refresh.get(connector_name, 0) + 1

    def record_connector_failure(self, connector_name: str) -> None:
        # M4: dataset_refresh_failed_total is incremented by record_dataset_refresh(success=False)
        # This only tracks per-connector failure count for dashboard display
        self._connector_failures[connector_name] = (
            self._connector_failures.get(connector_name, 0) + 1
        )

    def record_connector_runtime(self, connector_name: str, runtime_seconds: float) -> None:
        self._connector_runtime_sum[connector_name] = (
            self._connector_runtime_sum.get(connector_name, 0.0) + runtime_seconds
        )
        self._connector_runtime_count[connector_name] = (
            self._connector_runtime_count.get(connector_name, 0) + 1
        )

    def record_sanctions_update(self) -> None:
        self.sanctions_updates_total += 1

    def record_benchmark_refresh(self) -> None:
        self.benchmark_refresh_total += 1

    def record_validation_failure(self, *, quarantined: bool = False) -> None:
        self.dataset_validation_failures += 1
        if quarantined:
            self.dataset_quarantined_total += 1

    def connector_failures(self, connector_name: str) -> int:
        return self._connector_failures.get(connector_name, 0)

    def connector_refreshes(self, connector_name: str) -> int:
        return self._connector_refresh.get(connector_name, 0)

    def connector_avg_runtime(self, connector_name: str) -> float:
        count = self._connector_runtime_count.get(connector_name, 0)
        total = self._connector_runtime_sum.get(connector_name, 0.0)
        return round(total / count, 3) if count > 0 else 0.0

    def all_connectors(self) -> list[str]:
        return sorted(set(self._connector_refresh) | set(self._connector_failures))

    def to_prometheus_lines(self, env: str) -> list[str]:
        lines = [
            "",
            "# HELP eios_external_dataset_refresh_total Total external dataset refresh attempts",
            "# TYPE eios_external_dataset_refresh_total counter",
            f'eios_external_dataset_refresh_total{{environment="{env}"}} {self.dataset_refresh_total}',
            "",
            "# HELP eios_external_dataset_refresh_failed_total Failed external dataset refreshes",
            "# TYPE eios_external_dataset_refresh_failed_total counter",
            f'eios_external_dataset_refresh_failed_total{{environment="{env}"}} {self.dataset_refresh_failed_total}',
            "",
            "# HELP eios_sanctions_updates_total Total sanctions signal updates created",
            "# TYPE eios_sanctions_updates_total counter",
            f'eios_sanctions_updates_total{{environment="{env}"}} {self.sanctions_updates_total}',
            "",
            "# HELP eios_benchmark_refresh_total Total benchmark recalculations triggered",
            "# TYPE eios_benchmark_refresh_total counter",
            f'eios_benchmark_refresh_total{{environment="{env}"}} {self.benchmark_refresh_total}',
            "",
        ]
        for name in self.all_connectors():
            n = name.replace("-", "_")
            lines += [
                f'# HELP eios_connector_failures_total{{connector="{n}"}} Connector failure count',
                "# TYPE eios_connector_failures_total counter",
                f'eios_connector_failures_total{{connector="{n}",environment="{env}"}} {self.connector_failures(name)}',
                "",
                f"# HELP eios_connector_runtime_seconds_avg Average runtime for {name}",
                "# TYPE eios_connector_runtime_seconds_avg gauge",
                f'eios_connector_runtime_seconds_avg{{connector="{n}",environment="{env}"}} {self.connector_avg_runtime(name)}',
                "",
            ]
        return lines


# Process-level singleton
ext_counters = _ExtCounters()
