"""
Sliding-window rate limiter implemented as FastAPI dependencies.

Primary backend: Redis (atomic pipeline, correct under multiple workers).
Fallback: In-process defaultdict/deque (single-worker only, used when Redis
is unavailable — e.g. in unit tests or during Redis restart).

Different endpoint groups carry different limits (auth vs API vs LLM).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from shared.config import settings

# ── In-memory fallback (single-process only) ──────────────────────────────────

_windows: dict[str, deque[float]] = defaultdict(deque)


def reset_for_tests() -> None:
    """Clear all rate-limit windows. Call from test fixtures only."""
    _windows.clear()


def _check_memory(key: str, limit: int, window_seconds: int = 60) -> bool:
    now = time.monotonic()
    cutoff = now - window_seconds
    dq = _windows[key]
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= limit:
        return False
    dq.append(now)
    return True


# ── Redis sliding window ──────────────────────────────────────────────────────


async def _check_redis(key: str, limit: int, window_seconds: int = 60) -> bool:
    from infrastructure.redis.client import get_redis

    redis = get_redis()
    if redis is None:
        return _check_memory(key, limit, window_seconds)

    now = time.time()
    window_start = now - window_seconds
    try:
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {f"{now:.6f}": now})
        pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()
        count_before = results[1]
        return count_before < limit
    except Exception:
        return _check_memory(key, limit, window_seconds)


# ── IP extraction ─────────────────────────────────────────────────────────────


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── FastAPI dependencies ──────────────────────────────────────────────────────


# Aliases for tests that reference the in-memory implementation directly
_check = _check_memory


async def rate_limit_auth(request: Request) -> None:
    """Strict rate limit for authentication endpoints (login, register)."""
    key = f"rl:auth:{_client_ip(request)}"
    if not await _check_redis(key, settings.rate_limit_auth_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please wait before trying again.",
            headers={"Retry-After": "60"},
        )


async def rate_limit_api(request: Request) -> None:
    """Standard rate limit for general API endpoints."""
    key = f"rl:api:{_client_ip(request)}"
    if not await _check_redis(key, settings.rate_limit_api_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded. Please slow down your requests.",
            headers={"Retry-After": "60"},
        )


async def rate_limit_llm(request: Request) -> None:
    """Tighter rate limit for agent/workflow endpoints that invoke LLM APIs."""
    key = f"rl:llm:{_client_ip(request)}"
    if not await _check_redis(key, settings.rate_limit_llm_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="LLM request rate limit exceeded. Please wait before submitting another analysis.",
            headers={"Retry-After": "60"},
        )
