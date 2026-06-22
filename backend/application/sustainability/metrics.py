"""M42 Sustainability Prometheus Counters.

In-process singleton. Exposed at GET /metrics/prometheus.
"""

from __future__ import annotations


class _SustainabilityCounters:
    def __init__(self) -> None:
        self.sustainability_objectives_total: int = 0
        self.sustainability_targets_total: int = 0
        self.sustainability_kpis_total: int = 0
        self.sustainability_kpi_alerts_total: int = 0
        self.sustainability_reports_total: int = 0
        self.sustainability_reports_finalized_total: int = 0
        self.carbon_inventory_recalculations_total: int = 0
        self.carbon_inventories_finalized_total: int = 0
        self.decarbonization_initiatives_total: int = 0
        self.science_based_targets_total: int = 0
        self.climate_risk_assessments_total: int = 0
        self.sustainability_forecasts_total: int = 0

    def record_objective_created(self) -> None:
        self.sustainability_objectives_total += 1

    def record_target_created(self) -> None:
        self.sustainability_targets_total += 1

    def record_kpi_created(self) -> None:
        self.sustainability_kpis_total += 1

    def record_kpi_alert(self) -> None:
        self.sustainability_kpi_alerts_total += 1

    def record_report_generated(self) -> None:
        self.sustainability_reports_total += 1

    def record_report_finalized(self) -> None:
        self.sustainability_reports_finalized_total += 1

    def record_inventory_recalculation(self) -> None:
        self.carbon_inventory_recalculations_total += 1

    def record_inventory_finalized(self) -> None:
        self.carbon_inventories_finalized_total += 1

    def record_initiative_created(self) -> None:
        self.decarbonization_initiatives_total += 1

    def record_sbt_created(self) -> None:
        self.science_based_targets_total += 1

    def record_climate_risk_created(self) -> None:
        self.climate_risk_assessments_total += 1

    def record_forecast_created(self) -> None:
        self.sustainability_forecasts_total += 1

    def record_measurement_recorded(self) -> None:
        pass  # KPI measurements tracked via kpis_total; no separate Prometheus counter needed

    def record_inventory_recalculated(self) -> None:
        self.carbon_inventory_recalculations_total += 1

    def to_prometheus_lines(self, env: str) -> list[str]:
        return [
            "",
            "# HELP eios_sustainability_objectives_total Total ESG objectives created",
            "# TYPE eios_sustainability_objectives_total counter",
            f'eios_sustainability_objectives_total{{environment="{env}"}} {self.sustainability_objectives_total}',
            "",
            "# HELP eios_sustainability_targets_total Total ESG targets created",
            "# TYPE eios_sustainability_targets_total counter",
            f'eios_sustainability_targets_total{{environment="{env}"}} {self.sustainability_targets_total}',
            "",
            "# HELP eios_sustainability_kpis_total Total KPIs created",
            "# TYPE eios_sustainability_kpis_total counter",
            f'eios_sustainability_kpis_total{{environment="{env}"}} {self.sustainability_kpis_total}',
            "",
            "# HELP eios_sustainability_kpi_alerts_total Total KPI alerts triggered",
            "# TYPE eios_sustainability_kpi_alerts_total counter",
            f'eios_sustainability_kpi_alerts_total{{environment="{env}"}} {self.sustainability_kpi_alerts_total}',
            "",
            "# HELP eios_sustainability_reports_total Total sustainability reports generated",
            "# TYPE eios_sustainability_reports_total counter",
            f'eios_sustainability_reports_total{{environment="{env}"}} {self.sustainability_reports_total}',
            "",
            "# HELP eios_sustainability_reports_finalized_total Total reports finalized (immutable)",
            "# TYPE eios_sustainability_reports_finalized_total counter",
            f'eios_sustainability_reports_finalized_total{{environment="{env}"}} {self.sustainability_reports_finalized_total}',
            "",
            "# HELP eios_carbon_inventory_recalculations_total Total carbon inventory recalculations",
            "# TYPE eios_carbon_inventory_recalculations_total counter",
            f'eios_carbon_inventory_recalculations_total{{environment="{env}"}} {self.carbon_inventory_recalculations_total}',
            "",
            "# HELP eios_carbon_inventories_finalized_total Total carbon inventories finalized",
            "# TYPE eios_carbon_inventories_finalized_total counter",
            f'eios_carbon_inventories_finalized_total{{environment="{env}"}} {self.carbon_inventories_finalized_total}',
            "",
            "# HELP eios_decarbonization_initiatives_total Total decarbonization initiatives created",
            "# TYPE eios_decarbonization_initiatives_total counter",
            f'eios_decarbonization_initiatives_total{{environment="{env}"}} {self.decarbonization_initiatives_total}',
            "",
            "# HELP eios_science_based_targets_total Total science-based targets created",
            "# TYPE eios_science_based_targets_total counter",
            f'eios_science_based_targets_total{{environment="{env}"}} {self.science_based_targets_total}',
            "",
            "# HELP eios_climate_risk_assessments_total Total climate risk assessments",
            "# TYPE eios_climate_risk_assessments_total counter",
            f'eios_climate_risk_assessments_total{{environment="{env}"}} {self.climate_risk_assessments_total}',
            "",
            "# HELP eios_sustainability_forecasts_total Total performance forecasts created",
            "# TYPE eios_sustainability_forecasts_total counter",
            f'eios_sustainability_forecasts_total{{environment="{env}"}} {self.sustainability_forecasts_total}',
            "",
        ]


sustainability_counters = _SustainabilityCounters()
