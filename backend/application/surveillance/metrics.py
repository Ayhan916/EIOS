"""M37 Surveillance Prometheus Counters.

In-process singleton. Exposed at GET /metrics/prometheus.
"""

from __future__ import annotations


class _SurveillanceCounters:
    def __init__(self) -> None:
        self.surveillance_signals_total: int = 0
        self.surveillance_signals_active: int = 0
        self.surveillance_episodes_total: int = 0
        self.surveillance_watchlist_total: int = 0
        self.surveillance_escalations_total: int = 0
        self._signals_by_severity: dict[str, int] = {}

    def record_signal_created(self, severity: str = "MEDIUM") -> None:
        self.surveillance_signals_total += 1
        self.surveillance_signals_active += 1
        self._signals_by_severity[severity] = (
            self._signals_by_severity.get(severity, 0) + 1
        )

    def record_signal_resolved(self) -> None:
        if self.surveillance_signals_active > 0:
            self.surveillance_signals_active -= 1

    def record_episode_created(self) -> None:
        self.surveillance_episodes_total += 1

    def record_watchlist_added(self) -> None:
        self.surveillance_watchlist_total += 1

    def record_escalation(self) -> None:
        self.surveillance_escalations_total += 1

    def to_prometheus_lines(self, env: str) -> list[str]:
        lines = [
            "",
            "# HELP eios_surveillance_signals_total Total surveillance signals generated",
            "# TYPE eios_surveillance_signals_total counter",
            f'eios_surveillance_signals_total{{environment="{env}"}} {self.surveillance_signals_total}',
            "",
            "# HELP eios_surveillance_signals_active Currently active surveillance signals",
            "# TYPE eios_surveillance_signals_active gauge",
            f'eios_surveillance_signals_active{{environment="{env}"}} {self.surveillance_signals_active}',
            "",
            "# HELP eios_surveillance_episodes_total Total risk episodes created",
            "# TYPE eios_surveillance_episodes_total counter",
            f'eios_surveillance_episodes_total{{environment="{env}"}} {self.surveillance_episodes_total}',
            "",
            "# HELP eios_surveillance_watchlist_total Total supplier watchlist entries",
            "# TYPE eios_surveillance_watchlist_total counter",
            f'eios_surveillance_watchlist_total{{environment="{env}"}} {self.surveillance_watchlist_total}',
            "",
            "# HELP eios_surveillance_escalations_total Total predictive escalations",
            "# TYPE eios_surveillance_escalations_total counter",
            f'eios_surveillance_escalations_total{{environment="{env}"}} {self.surveillance_escalations_total}',
            "",
        ]
        return lines


surveillance_counters = _SurveillanceCounters()
