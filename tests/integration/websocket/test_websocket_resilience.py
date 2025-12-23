"""
WebSocket Resilience Integration Tests.

End-to-end tests for WebSocket resilience patterns:
- Circuit breakers for external service failures
- Rate limiting for abuse prevention
- Heartbeat for dead connection detection
- Timeout handling for slow operations

Architecture:
- Tests use mock services to simulate failures
- Tests verify circuit breaker state transitions
- Tests verify rate limiting enforcement
- Tests verify heartbeat timeout detection
"""

from __future__ import annotations

import asyncio
import gc
from unittest.mock import AsyncMock

import pybreaker
import pytest

from mcp_server_langgraph.websocket.heartbeat import HeartbeatManager
from mcp_server_langgraph.websocket.rate_limiter import (
    ConnectionRateLimiter,
    MessageRateLimiter,
    RateLimitInfo,
    UserRateLimiter,
    WebSocketRateLimiter,
)
from mcp_server_langgraph.websocket.resilience import (
    WebSocketServices,
    get_circuit_breaker_state,
    is_circuit_open,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.resilience,
    pytest.mark.asyncio,
]


# =============================================================================
# Circuit Breaker Tests
# =============================================================================


@pytest.mark.xdist_group(name="websocket_resilience_cb")
class TestWebSocketCircuitBreaker:
    """Integration tests for WebSocket circuit breaker patterns."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_circuit_breaker_state_management(self):
        """GIVEN circuit breaker WHEN accessed THEN state is accessible."""
        from mcp_server_langgraph.resilience.circuit_breaker import (
            CircuitBreakerState,
            get_circuit_breaker,
        )

        test_service = "test_state_management"
        breaker = get_circuit_breaker(test_service)

        # Breaker should exist
        assert breaker is not None

        # State should be retrievable
        state = get_circuit_breaker_state(test_service)
        assert state in [
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
        ]

    async def test_circuit_breaker_synchronous_call(self):
        """GIVEN circuit breaker WHEN sync call succeeds THEN result returned."""
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

        test_service = "test_sync_call"
        breaker = get_circuit_breaker(test_service)

        # Sync calls work without pybreaker async issues
        def sync_operation():
            return {"status": "success", "value": 42}

        result = breaker.call(sync_operation)

        assert result["status"] == "success"
        assert result["value"] == 42

    async def test_circuit_breaker_opens_after_failures(self):
        """GIVEN multiple failures WHEN threshold exceeded THEN circuit opens."""
        from mcp_server_langgraph.resilience.circuit_breaker import (
            CircuitBreakerState,
            get_circuit_breaker,
        )

        test_service = "test_opens_after_failures"
        breaker = get_circuit_breaker(test_service)

        # Force failures using sync calls
        for _ in range(10):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("failure")))  # noqa: E731
            except Exception:
                pass

        # Circuit should be open now
        state = get_circuit_breaker_state(test_service)
        assert state == CircuitBreakerState.OPEN

    async def test_circuit_breaker_rejects_when_open(self):
        """GIVEN open circuit WHEN called THEN raises CircuitBreakerError."""
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

        test_service = "test_rejects_when_open"
        breaker = get_circuit_breaker(test_service)

        # Force circuit open
        for _ in range(10):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("failure")))  # noqa: E731
            except Exception:
                pass

        # Should reject with CircuitBreakerError
        with pytest.raises(pybreaker.CircuitBreakerError):
            breaker.call(lambda: "this should fail")

    async def test_get_circuit_breaker_state_returns_correct_state(self):
        """GIVEN circuit breaker WHEN get_state called THEN returns correct state."""
        from mcp_server_langgraph.resilience.circuit_breaker import (
            CircuitBreakerState,
        )

        # Create a fresh test service
        test_service = "test_service_state_check"

        # Initial state should be CLOSED
        state = get_circuit_breaker_state(test_service)
        assert state == CircuitBreakerState.CLOSED

        # is_circuit_open should return False
        assert is_circuit_open(test_service) is False

    async def test_websocket_services_constants(self):
        """GIVEN WebSocketServices WHEN accessed THEN returns expected constants."""
        assert WebSocketServices.REDIS == "websocket_redis"
        assert WebSocketServices.OPENFGA == "websocket_openfga"
        assert WebSocketServices.DATABASE == "websocket_database"
        assert WebSocketServices.METRICS_SERVICE == "websocket_metrics"
        assert WebSocketServices.COST_SERVICE == "websocket_cost"
        assert WebSocketServices.NOTIFICATIONS == "websocket_notifications"


# =============================================================================
# Rate Limiting Tests
# =============================================================================


@pytest.mark.xdist_group(name="websocket_resilience_rl")
class TestWebSocketRateLimiting:
    """Integration tests for WebSocket rate limiting patterns."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_message_rate_limiter_allows_within_limit(self):
        """GIVEN rate limiter WHEN within limit THEN messages allowed."""
        limiter = MessageRateLimiter(max_messages=10, window_seconds=60)

        # Should allow 10 messages
        for i in range(10):
            assert limiter.check_and_increment() is True, f"Message {i + 1} should be allowed"

        # 11th should be denied
        assert limiter.check_and_increment() is False

    async def test_message_rate_limiter_resets_after_window(self):
        """GIVEN exhausted limit WHEN window expires THEN limit resets."""
        limiter = MessageRateLimiter(max_messages=5, window_seconds=1)

        # Exhaust the limit
        for _ in range(5):
            limiter.check_and_increment()

        assert limiter.check_and_increment() is False

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be allowed again
        assert limiter.check_and_increment() is True

    async def test_message_rate_limiter_get_remaining(self):
        """GIVEN rate limiter WHEN get_remaining called THEN returns correct value."""
        limiter = MessageRateLimiter(max_messages=10, window_seconds=60)

        assert limiter.get_remaining() == 10

        for _ in range(3):
            limiter.check_and_increment()

        assert limiter.get_remaining() == 7

    async def test_user_rate_limiter_per_user_tracking(self):
        """GIVEN user rate limiter WHEN different users THEN independent limits."""
        limiter = UserRateLimiter(max_messages=5, window_seconds=60)

        # User A uses their limit
        for _ in range(5):
            assert limiter.check_and_increment("user-a") is True

        # User A is now limited
        assert limiter.check_and_increment("user-a") is False

        # User B should still have their full limit
        for _ in range(5):
            assert limiter.check_and_increment("user-b") is True

        assert limiter.check_and_increment("user-b") is False

    async def test_user_rate_limiter_cleanup_expired(self):
        """GIVEN expired user limits WHEN cleanup called THEN users removed."""
        limiter = UserRateLimiter(max_messages=5, window_seconds=1)

        # Create some users
        limiter.check_and_increment("user-1")
        limiter.check_and_increment("user-2")
        limiter.check_and_increment("user-3")

        assert limiter.get_user_count() == 3

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Cleanup expired users
        limiter.cleanup_expired()

        # All users should be cleaned up
        assert limiter.get_user_count() == 0

    async def test_connection_rate_limiter_enforces_max(self):
        """GIVEN connection limiter WHEN at max THEN new connections rejected."""
        limiter = ConnectionRateLimiter(max_connections=3)

        # First 3 connections allowed
        assert limiter.check_connection() is True
        assert limiter.check_connection() is True
        assert limiter.check_connection() is True

        # 4th rejected
        assert limiter.check_connection() is False

        # Active count is at max
        assert limiter.active_connections == 3

    async def test_connection_rate_limiter_release(self):
        """GIVEN at max connections WHEN connection released THEN new allowed."""
        limiter = ConnectionRateLimiter(max_connections=2)

        assert limiter.check_connection() is True
        assert limiter.check_connection() is True
        assert limiter.check_connection() is False

        # Release one connection
        limiter.release_connection()

        # Now a new one is allowed
        assert limiter.check_connection() is True

    async def test_websocket_rate_limiter_combined(self):
        """GIVEN WebSocketRateLimiter WHEN used THEN tracks per-user."""
        limiter = WebSocketRateLimiter(messages_per_minute=5)

        # User messages
        for _ in range(5):
            assert limiter.check_message(user_id="user-123") is True

        # User is now limited
        assert limiter.check_message(user_id="user-123") is False

        # Another user is fine
        assert limiter.check_message(user_id="user-456") is True

    async def test_websocket_rate_limiter_global_fallback(self):
        """GIVEN no user_id WHEN check_message called THEN uses global limit."""
        limiter = WebSocketRateLimiter(messages_per_minute=3)

        # Anonymous messages
        assert limiter.check_message() is True
        assert limiter.check_message() is True
        assert limiter.check_message() is True

        # Now limited
        assert limiter.check_message() is False

        # But user-specific is separate
        assert limiter.check_message(user_id="user-with-id") is True

    async def test_rate_limit_info_structure(self):
        """GIVEN rate limit WHEN get_rate_limit_info called THEN returns RateLimitInfo."""
        limiter = WebSocketRateLimiter(messages_per_minute=100)

        # Use some quota
        for _ in range(30):
            limiter.check_message(user_id="test-user")

        info = limiter.get_rate_limit_info(user_id="test-user")

        assert isinstance(info, RateLimitInfo)
        assert info.limit == 100
        assert info.remaining == 70
        assert info.retry_after >= 0

        # Check dict conversion
        info_dict = info.to_dict()
        assert info_dict["limit"] == 100
        assert info_dict["remaining"] == 70

    async def test_websocket_rate_limiter_stats(self):
        """GIVEN limiter with activity WHEN get_stats called THEN returns stats."""
        limiter = WebSocketRateLimiter(messages_per_minute=100)

        # Create some users
        limiter.check_message(user_id="user-1")
        limiter.check_message(user_id="user-2")
        limiter.check_message(user_id="user-3")

        stats = limiter.get_stats()

        assert stats["messages_per_minute"] == 100
        assert stats["active_users"] == 3
        assert stats["global_remaining"] == 100  # No anonymous messages


# =============================================================================
# Heartbeat Tests
# =============================================================================


@pytest.mark.xdist_group(name="websocket_resilience_hb")
class TestWebSocketHeartbeat:
    """Integration tests for WebSocket heartbeat patterns."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_heartbeat_manager_initialization(self):
        """GIVEN HeartbeatManager WHEN created THEN has correct defaults."""
        manager = HeartbeatManager(interval=30)

        assert manager.interval == 30
        assert manager.timeout == 90  # 3x interval by default
        assert manager.is_alive is True  # Just created

    async def test_heartbeat_manager_custom_timeout(self):
        """GIVEN custom timeout WHEN created THEN uses custom value."""
        manager = HeartbeatManager(interval=30, timeout=60)

        assert manager.interval == 30
        assert manager.timeout == 60  # Custom value

    async def test_heartbeat_manager_start_creates_task(self):
        """GIVEN HeartbeatManager WHEN start called THEN creates background task."""
        manager = HeartbeatManager(interval=1)

        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        task = await manager.start(mock_websocket)

        try:
            assert task is not None
            assert not task.done()
        finally:
            await manager.stop()

    async def test_heartbeat_manager_stop_cancels_task(self):
        """GIVEN running heartbeat WHEN stop called THEN task cancelled."""
        manager = HeartbeatManager(interval=1)

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        task = await manager.start(mock_websocket)
        assert not task.done()

        await manager.stop()

        # Task should be cancelled
        assert task.done()

    async def test_heartbeat_manager_on_pong_updates_activity(self):
        """GIVEN heartbeat manager WHEN on_pong called THEN last_activity updated."""
        manager = HeartbeatManager(interval=30)

        initial_activity = manager.last_activity

        # Simulate some time passing
        await asyncio.sleep(0.1)

        await manager.on_pong()

        assert manager.last_activity > initial_activity

    async def test_heartbeat_manager_is_alive_within_timeout(self):
        """GIVEN recent activity WHEN is_alive checked THEN returns True."""
        manager = HeartbeatManager(interval=30, timeout=90)

        await manager.on_pong()
        assert manager.is_alive is True

    async def test_heartbeat_manager_sends_heartbeat_messages(self):
        """GIVEN running manager WHEN interval elapses THEN sends heartbeat."""
        manager = HeartbeatManager(interval=0.1)  # Very short for testing

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        await manager.start(mock_websocket)

        try:
            # Wait for a heartbeat to be sent
            await asyncio.sleep(0.3)

            # Should have called send_json with heartbeat
            assert mock_websocket.send_json.called
            call_args = mock_websocket.send_json.call_args_list
            # Find a heartbeat message
            heartbeat_found = any(call.args[0].get("type") == "heartbeat" for call in call_args if call.args)
            assert heartbeat_found, "Expected heartbeat message to be sent"
        finally:
            await manager.stop()

    async def test_heartbeat_manager_timeout_callback(self):
        """GIVEN timeout WHEN connection dead THEN callback invoked."""
        timeout_called = False

        async def on_timeout():
            nonlocal timeout_called
            timeout_called = True

        # Very short intervals for testing
        manager = HeartbeatManager(interval=0.1, timeout=0.2, on_timeout=on_timeout)

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        await manager.start(mock_websocket)

        try:
            # Wait for timeout to occur (no pong responses)
            await asyncio.sleep(0.5)

            # Timeout callback should have been called
            assert timeout_called is True
        finally:
            await manager.stop()


# =============================================================================
# Timeout Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="websocket_resilience_timeout")
class TestWebSocketTimeout:
    """Integration tests for WebSocket timeout patterns."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_async_operation_completes_within_timeout(self):
        """GIVEN fast operation WHEN within timeout THEN completes successfully."""

        async def fast_operation():
            await asyncio.sleep(0.1)
            return "completed"

        # Should complete within 1 second
        result = await asyncio.wait_for(fast_operation(), timeout=1.0)
        assert result == "completed"

    async def test_async_operation_timeout_raises_exception(self):
        """GIVEN slow operation WHEN timeout exceeded THEN TimeoutError raised."""

        async def slow_operation():
            await asyncio.sleep(10)  # Way too slow
            return "never reached"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=0.1)

    async def test_timeout_with_fallback_pattern(self):
        """GIVEN timeout WHEN fallback provided THEN fallback used."""

        async def slow_operation():
            await asyncio.sleep(10)
            return "slow result"

        fallback_value = "timeout fallback"

        try:
            result = await asyncio.wait_for(slow_operation(), timeout=0.1)
        except TimeoutError:
            result = fallback_value

        assert result == fallback_value


# =============================================================================
# End-to-End Resilience Tests
# =============================================================================


@pytest.mark.xdist_group(name="websocket_resilience_e2e")
class TestWebSocketResilienceE2E:
    """End-to-end tests combining multiple resilience patterns."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_combined_rate_limit_and_circuit_breaker(self):
        """GIVEN rate limit and circuit breaker WHEN both triggered THEN both enforced."""
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

        # Rate limiter
        limiter = WebSocketRateLimiter(messages_per_minute=3)

        # Get a circuit breaker (using sync call to avoid pybreaker async bug)
        test_service = "test_combined_e2e"
        breaker = get_circuit_breaker(test_service)

        # Simulate messages with rate limit + circuit breaker protection
        results = []
        for i in range(5):
            if limiter.check_message(user_id="test-user"):
                # Message allowed - simulate external service call using sync breaker
                try:
                    result = breaker.call(lambda idx=i: f"result-{idx}")
                    results.append(result)
                except Exception:
                    results.append("error")
            else:
                results.append("rate_limited")

        # First 3 should succeed, last 2 rate limited
        assert len([r for r in results if r.startswith("result")]) == 3
        assert results.count("rate_limited") == 2

    async def test_connection_lifecycle_resilience(self):
        """GIVEN WebSocket connection WHEN lifecycle events occur THEN resilience applied."""
        # Simulate connection lifecycle
        connection_limiter = ConnectionRateLimiter(max_connections=2)
        message_limiter = WebSocketRateLimiter(messages_per_minute=10)

        # Simulate 3 connection attempts
        connections = []
        for conn_id in range(3):
            if connection_limiter.check_connection():
                connections.append(conn_id)

        # Only 2 connections allowed
        assert len(connections) == 2
        assert 0 in connections
        assert 1 in connections

        # Simulate messages on connection 0
        for _ in range(12):
            message_limiter.check_message(user_id="conn-0")

        # Connection 0 should be rate limited
        assert message_limiter.check_message(user_id="conn-0") is False

        # Connection 1 should still have quota
        assert message_limiter.check_message(user_id="conn-1") is True

        # Simulate connection 0 disconnecting
        connection_limiter.release_connection()

        # Now connection 2 can connect
        assert connection_limiter.check_connection() is True

    async def test_graceful_degradation_pattern(self):
        """GIVEN cascading failures WHEN degradation pattern applied THEN service continues."""
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

        # Simulate primary, secondary, and fallback services
        primary_available = False
        secondary_available = False

        def call_primary():
            if not primary_available:
                raise Exception("Primary unavailable")
            return "primary_result"

        def call_secondary():
            if not secondary_available:
                raise Exception("Secondary unavailable")
            return "secondary_result"

        fallback_result = "cached_result"

        # Attempt with graceful degradation using sync circuit breaker calls
        result = None

        # Try primary (using sync call to avoid pybreaker async bug)
        primary_breaker = get_circuit_breaker("test_primary_gd")
        try:
            result = primary_breaker.call(call_primary)
        except Exception:
            pass

        # Try secondary if primary failed
        if result is None:
            secondary_breaker = get_circuit_breaker("test_secondary_gd")
            try:
                result = secondary_breaker.call(call_secondary)
            except Exception:
                pass

        # Fall back to cached result
        if result is None:
            result = fallback_result

        assert result == fallback_result

    async def test_backpressure_handling(self):
        """GIVEN high load WHEN backpressure applied THEN system remains stable."""
        limiter = WebSocketRateLimiter(messages_per_minute=100)

        # Simulate burst of 200 messages from single user
        allowed = 0
        rejected = 0

        for _ in range(200):
            if limiter.check_message(user_id="burst-user"):
                allowed += 1
            else:
                rejected += 1

        # Should only allow up to the limit
        assert allowed == 100
        assert rejected == 100

        # System should provide backoff info
        info = limiter.get_rate_limit_info(user_id="burst-user")
        assert info.remaining == 0
        assert info.retry_after > 0
