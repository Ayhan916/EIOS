"""Dedicated Redis connection for the JWT blacklist (M45.2).

Security requirement:
  The JWT blacklist must NEVER evict entries — an evicted blacklist entry means
  a revoked token silently becomes valid again.

This client connects to a separate Redis instance (or logical DB) configured
with maxmemory-policy=noeviction so OOM errors are raised instead of evicting.

The rate-limiting and session clients (infrastructure/redis/client.py) use the
main Redis instance with allkeys-lru, which may evict old sliding-window data
safely.  They are never connected to this client.

Configuration:
  REDIS_BLACKLIST_URL=redis://:password@redis-blacklist:6379/0
  Defaults to redis://localhost:6379/1 (DB=1 of the dev Redis instance).
"""

from __future__ import annotations

import structlog
from redis.asyncio import Redis, from_url

from shared.config import settings

logger = structlog.get_logger(__name__)

_blacklist: Redis | None = None


async def init_redis_blacklist() -> None:
    global _blacklist
    try:
        client: Redis = from_url(
            settings.redis_blacklist_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        await client.ping()
        _blacklist = client
        logger.info("redis_blacklist_connected", url=settings.redis_blacklist_url.split("@")[-1])
    except Exception as exc:
        logger.warning(
            "redis_blacklist_unavailable",
            error=str(exc),
            detail="Token blacklist will not function — revoked tokens may be reused",
        )
        _blacklist = None


async def close_redis_blacklist() -> None:
    global _blacklist
    if _blacklist is not None:
        await _blacklist.aclose()
        _blacklist = None
        logger.info("redis_blacklist_closed")


def get_redis_blacklist() -> Redis | None:
    return _blacklist
