"""M38 Network Intelligence Prometheus Counters."""

from __future__ import annotations


class _NetworkCounters:
    def __init__(self) -> None:
        self.network_relationships_total: int = 0
        self.network_suggestions_total: int = 0
        self.network_exposures_total: int = 0
        self.network_clusters_total: int = 0
        self.network_resilience_calculations_total: int = 0

    def record_relationship_created(self) -> None:
        self.network_relationships_total += 1

    def record_suggestion_created(self) -> None:
        self.network_suggestions_total += 1

    def record_exposure_created(self) -> None:
        self.network_exposures_total += 1

    def record_cluster_created(self) -> None:
        self.network_clusters_total += 1

    def record_resilience_calculated(self) -> None:
        self.network_resilience_calculations_total += 1

    def to_prometheus_lines(self, env: str) -> list[str]:
        return [
            "",
            "# HELP eios_network_relationships_total Total supplier relationships created",
            "# TYPE eios_network_relationships_total counter",
            f'eios_network_relationships_total{{environment="{env}"}} {self.network_relationships_total}',
            "",
            "# HELP eios_network_suggestions_total Total suggested relationships generated",
            "# TYPE eios_network_suggestions_total counter",
            f'eios_network_suggestions_total{{environment="{env}"}} {self.network_suggestions_total}',
            "",
            "# HELP eios_network_exposures_total Total network exposure signals generated",
            "# TYPE eios_network_exposures_total counter",
            f'eios_network_exposures_total{{environment="{env}"}} {self.network_exposures_total}',
            "",
            "# HELP eios_network_clusters_total Total incident clusters created",
            "# TYPE eios_network_clusters_total counter",
            f'eios_network_clusters_total{{environment="{env}"}} {self.network_clusters_total}',
            "",
            "# HELP eios_network_resilience_calculations_total Total resilience assessments computed",
            "# TYPE eios_network_resilience_calculations_total counter",
            f'eios_network_resilience_calculations_total{{environment="{env}"}} {self.network_resilience_calculations_total}',
            "",
        ]


network_counters = _NetworkCounters()
