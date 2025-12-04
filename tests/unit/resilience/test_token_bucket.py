"""
Unit tests for token bucket rate limiter.

TDD tests for pre-emptive rate limiting with burst capacity:
- Token bucket allows short bursts up to capacity
- Refills tokens at a steady rate
- Blocks/delays when bucket is empty
- Provider-aware token bucket configurations

The token bucket algorithm is a standard rate limiting pattern that:
1. Allows bursting when tokens are available
2. Limits sustained throughput to refill rate
3. Provides smoother request distribution than hard RPM limits

Reference: https://en.wikipedia.org/wiki/Token_bucket
"""

import asyncio
import gc
import time
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


# =============================================================================
# Test Token Bucket Core Functionality
# =============================================================================


@pytest.mark.xdist_group(name="token_bucket")
class TestTokenBucketCore:
    """Test core token bucket functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_token_bucket_init(self):
        """TokenBucket should initialize with capacity and refill rate."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 10  # Starts full

    @pytest.mark.unit
    def test_token_bucket_acquire_single(self):
        """Should successfully acquire a single token when available."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.try_acquire() is True
        # Use approx due to refill timing
        assert bucket.tokens == pytest.approx(9, abs=0.1)

    @pytest.mark.unit
    def test_token_bucket_acquire_multiple(self):
        """Should acquire multiple tokens."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.try_acquire(tokens=5) is True
        # Use approx due to refill timing
        assert bucket.tokens == pytest.approx(5, abs=0.1)

    @pytest.mark.unit
    def test_token_bucket_deny_when_empty(self):
        """Should deny acquisition when not enough tokens available."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=2, refill_rate=1.0)
        assert bucket.try_acquire(tokens=2) is True  # Drain bucket
        assert bucket.try_acquire() is False  # No tokens left

    @pytest.mark.unit
    def test_token_bucket_deny_exceeds_capacity(self):
        """Should deny if requested tokens exceed capacity."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        assert bucket.try_acquire(tokens=10) is False  # More than capacity

    @pytest.mark.unit
    def test_token_bucket_refill_over_time(self):
        """Tokens should refill based on elapsed time."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec
        bucket.try_acquire(tokens=10)  # Drain all tokens
        # Due to refill on access, tokens may be slightly above 0
        assert bucket.tokens == pytest.approx(0, abs=0.1)

        # Simulate time passing
        bucket._last_refill = time.monotonic() - 0.5  # 0.5s ago
        bucket._refill()

        # Should have ~5 tokens (10 * 0.5)
        assert bucket.tokens >= 4  # Allow some timing variance
        assert bucket.tokens <= 6

    @pytest.mark.unit
    def test_token_bucket_refill_caps_at_capacity(self):
        """Refill should not exceed bucket capacity."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=100.0)  # Fast refill
        bucket.try_acquire(tokens=5)  # Use half

        # Simulate long time passing
        bucket._last_refill = time.monotonic() - 10  # 10s ago
        bucket._refill()

        # Should cap at capacity
        assert bucket.tokens == 10


# =============================================================================
# Test Async Token Bucket
# =============================================================================


@pytest.mark.xdist_group(name="token_bucket")
class TestTokenBucketAsync:
    """Test async token bucket operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_acquire_immediate(self):
        """Should acquire immediately when tokens available."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        start = time.monotonic()
        await bucket.acquire()
        elapsed = time.monotonic() - start

        assert elapsed < 0.1  # Should be near-instant
        # Use approx due to refill timing
        assert bucket.tokens == pytest.approx(9, abs=0.1)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_acquire_waits_when_empty(self):
        """Should wait for refill when bucket is empty."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=1, refill_rate=10.0)  # 10 tokens/sec
        await bucket.acquire()  # Drain the single token

        start = time.monotonic()
        await bucket.acquire()  # Must wait for refill
        elapsed = time.monotonic() - start

        # Should wait ~0.1s for 1 token at 10 tokens/sec
        assert elapsed >= 0.05  # Allow variance
        assert elapsed < 0.3  # But not too long

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_acquire_with_timeout(self):
        """Should raise TimeoutError if cannot acquire within timeout."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=1, refill_rate=0.1)  # Very slow: 0.1 tokens/sec
        await bucket.acquire()  # Drain bucket

        with pytest.raises(asyncio.TimeoutError):
            await bucket.acquire(timeout=0.1)  # Timeout before refill


# =============================================================================
# Test Provider Token Bucket Factory
# =============================================================================


@pytest.mark.xdist_group(name="token_bucket")
class TestProviderTokenBucket:
    """Test provider-specific token bucket configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        reset_all_token_buckets()

    @pytest.mark.unit
    def test_get_provider_token_bucket_creates_bucket(self):
        """Should create token bucket for provider."""
        from mcp_server_langgraph.resilience.rate_limit import TokenBucket, get_provider_token_bucket

        bucket = get_provider_token_bucket("anthropic")
        assert isinstance(bucket, TokenBucket)

    @pytest.mark.unit
    def test_get_provider_token_bucket_uses_provider_limits(self):
        """Should use provider-specific rate limits."""
        from mcp_server_langgraph.resilience.rate_limit import get_provider_token_bucket

        # Anthropic Tier 1: 50 RPM → ~0.83 requests/sec
        bucket = get_provider_token_bucket("anthropic")
        assert bucket.refill_rate > 0
        assert bucket.refill_rate <= 2.0  # Conservative

    @pytest.mark.unit
    def test_get_provider_token_bucket_caches(self):
        """Same provider should return same bucket."""
        from mcp_server_langgraph.resilience.rate_limit import get_provider_token_bucket

        bucket1 = get_provider_token_bucket("openai")
        bucket2 = get_provider_token_bucket("openai")
        assert bucket1 is bucket2

    @pytest.mark.unit
    def test_different_providers_different_buckets(self):
        """Different providers should have separate buckets."""
        from mcp_server_langgraph.resilience.rate_limit import get_provider_token_bucket

        anthropic = get_provider_token_bucket("anthropic")
        openai = get_provider_token_bucket("openai")
        assert anthropic is not openai

    @pytest.mark.unit
    def test_ollama_has_high_rate(self):
        """Ollama (local) should have very high rate limit."""
        from mcp_server_langgraph.resilience.rate_limit import get_provider_token_bucket

        bucket = get_provider_token_bucket("ollama")
        # Local model - should allow high throughput
        assert bucket.refill_rate >= 10.0


# =============================================================================
# Test Rate Limiter Decorator
# =============================================================================


@pytest.mark.xdist_group(name="token_bucket")
class TestRateLimiterDecorator:
    """Test rate limiter decorator for functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        reset_all_token_buckets()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limited_decorator_allows_burst(self):
        """Decorated function should allow burst up to capacity."""
        from mcp_server_langgraph.resilience.rate_limit import rate_limited

        call_count = 0

        @rate_limited(provider="test_burst", capacity=5, refill_rate=0.1)
        async def my_function():
            nonlocal call_count
            call_count += 1
            return "ok"

        # Should allow 5 rapid calls (burst)
        for _ in range(5):
            await my_function()

        assert call_count == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limited_decorator_throttles(self):
        """Decorated function should throttle after burst exhausted."""
        from mcp_server_langgraph.resilience.rate_limit import rate_limited

        # Use custom capacity/refill_rate WITHOUT provider to get deterministic behavior
        # capacity=1 with slow refill_rate=2.0 means ~0.5s wait for each token
        @rate_limited(capacity=1, refill_rate=2.0)
        async def my_function():
            return "ok"

        # First call uses the token
        start = time.monotonic()
        await my_function()
        first_elapsed = time.monotonic() - start

        # Second call must wait for refill (~0.5s for 1 token at 2 tokens/sec)
        start = time.monotonic()
        await my_function()
        second_elapsed = time.monotonic() - start

        assert first_elapsed < 0.1  # First is immediate
        assert second_elapsed >= 0.3  # Second waits for token (~0.5s)


# =============================================================================
# Test Environment Variable Override
# =============================================================================


@pytest.mark.xdist_group(name="token_bucket")
class TestTokenBucketEnvOverride:
    """Test environment variable overrides for token bucket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        reset_all_token_buckets()

    @pytest.mark.unit
    def test_env_override_rate_limit(self):
        """RATE_LIMIT_<PROVIDER>_RPM should override default."""
        import os

        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        reset_all_token_buckets()  # Clear cache before env change

        with patch.dict(os.environ, {"RATE_LIMIT_ANTHROPIC_RPM": "120"}):
            from mcp_server_langgraph.resilience.rate_limit import get_provider_token_bucket

            bucket = get_provider_token_bucket("anthropic")
            # 120 RPM = 2 requests/sec
            assert bucket.refill_rate == pytest.approx(2.0, rel=0.1)
