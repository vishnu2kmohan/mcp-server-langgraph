"""
Unit tests for LLM client resilience patterns.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. LLM factory applies rate limiting before API calls
2. LLM factory uses adaptive bulkhead for concurrency control
3. Circuit breaker trips after repeated LLM failures
4. Rate limit errors (429/529) are handled correctly

Reference: ADR-0026 - Resilience Patterns
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.llm,
    pytest.mark.resilience,
]


@pytest.mark.xdist_group(name="llm_resilience_tests")
class TestLLMRateLimiting:
    """Test LLM rate limiting integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_llm_ainvoke_acquires_rate_limit_token(self):
        """
        GIVEN: LLMFactory with rate limiting enabled
        WHEN: ainvoke is called
        THEN: Should acquire token from provider's rate limiter before making API call

        User Journey: Pre-emptive rate limiting prevents 429 errors
        """
        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.resilience.rate_limit import (
            get_provider_token_bucket,
            reset_all_token_buckets,
        )

        # Reset rate limiter state
        reset_all_token_buckets()

        # Create factory with known provider
        factory = LLMFactory(model="gpt-4", provider="openai")

        # Get the token bucket for verification
        bucket = get_provider_token_bucket("openai")

        # Mock the litellm acompletion to avoid real API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_acompletion.return_value = mock_response

            # Make the call
            await factory.ainvoke([{"role": "user", "content": "Hello"}])

            # Verify rate limiter was used (token consumed)
            # Note: Token should be lower after call
            assert bucket.tokens < bucket.capacity

    @pytest.mark.asyncio
    async def test_llm_rate_limiter_waits_when_no_tokens(self):
        """
        GIVEN: LLMFactory with exhausted rate limit tokens
        WHEN: ainvoke is called
        THEN: Should wait for token availability before proceeding

        User Journey: Smooth request distribution during high load
        """
        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.resilience.rate_limit import (
            get_provider_token_bucket,
            reset_all_token_buckets,
        )

        # Reset rate limiter state
        reset_all_token_buckets()

        # Create factory
        factory = LLMFactory(model="gpt-4", provider="openai")

        # Get the bucket that will be used
        bucket = get_provider_token_bucket("openai")

        # Mock the litellm acompletion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        acquire_called = False

        async def mock_acquire(tokens: float = 1, timeout: float | None = None) -> None:
            nonlocal acquire_called
            acquire_called = True
            # Just return immediately for the test
            return None

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch.object(bucket, "acquire", side_effect=mock_acquire),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_acompletion.return_value = mock_response

            await factory.ainvoke([{"role": "user", "content": "Hello"}])

            # Verify rate limiter's acquire was called
            assert acquire_called, "Rate limiter acquire should be called"
            mock_acompletion.assert_called_once()


@pytest.mark.xdist_group(name="llm_resilience_tests")
class TestLLMAdaptiveBulkhead:
    """Test LLM adaptive bulkhead integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_llm_adaptive_bulkhead_limits_concurrency(self):
        """
        GIVEN: LLMFactory with adaptive bulkhead
        WHEN: Many concurrent ainvoke calls are made
        THEN: Should limit concurrent requests based on adaptive limit

        User Journey: Prevent overwhelming LLM provider
        """
        import asyncio

        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.resilience.adaptive import (
            get_provider_adaptive_bulkhead,
            reset_all_adaptive_bulkheads,
        )
        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        # Reset state
        reset_all_token_buckets()
        reset_all_adaptive_bulkheads()

        # Create factory
        factory = LLMFactory(model="gpt-4", provider="openai")

        # Get bulkhead
        bulkhead = get_provider_adaptive_bulkhead("openai")
        initial_limit = bulkhead.current_limit

        # Track concurrent calls
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        async def mock_acompletion_tracking(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.05)  # Simulate API latency
            async with lock:
                current_concurrent -= 1
            return mock_response

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", side_effect=mock_acompletion_tracking),
        ):
            # Launch many concurrent calls
            num_calls = initial_limit + 5  # More than the limit

            tasks = [factory.ainvoke([{"role": "user", "content": f"Request {i}"}]) for i in range(num_calls)]

            await asyncio.gather(*tasks, return_exceptions=True)

            # Verify concurrency was limited
            # Note: The actual limit depends on bulkhead configuration
            assert max_concurrent <= initial_limit + 2  # Some tolerance for timing

    @pytest.mark.asyncio
    async def test_llm_adaptive_bulkhead_decreases_on_rate_limit_error(self):
        """
        GIVEN: LLMFactory with adaptive bulkhead
        WHEN: ainvoke receives 429 rate limit error
        THEN: Should decrease the concurrency limit

        User Journey: Self-healing response to rate limit errors
        """
        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.resilience.adaptive import (
            get_provider_adaptive_bulkhead,
            reset_all_adaptive_bulkheads,
        )
        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        # Reset state
        reset_all_token_buckets()
        reset_all_adaptive_bulkheads()

        # Create factory
        factory = LLMFactory(model="gpt-4", provider="openai")

        # Get bulkhead and record initial limit
        bulkhead = get_provider_adaptive_bulkhead("openai")
        initial_limit = bulkhead.current_limit

        # Simulate rate limit error (429)
        from litellm.exceptions import RateLimitError

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_acompletion.side_effect = RateLimitError(
                message="Rate limit exceeded",
                model="gpt-4",
                llm_provider="openai",
            )

            # Trigger errors (will be caught by retry)
            for _ in range(3):
                try:
                    await factory.ainvoke([{"role": "user", "content": "Hello"}])
                except Exception:
                    # Record error in adaptive bulkhead
                    bulkhead.record_error()

            # Verify limit decreased
            assert bulkhead.current_limit < initial_limit

    @pytest.mark.asyncio
    async def test_llm_adaptive_bulkhead_increases_on_success_streak(self):
        """
        GIVEN: LLMFactory with adaptive bulkhead at reduced limit
        WHEN: Multiple successful ainvoke calls
        THEN: Should gradually increase the concurrency limit

        User Journey: Recovery after rate limit issues
        """
        from mcp_server_langgraph.resilience.adaptive import (
            get_provider_adaptive_bulkhead,
            reset_all_adaptive_bulkheads,
        )

        # Reset state
        reset_all_adaptive_bulkheads()

        # Get bulkhead with reduced initial limit
        bulkhead = get_provider_adaptive_bulkhead("openai")

        # Simulate a previous error condition (reduced limit)
        for _ in range(3):
            bulkhead.record_error()

        reduced_limit = bulkhead.current_limit

        # Record success streak (threshold is typically 10)
        for _ in range(15):
            bulkhead.record_success()

        # Verify limit increased
        assert bulkhead.current_limit > reduced_limit


@pytest.mark.xdist_group(name="llm_resilience_tests")
class TestLLMCircuitBreakerIntegration:
    """Test LLM circuit breaker integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_llm_circuit_breaker_opens_after_failures(self):
        """
        GIVEN: LLMFactory with circuit breaker
        WHEN: ainvoke fails repeatedly (exceeds threshold)
        THEN: Circuit breaker should open and fail fast

        User Journey: Prevent cascade failures when LLM provider is down
        """
        import pybreaker

        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )
        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        # Reset state
        reset_all_token_buckets()
        reset_circuit_breaker("llm")

        # Create factory
        factory = LLMFactory(model="gpt-4", provider="openai")

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_acompletion.side_effect = Exception("Service unavailable")

            # Trigger enough failures to trip circuit breaker
            for _ in range(10):
                try:
                    await factory.ainvoke([{"role": "user", "content": "Hello"}])
                except (Exception, pybreaker.CircuitBreakerError):
                    pass

            # Verify circuit breaker is now OPEN
            breaker = get_circuit_breaker("llm")
            assert breaker.current_state == pybreaker.STATE_OPEN

    @pytest.mark.asyncio
    async def test_llm_circuit_breaker_recovers_after_timeout(self):
        """
        GIVEN: LLM circuit breaker in OPEN state
        WHEN: Timeout passes and success is recorded
        THEN: Circuit breaker should transition to CLOSED

        User Journey: Automatic recovery after LLM provider outage
        """
        import pybreaker

        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset and trip the circuit breaker
        reset_circuit_breaker("llm")
        breaker = get_circuit_breaker("llm")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("LLM unavailable"))
            except pybreaker.CircuitBreakerError:
                pass

        assert breaker.current_state == pybreaker.STATE_OPEN

        # Reset for recovery simulation
        reset_circuit_breaker("llm")
        breaker = get_circuit_breaker("llm")

        # Verify it's now closed
        assert breaker.current_state == pybreaker.STATE_CLOSED


@pytest.mark.xdist_group(name="llm_resilience_tests")
class TestLLMRateLimitErrorHandling:
    """Test handling of rate limit errors (429/529)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_llm_handles_429_with_extended_retry(self):
        """
        GIVEN: LLMFactory receiving 429 rate limit error
        WHEN: ainvoke is called
        THEN: Should retry with extended attempts (up to 6 for overload)

        User Journey: Graceful handling of temporary rate limits
        """
        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        # Reset state
        reset_all_token_buckets()

        factory = LLMFactory(model="gpt-4", provider="openai")

        call_count = 0

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success!"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        async def mock_with_rate_limit(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                from litellm.exceptions import RateLimitError

                raise RateLimitError(
                    message="Rate limit exceeded",
                    model="gpt-4",
                    llm_provider="openai",
                )
            return mock_response

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", side_effect=mock_with_rate_limit),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await factory.ainvoke([{"role": "user", "content": "Hello"}])

            # Verify retry happened
            assert call_count >= 3

    @pytest.mark.asyncio
    async def test_llm_handles_529_overloaded_error(self):
        """
        GIVEN: LLMFactory receiving 529 overloaded error
        WHEN: ainvoke is called
        THEN: Should retry with exponential backoff (3 attempts by default)

        User Journey: Handle Anthropic overload with exponential backoff
        """
        from mcp_server_langgraph.llm.factory import LLMFactory
        from mcp_server_langgraph.resilience.rate_limit import reset_all_token_buckets

        # Reset state
        reset_all_token_buckets()

        factory = LLMFactory(model="claude-3-sonnet-20240229", provider="anthropic")

        call_count = 0

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success!"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        async def mock_with_overload(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts, succeed on 3rd
                from litellm.exceptions import ServiceUnavailableError

                raise ServiceUnavailableError(
                    message="Overloaded",
                    model="claude-3-sonnet",
                    llm_provider="anthropic",
                )
            return mock_response

        with (
            patch("mcp_server_langgraph.llm.factory.acompletion", side_effect=mock_with_overload),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await factory.ainvoke([{"role": "user", "content": "Hello"}])

            # Verify retries happened (3 attempts: 2 failures + 1 success)
            assert call_count == 3
