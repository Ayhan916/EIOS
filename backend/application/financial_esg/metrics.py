"""M43 Financial ESG Prometheus counters — in-process singleton."""

from __future__ import annotations


class _FinancialESGCounters:
    def __init__(self) -> None:
        self.financial_esg_kpis_total: int = 0
        self.financial_kpi_measurements_total: int = 0
        self.taxonomy_assessments_total: int = 0
        self.green_revenue_records_total: int = 0
        self.green_capex_records_total: int = 0
        self.green_opex_records_total: int = 0
        self.finance_instruments_total: int = 0
        self.value_creation_initiatives_total: int = 0
        self.carbon_cost_models_total: int = 0
        self.cost_of_risk_assessments_total: int = 0
        self.financial_reports_total: int = 0
        self.financial_reports_finalized_total: int = 0
        self.disclosure_packages_total: int = 0
        self.capital_markets_assessments_total: int = 0
        self.climate_finance_analyses_total: int = 0

    def record_kpi_created(self) -> None:
        self.financial_esg_kpis_total += 1

    def record_measurement_recorded(self) -> None:
        self.financial_kpi_measurements_total += 1

    def record_taxonomy_assessment(self) -> None:
        self.taxonomy_assessments_total += 1

    def record_green_revenue(self) -> None:
        self.green_revenue_records_total += 1

    def record_green_capex(self) -> None:
        self.green_capex_records_total += 1

    def record_green_opex(self) -> None:
        self.green_opex_records_total += 1

    def record_finance_instrument(self) -> None:
        self.finance_instruments_total += 1

    def record_value_initiative(self) -> None:
        self.value_creation_initiatives_total += 1

    def record_carbon_cost_model(self) -> None:
        self.carbon_cost_models_total += 1

    def record_cost_of_risk(self) -> None:
        self.cost_of_risk_assessments_total += 1

    def record_report_generated(self) -> None:
        self.financial_reports_total += 1

    def record_report_finalized(self) -> None:
        self.financial_reports_finalized_total += 1

    def record_disclosure_package(self) -> None:
        self.disclosure_packages_total += 1

    def record_capital_markets_assessment(self) -> None:
        self.capital_markets_assessments_total += 1

    def record_climate_finance_analysis(self) -> None:
        self.climate_finance_analyses_total += 1

    def to_prometheus_lines(self, env: str) -> list[str]:
        metrics = [
            (
                "eios_financial_esg_kpis_total",
                "Total Financial ESG KPIs created",
                self.financial_esg_kpis_total,
            ),
            (
                "eios_financial_kpi_measurements_total",
                "Total KPI measurements recorded",
                self.financial_kpi_measurements_total,
            ),
            (
                "eios_taxonomy_assessments_total",
                "Total taxonomy alignment assessments",
                self.taxonomy_assessments_total,
            ),
            (
                "eios_green_revenue_records_total",
                "Total green revenue records",
                self.green_revenue_records_total,
            ),
            (
                "eios_green_capex_records_total",
                "Total green capex records",
                self.green_capex_records_total,
            ),
            (
                "eios_green_opex_records_total",
                "Total green opex records",
                self.green_opex_records_total,
            ),
            (
                "eios_finance_instruments_total",
                "Total sustainable finance instruments",
                self.finance_instruments_total,
            ),
            (
                "eios_value_creation_initiatives_total",
                "Total value creation initiatives",
                self.value_creation_initiatives_total,
            ),
            (
                "eios_carbon_cost_models_total",
                "Total carbon cost models",
                self.carbon_cost_models_total,
            ),
            (
                "eios_cost_of_risk_assessments_total",
                "Total cost of risk assessments",
                self.cost_of_risk_assessments_total,
            ),
            (
                "eios_financial_reports_total",
                "Total financial ESG reports generated",
                self.financial_reports_total,
            ),
            (
                "eios_financial_reports_finalized_total",
                "Total financial ESG reports finalized",
                self.financial_reports_finalized_total,
            ),
            (
                "eios_disclosure_packages_total",
                "Total investor disclosure packages",
                self.disclosure_packages_total,
            ),
            (
                "eios_capital_markets_assessments_total",
                "Total capital markets assessments",
                self.capital_markets_assessments_total,
            ),
            (
                "eios_climate_finance_analyses_total",
                "Total climate finance analyses",
                self.climate_finance_analyses_total,
            ),
        ]
        lines: list[str] = []
        for name, help_text, value in metrics:
            lines += [
                "",
                f"# HELP {name} {help_text}",
                f"# TYPE {name} counter",
                f'{name}{{environment="{env}"}} {value}',
            ]
        return lines


financial_esg_counters = _FinancialESGCounters()
