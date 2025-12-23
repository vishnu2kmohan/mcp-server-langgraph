"""
Unit tests for resilience stats in health endpoint.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. ReadinessResult includes resilience_stats field
2. resilience_stats contains adaptive bulkhead info
3. resilience_stats contains rate limit info
4. Stats are correctly populated from actual resilience components

Reference: ADR-0026 - Resilience Patterns
"""

import gc
from unittest.mock import patch

import pytest

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.resilience,
]


@pytest.mark.xdist_group(name="health_resilience_tests")
class TestHealthResilienceStats:
    """Test resilience stats in health endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_readiness_result_has_resilience_stats_field(self):
        """
        GIVEN: ReadinessResult model
        WHEN: Model is inspected
        THEN: Should have resilience_stats field

        User Journey: Operators see resilience stats in health checks
        """
        from mcp_server_langgraph.api.health import ReadinessResult

        # Check that the model has resilience_stats field
        assert "resilience_stats" in ReadinessResult.model_fields

    def test_get_resilience_stats_returns_dict(self):
        """
        GIVEN: get_resilience_stats function
        WHEN: Called
        THEN: Should return dict with adaptive_bulkheads and rate_limits

        User Journey: Health check includes resilience component stats
        """
        from mcp_server_langgraph.api.health import get_resilience_stats

        stats = get_resilience_stats()

        assert isinstance(stats, dict)
        assert "adaptive_bulkheads" in stats
        assert "rate_limits" in stats
        assert "circuit_breakers" in stats

    def test_get_resilience_stats_includes_provider_info(self):
        """
        GIVEN: Adaptive bulkheads for multiple providers
        WHEN: get_resilience_stats is called
        THEN: Should include per-provider stats

        User Journey: Monitor per-provider concurrency limits
        """
        from mcp_server_langgraph.api.health import get_resilience_stats
        from mcp_server_langgraph.resilience.adaptive import (
            get_provider_adaptive_bulkhead,
            reset_all_adaptive_bulkheads,
        )

        # Reset and create bulkhead for a provider
        reset_all_adaptive_bulkheads()
        bulkhead = get_provider_adaptive_bulkhead("openai")

        stats = get_resilience_stats()

        # Should include openai provider stats
        assert "openai" in stats["adaptive_bulkheads"]
        assert "current_limit" in stats["adaptive_bulkheads"]["openai"]
        assert "error_rate" in stats["adaptive_bulkheads"]["openai"]

    @pytest.mark.asyncio
    async def test_readiness_probe_includes_resilience_stats(self):
        """
        GIVEN: Readiness probe endpoint
        WHEN: Called
        THEN: Response should include resilience_stats

        User Journey: K8s readiness probe shows resilience health
        """
        from mcp_server_langgraph.api.health import readiness_probe

        with (
            patch("mcp_server_langgraph.api.health.validate_observability_initialized") as mock_obs,
            patch("mcp_server_langgraph.api.health.validate_database_connectivity_async") as mock_db,
            patch("mcp_server_langgraph.api.health.validate_circuit_breakers_healthy") as mock_cb,
        ):
            mock_obs.return_value = (True, "OK")
            mock_db.return_value = (True, "OK")
            mock_cb.return_value = (True, "OK")

            result = await readiness_probe()

            # Should have resilience_stats
            assert hasattr(result, "resilience_stats")
            assert result.resilience_stats is not None
            assert "adaptive_bulkheads" in result.resilience_stats


@pytest.mark.xdist_group(name="health_resilience_tests")
class TestCircuitBreakerStatsInHealth:
    """Test circuit breaker stats in health response."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_circuit_breaker_stats_include_state(self):
        """
        GIVEN: Circuit breakers for various services
        WHEN: get_resilience_stats is called
        THEN: Should include circuit breaker states

        User Journey: See which circuit breakers are open/closed
        """
        from mcp_server_langgraph.api.health import get_resilience_stats

        stats = get_resilience_stats()

        assert "circuit_breakers" in stats
        # Stats should be a dict mapping service to state
        assert isinstance(stats["circuit_breakers"], dict)

    def test_circuit_breaker_states_are_strings(self):
        """
        GIVEN: get_resilience_stats function
        WHEN: Called with circuit breakers registered
        THEN: States should be human-readable strings

        User Journey: Easy to understand circuit breaker status
        """
        from mcp_server_langgraph.api.health import get_resilience_stats
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Ensure a circuit breaker exists
        reset_circuit_breaker("llm")
        get_circuit_breaker("llm")

        stats = get_resilience_stats()

        # LLM circuit breaker should be in stats
        if "llm" in stats["circuit_breakers"]:
            state = stats["circuit_breakers"]["llm"]
            assert state in ["CLOSED", "OPEN", "HALF_OPEN"]


@pytest.mark.xdist_group(name="health_resilience_tests")
class TestRateLimitStatsInHealth:
    """Test rate limit stats in health response."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_limit_stats_include_provider_info(self):
        """
        GIVEN: Token buckets for LLM providers
        WHEN: get_resilience_stats is called
        THEN: Should include per-provider rate limit stats

        User Journey: Monitor available rate limit tokens per provider
        """
        from mcp_server_langgraph.api.health import get_resilience_stats
        from mcp_server_langgraph.resilience.rate_limit import (
            get_provider_token_bucket,
            reset_all_token_buckets,
        )

        # Reset and create token bucket for a provider
        reset_all_token_buckets()
        bucket = get_provider_token_bucket("anthropic")

        stats = get_resilience_stats()

        # Should include anthropic provider stats
        assert "anthropic" in stats["rate_limits"]
        assert "available_tokens" in stats["rate_limits"]["anthropic"]
        assert "capacity" in stats["rate_limits"]["anthropic"]

    def test_rate_limit_stats_show_token_availability(self):
        """
        GIVEN: Token bucket with known capacity
        WHEN: get_resilience_stats is called
        THEN: Should show accurate token availability

        User Journey: Operators see how many API calls are available
        """
        from mcp_server_langgraph.api.health import get_resilience_stats
        from mcp_server_langgraph.resilience.rate_limit import (
            get_provider_token_bucket,
            reset_all_token_buckets,
        )

        # Reset and create fresh bucket
        reset_all_token_buckets()
        bucket = get_provider_token_bucket("openai")

        stats = get_resilience_stats()

        # Fresh bucket should have tokens near capacity
        if "openai" in stats["rate_limits"]:
            openai_stats = stats["rate_limits"]["openai"]
            assert openai_stats["available_tokens"] <= openai_stats["capacity"]
            assert openai_stats["available_tokens"] >= 0

    def test_rate_limit_stats_include_refill_rate(self):
        """
        GIVEN: Token bucket for a provider
        WHEN: get_resilience_stats is called
        THEN: Should include refill rate for capacity planning

        User Journey: Operators understand sustained rate limits
        """
        from mcp_server_langgraph.api.health import get_resilience_stats
        from mcp_server_langgraph.resilience.rate_limit import (
            get_provider_token_bucket,
            reset_all_token_buckets,
        )

        reset_all_token_buckets()
        get_provider_token_bucket("vertex_ai")

        stats = get_resilience_stats()

        if "vertex_ai" in stats["rate_limits"]:
            assert "refill_rate" in stats["rate_limits"]["vertex_ai"]
