"""HTTP Metrics Middleware (M46 — enhanced from M33).

Records per-request:
  - Prometheus latency histogram (eios_http_request_duration_seconds)
  - Prometheus per-route counter (eios_http_requests_total)
  - Active-request gauge (inc on entry, dec on exit)
  - Legacy in-process _Counters (kept for /metrics JSON endpoint backward compatibility)
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from infrastructure.observability.http_metrics import (
    http_requests_active,
    record_request,
)


class MetricsCounterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        http_requests_active.inc()
        try:
            response = await call_next(request)
        finally:
            http_requests_active.dec()

        duration = time.perf_counter() - start

        # FastAPI route template (e.g. "/evidences/{evidence_id}") — low cardinality
        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path

        record_request(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
            duration_seconds=duration,
        )

        # Legacy in-process counters (backward compat for /metrics JSON)
        from interfaces.api.routers.metrics import counters  # noqa: PLC0415

        counters.record_request(response.status_code)

        return response
