"""
Unit tests for observability client resilience patterns.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. Prometheus client uses exponential backoff (2.0x, not 1.0x)
2. Tempo client has circuit breaker and retry logic
3. Loki client has circuit breaker and retry logic
4. Health checks integrate circuit breaker state

Reference: ADR-0026 - Resilience Patterns
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
    pytest.mark.resilience,
]


@pytest.mark.xdist_group(name="observability_resilience_tests")
class TestPrometheusClientRetryLogic:
    """Test Prometheus client retry logic with exponential backoff."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_retries_with_exponential_backoff(self):
        """
        GIVEN: PrometheusClient configured with retry
        WHEN: Query fails with connection error, then succeeds
        THEN: Should retry with exponential backoff (2.0x multiplier)

        User Journey: Recover from Prometheus blips with proper backoff
        """
        from mcp_server_langgraph.monitoring.prometheus_client import (
            PrometheusClient,
            PrometheusConfig,
        )
        from mcp_server_langgraph.resilience.circuit_breaker import (
            reset_circuit_breaker,
        )

        # Reset circuit breaker state before test
        reset_circuit_breaker("prometheus")

        config = PrometheusConfig(
            url="http://prometheus:9090",
            timeout=30,
            retry_attempts=3,
            retry_backoff=2.0,  # 2.0x exponential backoff
        )
        client = PrometheusClient(config=config)

        call_count = 0
        delays_used = []

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": [{"metric": {}, "value": [1234567890, "42"]}]},
        }

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Prometheus unavailable")
            return mock_response

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Track actual delays used
            async def track_delay(delay):
                delays_used.append(delay)

            mock_sleep.side_effect = track_delay

            mock_http_client = AsyncMock()
            mock_http_client.get = mock_get
            client.client = mock_http_client
            client._initialized = True

            # Should retry and succeed
            results = await client.query("up")

            # Should have made 3 attempts
            assert call_count == 3

            # Should have slept between retries with exponential backoff
            # Base delay 1.0s, multiplier 2.0x: 1.0s, 2.0s
            assert len(delays_used) == 2
            assert delays_used[0] == pytest.approx(1.0, rel=0.1)  # First retry: 1.0s
            assert delays_used[1] == pytest.approx(2.0, rel=0.1)  # Second retry: 2.0s

    @pytest.mark.asyncio
    async def test_query_circuit_breaker_trips_after_failures(self):
        """
        GIVEN: PrometheusClient with circuit breaker
        WHEN: Query fails repeatedly (exceeds threshold)
        THEN: Circuit breaker should open and fail fast

        User Journey: Prevent cascade failures when Prometheus is down
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

        # Reset circuit breaker state before test
        reset_circuit_breaker("prometheus")

        config = PrometheusConfig(
            url="http://prometheus:9090",
            timeout=30,
            retry_attempts=3,
        )
        client = PrometheusClient(config=config)

        async def mock_get_always_fails(*args, **kwargs):
            raise httpx.ConnectError("Prometheus down")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            mock_http_client = AsyncMock()
            mock_http_client.get = mock_get_always_fails
            client.client = mock_http_client
            client._initialized = True

            # Trigger enough failures to open the circuit breaker
            for _ in range(6):
                try:
                    await client.query("up")
                except (httpx.ConnectError, pybreaker.CircuitBreakerError):
                    pass

            # Verify circuit breaker is now OPEN
            breaker = get_circuit_breaker("prometheus")
            assert breaker.current_state == pybreaker.STATE_OPEN


@pytest.mark.xdist_group(name="observability_resilience_tests")
class TestTempoClientResilience:
    """Test Tempo client resilience patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_trace_retries_on_connection_error(self):
        """
        GIVEN: TempoClient configured with retry
        WHEN: get_trace fails with connection error, then succeeds
        THEN: Should retry and return trace

        User Journey: Recover from Tempo blips
        """
        from mcp_server_langgraph.monitoring.tempo_client import (
            TempoClient,
            TempoConfig,
        )
        from mcp_server_langgraph.resilience.circuit_breaker import (
            reset_circuit_breaker,
        )

        # Reset circuit breaker state before test
        reset_circuit_breaker("tempo")

        config = TempoConfig(
            url="http://tempo:3200",
            timeout=30,
            retry_attempts=3,
            retry_backoff=2.0,
        )
        client = TempoClient(config=config)

        call_count = 0

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "batches": [
                {
                    "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "test"}}]},
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "spanId": "abc123",
                                    "traceId": "trace123",
                                    "name": "test-span",
                                    "startTimeUnixNano": 1234567890000000000,
                                    "endTimeUnixNano": 1234567891000000000,
                                }
                            ]
                        }
                    ],
                }
            ]
        }

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Tempo unavailable")
            return mock_response

        with patch("asyncio.sleep", new_callable=AsyncMock):
            mock_http_client = AsyncMock()
            mock_http_client.get = mock_get
            client.client = mock_http_client
            client._initialized = True

            # Should retry and succeed
            trace = await client.get_trace("trace123")

            # Should have made 2 attempts
            assert call_count == 2

            # Should return trace
            assert trace is not None
            assert trace.trace_id == "trace123"

    @pytest.mark.asyncio
    async def test_search_circuit_breaker_integration(self):
        """
        GIVEN: TempoClient with circuit breaker
        WHEN: Search fails repeatedly
        THEN: Circuit breaker should open

        User Journey: Prevent cascade failures when Tempo is down
        """
        import pybreaker

        from mcp_server_langgraph.monitoring.tempo_client import (
            TempoClient,
            TempoConfig,
        )
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset circuit breaker state before test
        reset_circuit_breaker("tempo")

        config = TempoConfig(url="http://tempo:3200", timeout=30, retry_attempts=3)
        client = TempoClient(config=config)

        async def mock_get_always_fails(*args, **kwargs):
            raise httpx.ConnectError("Tempo down")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            mock_http_client = AsyncMock()
            mock_http_client.get = mock_get_always_fails
            client.client = mock_http_client
            client._initialized = True

            # Trigger enough failures to open circuit breaker
            for _ in range(6):
                try:
                    await client.search(query='{ resource.service.name = "test" }')
                except (httpx.HTTPError, pybreaker.CircuitBreakerError):
                    pass

            # Verify circuit breaker is now OPEN
            breaker = get_circuit_breaker("tempo")
            assert breaker.current_state == pybreaker.STATE_OPEN


@pytest.mark.xdist_group(name="observability_resilience_tests")
class TestLokiClientResilience:
    """Test Loki client resilience patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_logs_retries_on_connection_error(self):
        """
        GIVEN: LokiLoggingClient configured with retry
        WHEN: search_logs fails with connection error, then succeeds
        THEN: Should retry and return results

        User Journey: Recover from Loki blips
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )
        from mcp_server_langgraph.resilience.circuit_breaker import (
            reset_circuit_breaker,
        )

        # Reset circuit breaker state before test
        reset_circuit_breaker("loki")

        client = LokiLoggingClient()

        call_count = 0

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []},
        }

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Loki unavailable")
            return mock_response

        with patch("asyncio.sleep", new_callable=AsyncMock):
            mock_http_client = AsyncMock()
            mock_http_client.get = mock_get
            client._client = mock_http_client
            client._initialized = True

            # Should retry and succeed
            result = await client.search_logs(query="error")

            # Should have made 2 attempts
            assert call_count == 2

            # Should return result
            assert result is not None

    @pytest.mark.asyncio
    async def test_search_logs_circuit_breaker_integration(self):
        """
        GIVEN: LokiLoggingClient with circuit breaker
        WHEN: search_logs fails repeatedly
        THEN: Circuit breaker should open

        User Journey: Prevent cascade failures when Loki is down
        """
        import pybreaker

        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset circuit breaker state before test
        reset_circuit_breaker("loki")

        client = LokiLoggingClient()

        async def mock_get_always_fails(*args, **kwargs):
            raise httpx.ConnectError("Loki down")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            mock_http_client = AsyncMock()
            mock_http_client.get = mock_get_always_fails
            client._client = mock_http_client
            client._initialized = True

            # Trigger enough failures to open circuit breaker
            for _ in range(6):
                try:
                    await client.search_logs(query="error")
                except (httpx.HTTPError, pybreaker.CircuitBreakerError):
                    pass

            # Verify circuit breaker is now OPEN
            breaker = get_circuit_breaker("loki")
            assert breaker.current_state == pybreaker.STATE_OPEN


@pytest.mark.xdist_group(name="observability_resilience_tests")
class TestHealthCheckCircuitBreakerIntegration:
    """Test health check integration with circuit breaker state."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_circuit_breakers_healthy_returns_true_when_all_closed(self):
        """
        GIVEN: All circuit breakers in CLOSED state
        WHEN: validate_circuit_breakers_healthy is called
        THEN: Should return (True, message)

        User Journey: Health check passes when no circuits are open
        """
        from mcp_server_langgraph.resilience.circuit_breaker import (
            reset_circuit_breaker,
        )

        # Reset all circuit breakers to CLOSED (critical + warning)
        reset_circuit_breaker("redis")
        reset_circuit_breaker("keycloak")
        reset_circuit_breaker("openfga")
        reset_circuit_breaker("postgres")
        reset_circuit_breaker("prometheus")
        reset_circuit_breaker("tempo")
        reset_circuit_breaker("loki")

        from mcp_server_langgraph.api.health import validate_circuit_breakers_healthy

        healthy, message = validate_circuit_breakers_healthy()

        assert healthy is True
        assert "healthy" in message.lower() or "closed" in message.lower()

    def test_validate_circuit_breakers_healthy_returns_false_when_critical_open(self):
        """
        GIVEN: A critical circuit breaker (redis) in OPEN state
        WHEN: validate_circuit_breakers_healthy is called
        THEN: Should return (False, message indicating which breaker is open)

        User Journey: Health check fails when critical circuit is open
        """
        import pybreaker

        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset all circuit breakers
        reset_circuit_breaker("redis")
        reset_circuit_breaker("keycloak")

        # Force redis circuit breaker to OPEN state
        breaker = get_circuit_breaker("redis")
        # Trip the breaker by simulating failures
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("simulated failure"))
            except pybreaker.CircuitBreakerError:
                pass

        # Verify it's open
        assert breaker.current_state == pybreaker.STATE_OPEN

        from mcp_server_langgraph.api.health import validate_circuit_breakers_healthy

        healthy, message = validate_circuit_breakers_healthy()

        assert healthy is False
        assert "redis" in message.lower()
        assert "open" in message.lower()

    @pytest.mark.asyncio
    async def test_readiness_probe_includes_circuit_breaker_check(self):
        """
        GIVEN: Readiness probe endpoint
        WHEN: Called with circuit breaker in OPEN state
        THEN: Should include circuit_breakers check in response

        User Journey: K8s readiness probe reflects circuit breaker health
        """
        import pybreaker

        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker,
        )

        # Reset and trip the redis circuit breaker
        reset_circuit_breaker("redis")
        breaker = get_circuit_breaker("redis")
        for _ in range(10):
            try:
                breaker._inc_counter()
                breaker.state.on_failure(Exception("simulated failure"))
            except pybreaker.CircuitBreakerError:
                pass

        # Verify it's open
        assert breaker.current_state == pybreaker.STATE_OPEN

        # Mock database connectivity to pass
        with patch(
            "mcp_server_langgraph.api.health.validate_database_connectivity_async",
            new_callable=AsyncMock,
        ) as mock_db:
            mock_db.return_value = (True, "Database connected")

            from mcp_server_langgraph.api.health import readiness_probe

            result = await readiness_probe()

            # Check that circuit_breakers is in the checks
            assert "circuit_breakers" in result.checks

            # Status should be "not_ready" if circuit breaker is OPEN
            # (depending on whether CB check is critical)
            assert result.checks["circuit_breakers"] is False
