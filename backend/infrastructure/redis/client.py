"""
Redis async client — single connection pool shared across the application.

Usage:
  from infrastructure.redis import get_redis
  redis = get_redis()
  await redis.set("key", "value", ex=60)

Startup/shutdown are called from app/main.py lifespan.
If Redis is unavailable (e.g. tests without Redis), get_redis() returns None
and callers must handle the None case with a graceful fallback.
"""

from __future__ import annotations

import structlog
from redis.asyncio import Redis, from_url

from shared.config import settings

logger = structlog.get_logger(__name__)

_redis: Redis | None = None


async def init_redis() -> None:
    global _redis
    try:
        client: Redis = from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        await client.ping()
        _redis = client
        logger.info("redis_connected", url=settings.redis_url.split("@")[-1])
    except Exception as exc:
        logger.warning(
            "redis_unavailable", error=str(exc), detail="Falling back to in-memory state"
        )
        _redis = None


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("redis_closed")


def get_redis() -> Redis | None:
    return _redis
