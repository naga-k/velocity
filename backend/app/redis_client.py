"""Async Redis client with graceful fallback.

If Redis is unavailable, operations log warnings and return None/defaults.
The app must never crash due to Redis being down.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def connect_redis() -> None:
    """Connect to Redis. Logs warning if unavailable — does not raise."""
    global _redis
    try:
        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        await _redis.ping()
        logger.info("Redis connected at %s", settings.redis_url)
    except Exception:
        logger.warning("Redis unavailable at %s — running without cache", settings.redis_url)
        _redis = None


async def disconnect_redis() -> None:
    """Close Redis connection if open."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis disconnected")


def get_redis() -> aioredis.Redis | None:
    """Return the shared Redis instance (or None if unavailable)."""
    return _redis


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Store a JSON-serializable value with TTL (seconds). No-op if Redis is down."""
    if _redis is None:
        return
    try:
        await _redis.set(key, json.dumps(value), ex=ttl)
    except Exception:
        logger.warning("Redis cache_set failed for key %s", key)


async def cache_get(key: str) -> Any | None:
    """Retrieve a cached value. Returns None if missing or Redis is down."""
    if _redis is None:
        return None
    try:
        raw = await _redis.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception:
        logger.warning("Redis cache_get failed for key %s", key)
        return None


# ---------------------------------------------------------------------------
# Session working memory
# ---------------------------------------------------------------------------

async def set_session_state(session_id: str, state: dict) -> None:
    """Store session working memory in Redis with 24h TTL."""
    await cache_set(f"session:{session_id}:state", state, ttl=86400)


async def get_session_state(session_id: str) -> dict | None:
    """Retrieve session working memory from Redis."""
    return await cache_get(f"session:{session_id}:state")
