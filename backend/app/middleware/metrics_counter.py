"""
Metrics Counter Middleware

Increments the in-process request counters (in interfaces/api/routers/metrics.py)
after each response so the /metrics endpoint reflects live traffic.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class MetricsCounterMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        # Import lazily to avoid circular imports at module load time
        from interfaces.api.routers.metrics import counters
        counters.record_request(response.status_code)
        return response
