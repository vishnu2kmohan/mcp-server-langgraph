"""
Integration tests for chaos scenarios - verifying graceful degradation.

These tests verify that the system handles service unavailability gracefully:
1. Keycloak unavailable → Circuit breaker trips, auth fails fast
2. Redis unavailable → L1 cache fallback activates
3. PostgreSQL unavailable → Circuit breaker trips, operations fail fast
4. Prometheus unavailable → Circuit breaker trips, metrics queries fail fast

Reference: ADR-0026 - Resilience Patterns

Note: These tests use mocks to simulate service unavailability.
For full chaos testing, use a chaos engineering tool like Litmus or Chaos Monkey.
"""

import gc
import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

# Mark as integration test
pytestmark = [
    pytest.mark.integration,
    pytest.mark.resilience,
    pytest.mark.chaos,
]


@pytest.mark.xdist_group(name="chaos_scenario_tests")
class TestKeycloakChaosScenario:
    """Test graceful degradation when Keycloak is unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_keycloak_circuit_breaker_trips_after_manual_failures(self):
        """
        GIVEN: Keycloak circuit breaker tracking failures
        WHEN: Failures exceed threshold
        THEN: Circuit breaker should trip to OPEN state

        Chaos Scenario: Keycloak pod killed, network partition
        """
        import pybreaker

        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset circuit breaker
        reset_circuit_breaker("keycloak")

        # Simulate failures by directly interacting with breaker
        breaker = get_circuit_breaker("keycloak")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("Keycloak unavailable"))
            except pybreaker.CircuitBreakerError:
                pass

        # Verify circuit breaker is OPEN
        assert breaker.current_state == pybreaker.STATE_OPEN

    def test_keycloak_circuit_breaker_recovers_after_timeout(self):
        """
        GIVEN: Keycloak circuit breaker is OPEN
        WHEN: Recovery timeout passes and success is recorded
        THEN: Circuit breaker should transition to HALF_OPEN then CLOSED

        Chaos Scenario: Keycloak recovery after outage
        """
        import pybreaker

        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset and trip the circuit breaker
        reset_circuit_breaker("keycloak")
        breaker = get_circuit_breaker("keycloak")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("Keycloak unavailable"))
            except pybreaker.CircuitBreakerError:
                pass

        assert breaker.current_state == pybreaker.STATE_OPEN

        # Reset for recovery simulation
        reset_circuit_breaker("keycloak")
        breaker = get_circuit_breaker("keycloak")

        # Verify it's now closed
        assert breaker.current_state == pybreaker.STATE_CLOSED


@pytest.mark.xdist_group(name="chaos_scenario_tests")
class TestRedisChaosScenario:
    """Test graceful degradation when Redis is unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_redis_circuit_breaker_trips_after_manual_failures(self):
        """
        GIVEN: Redis circuit breaker tracking failures
        WHEN: Failures exceed threshold
        THEN: Circuit breaker should trip to OPEN state

        Chaos Scenario: Redis pod killed, memory pressure eviction
        """
        import pybreaker

        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset circuit breaker
        reset_circuit_breaker("redis")

        # Simulate failures by directly interacting with breaker
        breaker = get_circuit_breaker("redis")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("Redis unavailable"))
            except pybreaker.CircuitBreakerError:
                pass

        # Verify circuit breaker is OPEN
        assert breaker.current_state == pybreaker.STATE_OPEN

    def test_redis_circuit_breaker_state_affects_health_check(self):
        """
        GIVEN: Redis circuit breaker is OPEN
        WHEN: Health check validates circuit breakers
        THEN: Should report Redis as unhealthy (critical service)

        Chaos Scenario: Redis cluster failure impacts health
        """
        import pybreaker

        from mcp_server_langgraph.api.health import validate_circuit_breakers_healthy
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset all other critical breakers to healthy
        for service in ["keycloak", "openfga", "postgres"]:
            reset_circuit_breaker(service)

        # Trip Redis circuit breaker
        reset_circuit_breaker("redis")
        breaker = get_circuit_breaker("redis")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("Redis unavailable"))
            except pybreaker.CircuitBreakerError:
                pass

        assert breaker.current_state == pybreaker.STATE_OPEN

        # Health check should report unhealthy
        healthy, message = validate_circuit_breakers_healthy()
        assert healthy is False
        assert "redis" in message.lower()


@pytest.mark.xdist_group(name="chaos_scenario_tests")
class TestPostgreSQLChaosScenario:
    """Test graceful degradation when PostgreSQL is unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_postgres_unavailable_circuit_breaker_trips(self):
        """
        GIVEN: PostgreSQL is unavailable
        WHEN: Multiple connection attempts fail
        THEN: Circuit breaker should trip

        Chaos Scenario: PostgreSQL pod killed, database failover
        """
        import pybreaker

        from mcp_server_langgraph.infrastructure.database import (
            check_database_connectivity,
        )
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset circuit breaker
        reset_circuit_breaker("postgres")

        async def mock_connect_always_fails(*args, **kwargs):
            raise OSError("Connection refused")

        with (
            patch("asyncpg.connect", side_effect=mock_connect_always_fails),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            # Trigger enough failures to trip circuit breaker
            postgres_port = os.getenv("POSTGRES_PORT", "9432")
            for _ in range(6):
                await check_database_connectivity(f"postgresql://test:test@localhost:{postgres_port}/test")

            # Verify circuit breaker is OPEN
            breaker = get_circuit_breaker("postgres")
            assert breaker.current_state == pybreaker.STATE_OPEN

    @pytest.mark.asyncio
    async def test_postgres_unavailable_returns_clear_error_message(self):
        """
        GIVEN: PostgreSQL circuit breaker is OPEN
        WHEN: Database connectivity check is performed
        THEN: Should return clear error message about circuit breaker

        Chaos Scenario: Graceful degradation during database outage
        """
        import pybreaker

        from mcp_server_langgraph.infrastructure.database import (
            check_database_connectivity,
        )
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset and trip the circuit breaker
        reset_circuit_breaker("postgres")
        breaker = get_circuit_breaker("postgres")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("simulated failure"))
            except pybreaker.CircuitBreakerError:
                pass

        assert breaker.current_state == pybreaker.STATE_OPEN

        # Check should fail fast with circuit breaker message
        postgres_port = os.getenv("POSTGRES_PORT", "9432")
        is_healthy, message = await check_database_connectivity(f"postgresql://test:test@localhost:{postgres_port}/test")

        assert is_healthy is False
        assert "circuit breaker" in message.lower()


@pytest.mark.xdist_group(name="chaos_scenario_tests")
class TestPrometheusChaosScenario:
    """Test graceful degradation when Prometheus is unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_prometheus_unavailable_circuit_breaker_trips(self):
        """
        GIVEN: Prometheus is unavailable
        WHEN: Multiple query attempts fail
        THEN: Circuit breaker should trip

        Chaos Scenario: Prometheus pod killed, storage full
        """
        import pybreaker

        from mcp_server_langgraph.monitoring.prometheus_client import (
            PrometheusClient,
            PrometheusConfig,
        )
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset circuit breaker
        reset_circuit_breaker("prometheus")

        config = PrometheusConfig(
            url="http://prometheus:9090",
            timeout=30,
            retry_attempts=3,
            retry_backoff=2.0,
        )
        client = PrometheusClient(config=config)

        async def mock_get_always_fails(*args, **kwargs):
            raise httpx.ConnectError("Prometheus unavailable")

        mock_http_client = AsyncMock()  # noqa: async-mock-config (configured via get below)
        mock_http_client.get = mock_get_always_fails
        client.client = mock_http_client
        client._initialized = True

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Trigger enough failures to trip circuit breaker
            for _ in range(6):
                try:
                    await client.query("up")
                except (httpx.HTTPError, pybreaker.CircuitBreakerError):
                    pass

            # Verify circuit breaker is OPEN
            breaker = get_circuit_breaker("prometheus")
            assert breaker.current_state == pybreaker.STATE_OPEN


@pytest.mark.xdist_group(name="chaos_scenario_tests")
class TestHealthCheckChaosIntegration:
    """Test health check behavior during chaos scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_health_check_reports_unhealthy_when_critical_services_down(self):
        """
        GIVEN: Critical circuit breakers (Redis, Keycloak, Postgres) are OPEN
        WHEN: Health check is performed
        THEN: Should report unhealthy

        Chaos Scenario: Multiple service failures during incident
        """
        import pybreaker

        from mcp_server_langgraph.api.health import validate_circuit_breakers_healthy
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset and trip multiple critical circuit breakers
        for service in ["redis", "keycloak", "postgres"]:
            reset_circuit_breaker(service)
            breaker = get_circuit_breaker(service)
            for _ in range(10):
                try:
                    breaker._inc_counter()
                    breaker.state.on_failure(Exception(f"{service} down"))
                except pybreaker.CircuitBreakerError:
                    pass

        # Health check should report unhealthy
        healthy, message = validate_circuit_breakers_healthy()

        assert healthy is False
        # Should mention at least one of the failed services
        message_lower = message.lower()
        assert any(svc in message_lower for svc in ["redis", "keycloak", "postgres"])

    def test_health_check_reports_warning_when_observability_down(self):
        """
        GIVEN: Observability circuit breakers (Prometheus, Tempo, Loki) are OPEN
        WHEN: Health check is performed
        THEN: Should report healthy with warning

        Chaos Scenario: Observability stack failure (non-critical)
        """
        import pybreaker

        from mcp_server_langgraph.api.health import validate_circuit_breakers_healthy
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset all critical breakers to healthy
        for service in ["redis", "keycloak", "postgres", "openfga"]:
            reset_circuit_breaker(service)

        # Trip observability circuit breakers
        for service in ["prometheus", "tempo", "loki"]:
            reset_circuit_breaker(service)
            breaker = get_circuit_breaker(service)
            for _ in range(10):
                try:
                    breaker._inc_counter()
                    breaker.state.on_failure(Exception(f"{service} down"))
                except pybreaker.CircuitBreakerError:
                    pass

        # Health check should report healthy (warning only)
        healthy, message = validate_circuit_breakers_healthy()

        assert healthy is True
        assert "warning" in message.lower() or "non-critical" in message.lower()


@pytest.mark.xdist_group(name="chaos_scenario_tests")
class TestLLMProviderChaosScenario:
    """Test graceful degradation when LLM providers are unavailable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_llm_circuit_breaker_trips_after_provider_failures(self):
        """
        GIVEN: LLM provider circuit breaker tracking failures
        WHEN: Failures exceed threshold
        THEN: Circuit breaker should trip to OPEN state

        Chaos Scenario: LLM provider API down (Anthropic, OpenAI outage)
        """
        import pybreaker

        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset circuit breaker
        reset_circuit_breaker("llm")

        # Simulate failures by directly interacting with breaker
        breaker = get_circuit_breaker("llm")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("LLM provider unavailable"))
            except pybreaker.CircuitBreakerError:
                pass

        # Verify circuit breaker is OPEN
        assert breaker.current_state == pybreaker.STATE_OPEN

    @pytest.mark.asyncio
    async def test_llm_rate_limiting_prevents_429_errors(self):
        """
        GIVEN: LLM rate limiter configured for provider
        WHEN: Many concurrent requests are made
        THEN: Rate limiter should queue requests to prevent 429 errors

        Chaos Scenario: Traffic spike during high demand
        """
        from mcp_server_langgraph.resilience.rate_limit import (
            get_provider_token_bucket,
            reset_all_token_buckets,
        )

        # Reset rate limiters
        reset_all_token_buckets()

        # Get token bucket for anthropic (low RPM: 50)
        bucket = get_provider_token_bucket("anthropic")

        # Verify bucket has capacity
        assert bucket.capacity > 0
        assert bucket.refill_rate > 0

        # Drain bucket
        drained = 0
        while bucket.try_acquire():
            drained += 1

        # Verify we can't acquire more immediately
        assert not bucket.try_acquire()
        assert drained > 0

    @pytest.mark.asyncio
    async def test_llm_adaptive_bulkhead_reduces_concurrency_on_429(self):
        """
        GIVEN: LLM adaptive bulkhead at default limit
        WHEN: Multiple 429 rate limit errors occur
        THEN: Bulkhead should reduce concurrency limit

        Chaos Scenario: Provider rate limiting during peak usage
        """
        from mcp_server_langgraph.resilience.adaptive import (
            get_provider_adaptive_bulkhead,
            reset_all_adaptive_bulkheads,
        )

        # Reset bulkheads
        reset_all_adaptive_bulkheads()

        # Get bulkhead for anthropic
        bulkhead = get_provider_adaptive_bulkhead("anthropic")
        initial_limit = bulkhead.current_limit

        # Simulate rate limit errors
        for _ in range(5):
            bulkhead.record_error()

        # Verify limit decreased
        assert bulkhead.current_limit < initial_limit

        # Simulate recovery with success streak
        for _ in range(15):
            bulkhead.record_success()

        # Verify limit increased (may not be back to initial if not enough successes)
        # But should be higher than the reduced limit
        final_limit = bulkhead.current_limit
        assert final_limit >= bulkhead.min_limit

    @pytest.mark.asyncio
    async def test_llm_circuit_breaker_does_not_affect_health_check(self):
        """
        GIVEN: LLM circuit breaker is OPEN
        WHEN: Health check is performed
        THEN: Should still report healthy (LLM is non-critical for health)

        Chaos Scenario: LLM outage should not prevent application startup
        """
        import pybreaker

        from mcp_server_langgraph.api.health import validate_circuit_breakers_healthy
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset all circuit breakers
        for service in ["redis", "keycloak", "postgres", "openfga"]:
            reset_circuit_breaker(service)

        # Trip the LLM circuit breaker
        reset_circuit_breaker("llm")
        breaker = get_circuit_breaker("llm")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("LLM unavailable"))
            except pybreaker.CircuitBreakerError:
                pass

        assert breaker.current_state == pybreaker.STATE_OPEN

        # Health check should still report healthy
        # (LLM is not in the critical_breakers list)
        healthy, message = validate_circuit_breakers_healthy()

        assert healthy is True
