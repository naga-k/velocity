"""Tests for Redis client — uses fakeredis, no real Redis needed."""

from __future__ import annotations

from app.redis_client import (
    cache_get,
    cache_set,
    get_redis,
    get_session_state,
    set_session_state,
)


class TestCacheHelpers:
    async def test_set_and_get(self):
        await cache_set("test:key", {"value": 42})
        result = await cache_get("test:key")
        assert result == {"value": 42}

    async def test_get_missing_key(self):
        result = await cache_get("nonexistent")
        assert result is None

    async def test_set_with_ttl(self):
        await cache_set("ttl:key", "hello", ttl=60)
        result = await cache_get("ttl:key")
        assert result == "hello"

    async def test_overwrite_value(self):
        await cache_set("ow:key", "first")
        await cache_set("ow:key", "second")
        result = await cache_get("ow:key")
        assert result == "second"


class TestSessionState:
    async def test_set_and_get_state(self):
        state = {"current_topic": "sprint planning", "context_loaded": True}
        await set_session_state("session-1", state)
        result = await get_session_state("session-1")
        assert result == state

    async def test_get_missing_state(self):
        result = await get_session_state("nonexistent")
        assert result is None


class TestGracefulFallback:
    async def test_cache_works_without_redis(self):
        """When Redis is None, cache operations should no-op without crashing."""
        import app.redis_client as redis_mod

        original = redis_mod._redis
        redis_mod._redis = None

        # These should not raise
        await cache_set("key", "value")
        result = await cache_get("key")
        assert result is None

        await set_session_state("s1", {"test": True})
        result = await get_session_state("s1")
        assert result is None

        redis_mod._redis = original

    async def test_get_redis_returns_instance(self):
        redis = get_redis()
        assert redis is not None
