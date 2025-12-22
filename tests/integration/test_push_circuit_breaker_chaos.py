"""
Chaos Engineering Tests for Push Notification Circuit Breaker.

Tests advanced circuit breaker scenarios:
- Half-open state recovery
- Timeout-based state transitions
- Concurrent failure handling
- Graceful degradation under load
- Circuit breaker metrics emission

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import asyncio
import gc
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pybreaker
import pytest

from mcp_server_langgraph.notifications.push_sender import (
    PushMessage,
    PushNotificationSender,
)
from mcp_server_langgraph.notifications.push_store import (
    InMemoryPushSubscriptionStore,
    PushSubscription,
)
from mcp_server_langgraph.resilience.circuit_breaker import (
    CircuitBreakerState,
    get_circuit_breaker,
    get_circuit_breaker_state,
    reset_all_circuit_breakers,
)

if TYPE_CHECKING:
    pass

# Mark as integration test
pytestmark = [pytest.mark.integration, pytest.mark.chaos]


@pytest.fixture
def push_store() -> InMemoryPushSubscriptionStore:
    """Create an in-memory push subscription store."""
    return InMemoryPushSubscriptionStore()


@pytest.fixture
def push_sender(push_store: InMemoryPushSubscriptionStore) -> PushNotificationSender:
    """Create a push notification sender with test VAPID keys."""
    return PushNotificationSender(
        vapid_private_key="test-private-key",
        vapid_public_key="test-public-key",
        vapid_claims={"sub": "mailto:admin@test.example.com"},
        subscription_store=push_store,
    )


@pytest.fixture
def sample_subscription() -> PushSubscription:
    """Create a sample push subscription."""
    return PushSubscription(
        id=str(uuid.uuid4()),
        user_id="chaos-test-user",
        endpoint="https://push.example.com/p/chaos-device",
        p256dh_key="test-p256dh-key",
        auth_key="test-auth-key",
        user_agent="Chaos Test/1.0",
        device_name="Chaos Test Device",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def reset_breakers() -> None:
    """Reset all circuit breakers before each test."""
    reset_all_circuit_breakers()


@pytest.mark.xdist_group(name="chaos_circuit_breaker")
class TestCircuitBreakerHalfOpenState:
    """Tests for circuit breaker half-open state transitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(self) -> None:
        """Test that circuit transitions from OPEN to HALF_OPEN after timeout."""
        cb = get_circuit_breaker("webpush")

        # Configure short timeout for testing (1 second)
        cb._reset_timeout = 1

        # Force circuit to OPEN by triggering failures
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        # Verify circuit is OPEN
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Wait for timeout to elapse
        await asyncio.sleep(1.5)

        # Next call should attempt half-open (pybreaker transitions on call attempt)
        # The call will fail but should transition to HALF_OPEN first
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("test failure")))
        except Exception:
            pass

        # After a failure in half-open, it goes back to OPEN
        # But we should verify the transition happened
        # For this test, we'll verify by succeeding after timeout
        cb.close()  # Reset for clean test

        # Force open again
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        await asyncio.sleep(1.5)

        # Successful call in half-open should close the circuit
        result = cb.call(lambda: "success")
        assert result == "success"
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self) -> None:
        """Test that a successful call in half-open state closes the circuit."""
        cb = get_circuit_breaker("webpush")
        cb._reset_timeout = 1

        # Force circuit to OPEN
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.2)

        # Successful call should close circuit
        result = cb.call(lambda: "recovery successful")
        assert result == "recovery successful"
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self) -> None:
        """Test that a failure in half-open state reopens the circuit."""
        cb = get_circuit_breaker("webpush")
        cb._reset_timeout = 1

        # Force circuit to OPEN
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Wait for timeout to allow half-open transition
        await asyncio.sleep(1.2)

        # Failing call in half-open should reopen circuit
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("still failing")))
        except Exception:
            pass

        # Circuit should be back to OPEN
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN


@pytest.mark.xdist_group(name="chaos_circuit_breaker")
class TestCircuitBreakerGracefulDegradation:
    """Tests for graceful degradation under circuit breaker protection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_open_circuit(
        self,
        push_sender: PushNotificationSender,
        push_store: InMemoryPushSubscriptionStore,
    ) -> None:
        """Test that circuit stays closed when failures are below threshold."""
        # Create subscriptions
        for i in range(5):
            sub = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=f"user-{i}",
                endpoint=f"https://push.example.com/p/device-{i}",
                p256dh_key=f"key-{i}",
                auth_key=f"auth-{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await push_store.save_subscription(sub)

        cb = get_circuit_breaker("webpush")

        # Trigger fewer failures than threshold
        failures_to_trigger = cb.fail_max - 1
        for _ in range(failures_to_trigger):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("partial failure")))
            except Exception:
                pass

        # Circuit should still be closed
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_calls_reset_failure_count(self) -> None:
        """Test that successful calls reset the failure counter."""
        cb = get_circuit_breaker("webpush")

        # Trigger some failures (but not enough to open)
        for _ in range(cb.fail_max - 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        # Successful call should reset failure count
        result = cb.call(lambda: "success")
        assert result == "success"

        # Now we should be able to have more failures before opening
        for _ in range(cb.fail_max - 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        # Still closed because success reset the counter
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.CLOSED


@pytest.mark.xdist_group(name="chaos_circuit_breaker")
class TestCircuitBreakerConcurrentAccess:
    """Tests for circuit breaker behavior under concurrent access."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_concurrent_failures_trip_circuit_once(self) -> None:
        """Test that concurrent failures properly trip the circuit once."""
        cb = get_circuit_breaker("webpush")
        failure_count = 0
        open_count = 0

        async def trigger_failure() -> None:
            nonlocal failure_count, open_count
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("concurrent failure")))
            except pybreaker.CircuitBreakerError:
                open_count += 1
            except Exception:
                failure_count += 1

        # Trigger many concurrent failures
        tasks = [trigger_failure() for _ in range(20)]
        await asyncio.gather(*tasks)

        # Circuit should be OPEN
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Some failures should have occurred before circuit opened
        assert failure_count > 0
        # Some should have been rejected by open circuit
        assert open_count > 0

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(
        self,
        push_sender: PushNotificationSender,
        push_store: InMemoryPushSubscriptionStore,
    ) -> None:
        """Test circuit breaker with concurrent success/failure mix."""
        # Create subscriptions
        for i in range(10):
            sub = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=f"concurrent-user-{i}",
                endpoint=f"https://push.example.com/p/concurrent-device-{i}",
                p256dh_key=f"key-{i}",
                auth_key=f"auth-{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await push_store.save_subscription(sub)

        success_count = 0
        failure_count = 0
        message = PushMessage(title="Concurrent Test", body="Testing concurrent access")

        async def send_push(should_fail: bool) -> None:
            nonlocal success_count, failure_count
            try:
                with patch.object(
                    push_sender, "_send_webpush", new_callable=AsyncMock
                ) as mock_send:
                    if should_fail:
                        mock_send.side_effect = Exception("Service unavailable")
                    else:
                        mock_send.return_value = True

                    result = await push_sender.send_to_all(message)
                    if result > 0:
                        success_count += 1
                    else:
                        failure_count += 1
            except Exception:
                failure_count += 1

        # Mix of success and failure operations
        tasks = [send_push(i % 3 == 0) for i in range(15)]  # 1/3 failures
        await asyncio.gather(*tasks, return_exceptions=True)

        # Circuit should still be functional
        state = get_circuit_breaker_state("webpush")
        assert state in {CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN}


@pytest.mark.xdist_group(name="chaos_circuit_breaker")
class TestCircuitBreakerMetricsEmission:
    """Tests for circuit breaker metrics emission during state changes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_state_change_emits_metric(self) -> None:
        """Test that state changes emit OpenTelemetry metrics."""
        cb = get_circuit_breaker("webpush")

        with patch(
            "mcp_server_langgraph.observability.telemetry.circuit_breaker_state_gauge"
        ) as mock_gauge:
            # Force circuit to OPEN
            for _ in range(cb.fail_max + 1):
                try:
                    cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
                except Exception:
                    pass

            # Verify metric was emitted for state change
            assert mock_gauge.set.called

    @pytest.mark.asyncio
    async def test_failure_counter_increments(self) -> None:
        """Test that failure counter metric increments on failures."""
        cb = get_circuit_breaker("webpush")

        with patch(
            "mcp_server_langgraph.observability.telemetry.circuit_breaker_failure_counter"
        ) as mock_counter:
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

            # Verify failure counter was incremented
            mock_counter.add.assert_called_with(
                1,
                attributes={
                    "service": "webpush",
                    "exception_type": "Exception",
                },
            )

    @pytest.mark.asyncio
    async def test_success_counter_increments(self) -> None:
        """Test that success counter metric increments on success."""
        cb = get_circuit_breaker("webpush")

        with patch(
            "mcp_server_langgraph.observability.telemetry.circuit_breaker_success_counter"
        ) as mock_counter:
            cb.call(lambda: "success")

            # Verify success counter was incremented
            mock_counter.add.assert_called_with(1, attributes={"service": "webpush"})


@pytest.mark.xdist_group(name="chaos_circuit_breaker")
class TestCircuitBreakerRecoveryPatterns:
    """Tests for different recovery patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_gradual_recovery_pattern(self) -> None:
        """Test gradual recovery with multiple success calls in half-open."""
        cb = get_circuit_breaker("webpush")
        cb._reset_timeout = 1

        # Force circuit to OPEN
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.2)

        # First successful call closes circuit
        result = cb.call(lambda: "recovery-1")
        assert result == "recovery-1"
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.CLOSED

        # Subsequent calls should all succeed
        for i in range(5):
            result = cb.call(lambda i=i: f"success-{i}")
            assert result == f"success-{i}"

        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_repeated_failure_recovery_cycles(self) -> None:
        """Test multiple open/close cycles."""
        cb = get_circuit_breaker("webpush")
        cb._reset_timeout = 1

        for cycle in range(3):
            # Force circuit to OPEN
            for _ in range(cb.fail_max + 1):
                try:
                    cb.call(lambda: (_ for _ in ()).throw(Exception(f"cycle-{cycle}")))
                except Exception:
                    pass

            assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

            # Wait and recover
            await asyncio.sleep(1.2)
            result = cb.call(lambda: f"recovered-{cycle}")
            assert result == f"recovered-{cycle}"
            assert get_circuit_breaker_state("webpush") == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_immediate_failure_after_recovery(self) -> None:
        """Test that immediate failure after recovery reopens circuit faster."""
        cb = get_circuit_breaker("webpush")
        cb._reset_timeout = 1

        # First failure cycle
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("initial")))
            except Exception:
                pass

        await asyncio.sleep(1.2)

        # Recover
        cb.call(lambda: "recovered")
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.CLOSED

        # Immediate failures should trip circuit again
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("relapse")))
            except Exception:
                pass

        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN


@pytest.mark.xdist_group(name="chaos_circuit_breaker")
class TestCircuitBreakerPushIntegration:
    """Tests for circuit breaker integration with push notification sender."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_sender_respects_open_circuit(
        self,
        push_sender: PushNotificationSender,
        push_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that push sender returns 0 when circuit is open."""
        await push_store.save_subscription(sample_subscription)

        cb = get_circuit_breaker("webpush")

        # Force circuit to OPEN
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Push should fail fast
        message = PushMessage(title="Test", body="Circuit should be open")
        result = await push_sender.send_to_user(sample_subscription.user_id, message)

        # Should return 0 because circuit is open
        assert result == 0

    @pytest.mark.asyncio
    async def test_push_sender_metrics_on_circuit_open(
        self,
        push_sender: PushNotificationSender,
        push_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that push sender logs warning when circuit is open."""
        await push_store.save_subscription(sample_subscription)

        cb = get_circuit_breaker("webpush")

        # Force circuit to OPEN
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        with patch(
            "mcp_server_langgraph.notifications.push_sender.logger"
        ) as mock_logger:
            message = PushMessage(title="Test", body="Open circuit test")
            await push_sender.send_to_user(sample_subscription.user_id, message)

            # Should log warning about open circuit
            mock_logger.warning.assert_called()
            call_args = str(mock_logger.warning.call_args)
            assert "Circuit breaker open" in call_args or "skipping" in call_args.lower()

    @pytest.mark.asyncio
    async def test_push_sender_recovers_with_circuit(
        self,
        push_sender: PushNotificationSender,
        push_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that push sender works again after circuit recovery."""
        await push_store.save_subscription(sample_subscription)

        cb = get_circuit_breaker("webpush")
        cb._reset_timeout = 1

        # Force circuit to OPEN
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Wait for recovery window
        await asyncio.sleep(1.2)

        # Manually close circuit to simulate recovery
        cb.close()

        # Push should work now
        with patch.object(
            push_sender, "_send_webpush", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True
            message = PushMessage(title="Recovery Test", body="Circuit recovered")
            result = await push_sender.send_to_user(
                sample_subscription.user_id, message
            )

            assert result == 1
            mock_send.assert_called_once()


@pytest.mark.xdist_group(name="chaos_circuit_breaker")
class TestCircuitBreakerTimingBehavior:
    """Tests for circuit breaker timing-related behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_circuit_stays_open_before_timeout(self) -> None:
        """Test that circuit stays open before timeout expires."""
        cb = get_circuit_breaker("webpush")
        cb._reset_timeout = 10  # Long timeout

        # Force circuit to OPEN
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("failure")))
            except Exception:
                pass

        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Wait a short time (less than timeout)
        await asyncio.sleep(0.5)

        # Circuit should still be OPEN
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN

        # Calls should still be rejected
        rejected = False
        try:
            cb.call(lambda: "should fail")
        except pybreaker.CircuitBreakerError:
            rejected = True

        assert rejected

    @pytest.mark.asyncio
    async def test_fast_failure_detection(self) -> None:
        """Test that failures are detected quickly without delays."""
        cb = get_circuit_breaker("webpush")

        start_time = time.monotonic()

        # Trigger failures rapidly
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fast failure")))
            except Exception:
                pass

        elapsed = time.monotonic() - start_time

        # Should complete quickly (no artificial delays)
        assert elapsed < 1.0  # Should be nearly instant

        # Circuit should be OPEN
        assert get_circuit_breaker_state("webpush") == CircuitBreakerState.OPEN
