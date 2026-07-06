"""Redis sliding-window rate limiter middleware.

Algorithm: sorted-set per (IP, route-prefix) key.
  - ZADD key NOW NOW
  - ZREMRANGEBYSCORE key -inf (NOW - window_seconds)
  - ZCARD key → count
  - EXPIRE key window_seconds

When Redis is unavailable the middleware degrades gracefully and passes the request.
"""

from __future__ import annotations

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Route-prefix → (max_requests, window_seconds)
_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login":                           (10, 60),    # 10 login attempts per minute per IP
    "/api/v1/auth/":                                (60, 60),    # 60 auth requests per minute
    "/api/v1/supplier-portal/assessment/":          (10, 3600),  # 10 submissions per IP per hour (CSDDD-015)
    "/api/v1/":                                     (300, 60),   # 300 API calls per minute
}
# Paths exempt from rate limiting (health, metrics)
_EXEMPT_PREFIXES = ("/health", "/metrics")


def _get_limit(path: str) -> tuple[int, int] | None:
    for prefix, limit in _LIMITS.items():
        if path.startswith(prefix):
            return limit
    return None


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        limit_cfg = _get_limit(path)
        if limit_cfg is None:
            return await call_next(request)

        max_requests, window_seconds = limit_cfg
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.client.host
        )
        redis_key = f"rl:{client_ip}:{path.split('/')[3] if path.count('/') >= 3 else 'root'}"

        try:
            from infrastructure.redis.client import get_redis
            redis = await get_redis()
            now = time.time()
            window_start = now - window_seconds

            pipe = redis.pipeline()
            pipe.zadd(redis_key, {str(now): now})
            pipe.zremrangebyscore(redis_key, "-inf", window_start)
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window_seconds)
            results = await pipe.execute()
            count = results[2]

            remaining = max(0, max_requests - count)
            reset_at = int(now) + window_seconds

            if count > max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests — please retry later."},
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at),
                        "Retry-After": str(window_seconds),
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_at)
            return response

        except Exception as exc:
            logger.warning("rate_limiter_redis_unavailable: %s", exc)
            return await call_next(request)
