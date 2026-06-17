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


# Process-level singleton — import in middleware and LLM client
counters = _Counters()


# ── Response schema ────────────────────────────────────────────────────────────


class MetricsResponse(BaseModel):
    uptime_seconds: float
    environment: str
    requests: dict[str, int]
    llm: dict[str, int]
    budget: dict[str, int | str]


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
    )
