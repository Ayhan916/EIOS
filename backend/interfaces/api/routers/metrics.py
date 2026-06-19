"""
Operational Metrics Endpoint

Returns lightweight in-process counters as JSON. Intended for:
  - ops dashboards during pilot
  - alerting rules (e.g. error_rate > 5%)
  - LLM spend visibility

Not a replacement for Prometheus — upgrade to prometheus-client and a scrape
job when moving to a managed infrastructure tier.

Access is open (no auth) because this endpoint reveals no user data.
Restrict via network policy / nginx allow-list in production.
"""

import time

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from shared.config import settings

router = APIRouter(tags=["metrics"])

_start_time = time.time()


# ── In-process counters ────────────────────────────────────────────────────────


class _Counters:
    def __init__(self) -> None:
        self.requests_total: int = 0
        self.requests_2xx: int = 0
        self.requests_4xx: int = 0
        self.requests_5xx: int = 0
        self.llm_calls_total: int = 0
        self.llm_tokens_total: int = 0
        self.llm_errors_total: int = 0
        # Webhook delivery counters (process-lifetime totals; reset on restart)
        self.webhook_deliveries_total: int = 0
        self.webhook_deliveries_succeeded: int = 0
        self.webhook_deliveries_failed: int = 0
        self.webhook_deliveries_dead_letter: int = 0
        # Report counters
        self.board_reports_generated: int = 0
        self.board_report_pdfs_downloaded: int = 0
        # API key usage
        self.api_key_requests_total: int = 0

    def record_request(self, status_code: int) -> None:
        self.requests_total += 1
        if 200 <= status_code < 300:
            self.requests_2xx += 1
        elif 400 <= status_code < 500:
            self.requests_4xx += 1
        elif status_code >= 500:
            self.requests_5xx += 1

    def record_llm_call(self, tokens: int, error: bool = False) -> None:
        self.llm_calls_total += 1
        self.llm_tokens_total += tokens
        if error:
            self.llm_errors_total += 1

    def record_webhook_delivery(self, *, succeeded: bool, dead_letter: bool = False) -> None:
        self.webhook_deliveries_total += 1
        if succeeded:
            self.webhook_deliveries_succeeded += 1
        elif dead_letter:
            self.webhook_deliveries_dead_letter += 1
        else:
            self.webhook_deliveries_failed += 1

    def record_board_report_generated(self) -> None:
        self.board_reports_generated += 1

    def record_board_report_downloaded(self) -> None:
        self.board_report_pdfs_downloaded += 1

    def record_api_key_request(self) -> None:
        self.api_key_requests_total += 1


# Process-level singleton — import in middleware and LLM client
counters = _Counters()


# ── Response schema ────────────────────────────────────────────────────────────


class MetricsResponse(BaseModel):
    uptime_seconds: float
    environment: str
    requests: dict[str, int]
    llm: dict[str, int]
    budget: dict[str, int | str]
    webhooks: dict[str, int]
    reports: dict[str, int]
    api_keys: dict[str, int]


@router.get("/metrics", response_model=MetricsResponse, include_in_schema=True)
async def get_metrics() -> MetricsResponse:
    """
    Return operational metrics for the running process.
    LLM budget shows system-wide token budget (per-org use the admin API).
    """
    uptime = round(time.time() - _start_time, 1)
    budget = settings.llm_monthly_token_budget
    return MetricsResponse(
        uptime_seconds=uptime,
        environment=settings.environment,
        requests={
            "total": counters.requests_total,
            "2xx": counters.requests_2xx,
            "4xx": counters.requests_4xx,
            "5xx": counters.requests_5xx,
        },
        llm={
            "calls_total": counters.llm_calls_total,
            "tokens_total": counters.llm_tokens_total,
            "errors_total": counters.llm_errors_total,
        },
        budget={
            "monthly_token_budget": budget,
            "policy": "unlimited" if budget == 0 else "enforced",
        },
        webhooks={
            "deliveries_total": counters.webhook_deliveries_total,
            "deliveries_succeeded": counters.webhook_deliveries_succeeded,
            "deliveries_failed": counters.webhook_deliveries_failed,
            "deliveries_dead_letter": counters.webhook_deliveries_dead_letter,
        },
        reports={
            "board_reports_generated": counters.board_reports_generated,
            "board_report_pdfs_downloaded": counters.board_report_pdfs_downloaded,
        },
        api_keys={
            "requests_total": counters.api_key_requests_total,
        },
    )


@router.get("/metrics/prometheus", response_class=PlainTextResponse, include_in_schema=True)
async def get_metrics_prometheus() -> str:
    """Prometheus text-format metrics for scraping by Prometheus or Grafana Agent."""
    uptime = round(time.time() - _start_time, 1)
    env = settings.environment
    lines = [
        "# HELP eios_uptime_seconds Seconds since process start",
        "# TYPE eios_uptime_seconds gauge",
        f'eios_uptime_seconds{{environment="{env}"}} {uptime}',
        "",
        "# HELP eios_requests_total Total HTTP requests handled",
        "# TYPE eios_requests_total counter",
        f'eios_requests_total{{status="2xx",environment="{env}"}} {counters.requests_2xx}',
        f'eios_requests_total{{status="4xx",environment="{env}"}} {counters.requests_4xx}',
        f'eios_requests_total{{status="5xx",environment="{env}"}} {counters.requests_5xx}',
        "",
        "# HELP eios_llm_calls_total Total LLM workflow calls completed",
        "# TYPE eios_llm_calls_total counter",
        f'eios_llm_calls_total{{environment="{env}"}} {counters.llm_calls_total}',
        "",
        "# HELP eios_llm_tokens_total Total LLM tokens consumed",
        "# TYPE eios_llm_tokens_total counter",
        f'eios_llm_tokens_total{{environment="{env}"}} {counters.llm_tokens_total}',
        "",
        "# HELP eios_llm_errors_total Total LLM call errors",
        "# TYPE eios_llm_errors_total counter",
        f'eios_llm_errors_total{{environment="{env}"}} {counters.llm_errors_total}',
        "",
        "# HELP eios_webhook_deliveries_total Total webhook delivery attempts",
        "# TYPE eios_webhook_deliveries_total counter",
        f'eios_webhook_deliveries_total{{environment="{env}"}} {counters.webhook_deliveries_total}',
        "",
        "# HELP eios_webhook_deliveries_succeeded_total Webhook deliveries that returned 2xx",
        "# TYPE eios_webhook_deliveries_succeeded_total counter",
        f'eios_webhook_deliveries_succeeded_total{{environment="{env}"}} {counters.webhook_deliveries_succeeded}',
        "",
        "# HELP eios_webhook_deliveries_failed_total Webhook deliveries that failed and will be retried",
        "# TYPE eios_webhook_deliveries_failed_total counter",
        f'eios_webhook_deliveries_failed_total{{environment="{env}"}} {counters.webhook_deliveries_failed}',
        "",
        "# HELP eios_webhook_deliveries_dead_letter_total Webhook deliveries that exhausted all retries",
        "# TYPE eios_webhook_deliveries_dead_letter_total counter",
        f'eios_webhook_deliveries_dead_letter_total{{environment="{env}"}} {counters.webhook_deliveries_dead_letter}',
        "",
        "# HELP eios_board_reports_generated_total Board reports generated",
        "# TYPE eios_board_reports_generated_total counter",
        f'eios_board_reports_generated_total{{environment="{env}"}} {counters.board_reports_generated}',
        "",
        "# HELP eios_board_report_pdfs_downloaded_total Board report PDFs downloaded",
        "# TYPE eios_board_report_pdfs_downloaded_total counter",
        f'eios_board_report_pdfs_downloaded_total{{environment="{env}"}} {counters.board_report_pdfs_downloaded}',
        "",
        "# HELP eios_api_key_requests_total Total requests authenticated via API key",
        "# TYPE eios_api_key_requests_total counter",
        f'eios_api_key_requests_total{{environment="{env}"}} {counters.api_key_requests_total}',
        "",
    ]
    # Append M34.1 external intelligence metrics
    from application.external_intelligence.metrics import ext_counters
    lines.extend(ext_counters.to_prometheus_lines(env))
    return "\n".join(lines)
