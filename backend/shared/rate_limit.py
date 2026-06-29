"""
In-process sliding-window rate limiter.

Implemented as FastAPI dependencies rather than middleware so that different
endpoint groups can carry different limits (auth vs API vs LLM).

Single-process only — sufficient for pilot deployment. Scale to Redis if
running multiple Uvicorn workers behind a load balancer.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from shared.config import settings

# {key: deque of timestamps (monotonic)}
_windows: dict[str, deque[float]] = defaultdict(deque)


def reset_for_tests() -> None:
    """Clear all rate-limit windows. Call from test fixtures only."""
    _windows.clear()


def _check(key: str, limit: int, window_seconds: int = 60) -> bool:
    """Return True if the request is within the limit, False if it should be rejected."""
    now = time.monotonic()
    cutoff = now - window_seconds
    dq = _windows[key]
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= limit:
        return False
    dq.append(now)
    return True


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_auth(request: Request) -> None:
    """Strict rate limit for authentication endpoints (login, register)."""
    key = f"auth:{_client_ip(request)}"
    if not _check(key, settings.rate_limit_auth_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please wait before trying again.",
            headers={"Retry-After": "60"},
        )


async def rate_limit_api(request: Request) -> None:
    """Standard rate limit for general API endpoints."""
    key = f"api:{_client_ip(request)}"
    if not _check(key, settings.rate_limit_api_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded. Please slow down your requests.",
            headers={"Retry-After": "60"},
        )


async def rate_limit_llm(request: Request) -> None:
    """Tighter rate limit for agent/workflow endpoints that invoke LLM APIs."""
    key = f"llm:{_client_ip(request)}"
    if not _check(key, settings.rate_limit_llm_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="LLM request rate limit exceeded. Please wait before submitting another analysis.",
            headers={"Retry-After": "60"},
        )
