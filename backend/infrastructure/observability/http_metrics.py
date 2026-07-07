"""Prometheus HTTP metrics — request latency histogram + active request gauge (M46).

Exposes:
  eios_http_request_duration_seconds{method, endpoint, status_code}
    — Histogram with SLO-relevant buckets (5ms … 30s)
  eios_http_requests_active
    — Gauge: number of requests currently in-flight
  eios_http_requests_total{method, endpoint, status_code}
    — Counter replacing the old in-process _Counters for per-route breakdown

These are registered once at module import time (prometheus_client singletons).
The MetricsCounterMiddleware calls record_request() after each response.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Latency histogram — buckets chosen to cover both fast API calls and slow LLM/S3 operations
http_request_duration = Histogram(
    "eios_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status_code"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# Active requests — useful for detecting request pile-ups
http_requests_active = Gauge(
    "eios_http_requests_active",
    "Number of HTTP requests currently being processed",
)

# Per-route counter (label cardinality kept low — endpoint is the FastAPI route template)
http_requests_total = Counter(
    "eios_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)


def record_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    label_status = str(status_code)
    http_request_duration.labels(
        method=method, endpoint=endpoint, status_code=label_status
    ).observe(duration_seconds)
    http_requests_total.labels(method=method, endpoint=endpoint, status_code=label_status).inc()
