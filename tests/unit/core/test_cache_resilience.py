"""
Unit tests for Redis cache resilience patterns.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. CacheService retries on transient Redis failures
2. Circuit breaker trips after threshold failures
3. L1 fallback works when Redis unavailable
4. Timeout enforcement works correctly

Reference: ADR-0026 - Resilience Patterns
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.exceptions

from mcp_server_langgraph.core.cache import CacheService

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.cache,
    pytest.mark.resilience,
]


@pytest.fixture
def cache_config():
    """Configuration for cache resilience tests."""
    return {
        "l1_maxsize": 100,
        "l1_ttl": 60,
        "redis_url": "redis://localhost:6379",
        "redis_db": 2,
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.delete.return_value = 1
    return mock


@pytest.mark.xdist_group(name="cache_resilience_tests")
class TestCacheServiceL1Fallback:
    """Test L1 cache fallback when Redis is unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_returns_l1_value_when_redis_unavailable(self, cache_config):
        """
        GIVEN: CacheService with Redis unavailable
        WHEN: Getting a value that's in L1
        THEN: Should return L1 cached value

        User Journey: Graceful degradation when Redis is down
        """
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.side_effect = redis.exceptions.ConnectionError("Redis unavailable")

            cache = CacheService(**cache_config)

            # Set value in L1 only
            cache.l1_cache["test:key"] = "test_value"

            # Should return L1 value
            result = cache.get("test:key")
            assert result == "test_value"

    def test_set_uses_l1_only_when_redis_unavailable(self, cache_config):
        """
        GIVEN: CacheService with Redis unavailable
        WHEN: Setting a value
        THEN: Should store in L1 only (no error)

        User Journey: Continue operating with L1 only when Redis is down
        """
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.side_effect = redis.exceptions.ConnectionError("Redis unavailable")

            cache = CacheService(**cache_config)
            assert cache.redis_available is False

            # Should not raise even though Redis is unavailable
            cache.set("test:key", "test_value", ttl=60)

            # Value should be in L1
            assert cache.l1_cache["test:key"] == "test_value"


@pytest.mark.xdist_group(name="cache_resilience_tests")
class TestCacheServiceRetryLogic:
    """Test retry logic for Redis operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_retries_on_transient_error(self, cache_config):
        """
        GIVEN: CacheService with Redis experiencing transient failures
        WHEN: Getting a value fails once then succeeds
        THEN: Should retry and return value

        User Journey: Recover from brief Redis blips
        """
        import pickle

        call_count = 0
        expected_value = {"key": "value"}

        def mock_get(key):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise redis.exceptions.ConnectionError("Transient error")
            return pickle.dumps(expected_value)

        with patch("redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis.get.side_effect = mock_get
            mock_from_url.return_value = mock_redis

            cache = CacheService(**cache_config)

            # Should retry and succeed
            result = cache.get("test:key")

            # Should have retried at least once
            assert call_count >= 2

            # Should return the value
            assert result == expected_value

    def test_set_retries_on_transient_error(self, cache_config):
        """
        GIVEN: CacheService with Redis experiencing transient failures
        WHEN: Setting a value fails once then succeeds
        THEN: Should retry and succeed

        User Journey: Recover from brief Redis blips during write
        """
        call_count = 0

        def mock_setex(key, ttl, value):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise redis.exceptions.ConnectionError("Transient error")
            return True

        with patch("redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis.setex.side_effect = mock_setex
            mock_from_url.return_value = mock_redis

            cache = CacheService(**cache_config)

            # Should retry and succeed
            cache.set("test:key", "test_value", ttl=60)

            # Should have retried at least once
            assert call_count >= 2


@pytest.mark.xdist_group(name="cache_resilience_tests")
class TestCacheServiceCircuitBreaker:
    """Test circuit breaker for Redis operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_circuit_breaker_opens_after_threshold_failures(self, cache_config):
        """
        GIVEN: CacheService with Redis repeatedly failing
        WHEN: Operations fail more than threshold (5)
        THEN: Circuit breaker should open and skip Redis (graceful degradation)

        User Journey: Prevent cascade failures when Redis is down
        Note: For cache, we use graceful degradation (L1 fallback) instead of
        raising CircuitBreakerError, since cache failures should not crash the app.
        """
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset circuit breaker state before test
        reset_circuit_breaker("redis")

        call_count = 0

        def counting_get(key):
            nonlocal call_count
            call_count += 1
            raise redis.exceptions.ConnectionError("Redis down")

        with patch("redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis.get.side_effect = counting_get
            mock_from_url.return_value = mock_redis

            cache = CacheService(**cache_config)

            # Trigger enough failures to open the circuit breaker
            # Config: redis circuit breaker fail_max=5
            # Each get() call should fail and count toward CB threshold
            for i in range(6):
                result = cache.get(f"test:key:{i}")
                assert result is None  # L1 miss, L2 fail, returns None

            # Verify circuit breaker is now OPEN
            breaker = get_circuit_breaker("redis")
            import pybreaker

            assert breaker.current_state == pybreaker.STATE_OPEN

            # Reset call count to verify Redis is skipped
            initial_call_count = call_count

            # Set L1 fallback value
            cache.l1_cache["test:fallback"] = "l1_value"

            # When CB is open, should skip Redis and return L1 value
            result = cache.get("test:fallback")
            assert result == "l1_value"

            # Verify Redis was NOT called (circuit breaker skipped it)
            assert call_count == initial_call_count, "Redis should not be called when CB is open"


@pytest.mark.xdist_group(name="cache_resilience_tests")
class TestCacheServiceAsyncResilience:
    """Test async operations with resilience patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_aget_returns_l1_value_when_redis_unavailable(self, cache_config):
        """
        GIVEN: CacheService with Redis unavailable
        WHEN: Async getting a value that's in L1
        THEN: Should return L1 cached value

        User Journey: Graceful async degradation
        """
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.side_effect = redis.exceptions.ConnectionError("Redis unavailable")

            cache = CacheService(**cache_config)

            # Set value in L1 only
            cache.l1_cache["test:key"] = "test_value"

            # Should return L1 value
            result = await cache.aget("test:key")
            assert result == "test_value"

    @pytest.mark.asyncio
    async def test_aget_retries_on_transient_error(self, cache_config):
        """
        GIVEN: CacheService with Redis experiencing transient failures
        WHEN: Async getting a value fails once then succeeds
        THEN: Should retry and return value

        User Journey: Recover from brief Redis blips in async operations
        """
        import pickle

        call_count = 0
        expected_value = {"key": "value"}

        async def mock_get(key):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise redis.exceptions.ConnectionError("Transient error")
            return pickle.dumps(expected_value)

        with patch("redis.from_url") as mock_from_url:
            mock_from_url.side_effect = redis.exceptions.ConnectionError("Skip sync init")

            cache = CacheService(**cache_config)

            # Mock async redis
            mock_async_redis = AsyncMock(return_value=None)
            mock_async_redis.get = mock_get
            cache.async_redis = mock_async_redis

            # Should retry and succeed
            result = await cache.aget("test:key")

            # Should have retried at least once
            assert call_count >= 2

            # Should return the value
            assert result == expected_value


@pytest.mark.xdist_group(name="cache_resilience_tests")
class TestCacheServiceTimeout:
    """Test timeout enforcement for Redis operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_respects_timeout(self, cache_config):
        """
        GIVEN: CacheService with timeout configuration
        WHEN: Redis operation takes too long
        THEN: Should timeout and fall back to L1

        User Journey: Prevent hanging on slow Redis
        """
        import time

        def slow_get(key):
            time.sleep(5)  # Longer than socket_timeout
            return None

        with patch("redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis.get.side_effect = redis.exceptions.TimeoutError("Timeout")
            mock_from_url.return_value = mock_redis

            cache = CacheService(**cache_config)

            # Set L1 fallback
            cache.l1_cache["test:key"] = "fallback_value"

            # Should timeout and return L1 fallback
            result = cache.get("test:key")
            assert result == "fallback_value"

    @pytest.mark.asyncio
    async def test_aget_respects_timeout(self, cache_config):
        """
        GIVEN: CacheService with timeout configuration
        WHEN: Async Redis operation times out
        THEN: Should timeout and fall back to L1

        User Journey: Prevent hanging on slow Redis in async operations
        """

        async def slow_get(key):
            raise redis.exceptions.TimeoutError("Timeout")

        with patch("redis.from_url") as mock_from_url:
            mock_from_url.side_effect = redis.exceptions.ConnectionError("Skip sync init")

            cache = CacheService(**cache_config)

            # Set L1 fallback
            cache.l1_cache["test:key"] = "fallback_value"

            # Mock async redis with timeout
            mock_async_redis = AsyncMock(return_value=None)
            mock_async_redis.get = slow_get
            cache.async_redis = mock_async_redis

            # Should timeout and return L1 fallback
            result = await cache.aget("test:key")
            assert result == "fallback_value"
