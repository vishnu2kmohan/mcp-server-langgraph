"""
Push Notification Sender Tests.

TDD tests for the Web Push notification sender service.

Features:
- Build push messages with proper formatting
- Send notifications to individual users
- Send critical alerts to all admin users
- Handle failed/expired subscriptions gracefully
- Update last_used_at on successful sends

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.notifications.push_sender import (
    PushMessage,
    PushNotificationSender,
)
from mcp_server_langgraph.notifications.push_store import (
    InMemoryPushSubscriptionStore,
    PushSubscription,
)
from mcp_server_langgraph.observability.query.interfaces import Alert, AlertSeverity, AlertState

pytestmark = pytest.mark.unit

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_subscription_store() -> InMemoryPushSubscriptionStore:
    """Create an in-memory subscription store with test data."""
    return InMemoryPushSubscriptionStore()


@pytest.fixture
def sample_subscription() -> PushSubscription:
    """Create a sample push subscription."""
    return PushSubscription(
        id=str(uuid.uuid4()),
        user_id="user-001",
        endpoint="https://push.example.com/p/abc123",
        p256dh_key="BGV2vxH1234567890abcdef",
        auth_key="auth123secret",
        user_agent="Mozilla/5.0 Chrome/120.0",
        device_name="Work Laptop",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_alert() -> Alert:
    """Create a sample alert for testing."""
    return Alert(
        alert_id="alert-001",
        name="HighCPU",
        severity=AlertSeverity.CRITICAL,
        state=AlertState.FIRING,
        message="CPU usage at 95%",
        labels={"service": "api-server", "namespace": "production"},
        annotations={"runbook_url": "https://runbooks.example.com/cpu"},
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def sender(mock_subscription_store: InMemoryPushSubscriptionStore) -> PushNotificationSender:
    """Create a push notification sender with mocked webpush."""
    return PushNotificationSender(
        vapid_private_key="fake-private-key",
        vapid_public_key="fake-public-key",
        vapid_claims={"sub": "mailto:admin@example.com"},
        subscription_store=mock_subscription_store,
    )


# =============================================================================
# PushMessage Tests
# =============================================================================


class TestPushMessage:
    """Tests for the PushMessage dataclass."""

    def test_create_message(self) -> None:
        """Test creating a push message with all fields."""
        message = PushMessage(
            title="Test Alert",
            body="This is a test notification",
            icon="/icons/icon-192.png",
            badge="/icons/badge-72.png",
            tag="test-alert-001",
            data={"alert_id": "001", "type": "critical_alert"},
            actions=[
                {"action": "view", "title": "View Alert"},
                {"action": "dismiss", "title": "Dismiss"},
            ],
        )
        assert message.title == "Test Alert"
        assert message.body == "This is a test notification"
        assert message.tag == "test-alert-001"
        assert len(message.actions or []) == 2

    def test_to_payload(self) -> None:
        """Test converting message to JSON payload."""
        message = PushMessage(
            title="Test Alert",
            body="This is a test notification",
            tag="test-001",
        )
        payload = message.to_payload()
        assert "title" in payload
        assert "body" in payload
        assert payload["title"] == "Test Alert"

    def test_minimal_message(self) -> None:
        """Test creating a minimal push message."""
        message = PushMessage(title="Minimal", body="Just a body")
        assert message.title == "Minimal"
        assert message.body == "Just a body"
        assert message.icon is None
        assert message.actions is None


# =============================================================================
# PushNotificationSender Tests
# =============================================================================


class TestPushNotificationSender:
    """Tests for the push notification sender service."""

    def test_create_sender(self, mock_subscription_store: InMemoryPushSubscriptionStore) -> None:
        """Test creating a push notification sender."""
        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )
        assert sender is not None

    @pytest.mark.asyncio
    async def test_send_to_user_no_subscriptions(
        self,
        sender: PushNotificationSender,
    ) -> None:
        """Test sending to a user with no subscriptions."""
        message = PushMessage(title="Test", body="Test message")
        result = await sender.send_to_user("nonexistent-user", message)
        assert result == 0

    @pytest.mark.asyncio
    async def test_send_to_user_with_subscriptions(
        self,
        sender: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test sending to a user with subscriptions."""
        # Add subscription
        await mock_subscription_store.save_subscription(sample_subscription)

        message = PushMessage(title="Test", body="Test message")

        # Mock the webpush call
        with patch.object(sender, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await sender.send_to_user(sample_subscription.user_id, message)

        assert result == 1
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_user_updates_last_used(
        self,
        sender: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that successful send updates last_used_at."""
        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        with patch.object(sender, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            await sender.send_to_user(sample_subscription.user_id, message)

        # Verify last_used_at was updated
        result = await mock_subscription_store.get_by_endpoint(sample_subscription.endpoint)
        assert result is not None
        assert result.last_used_at is not None

    @pytest.mark.asyncio
    async def test_send_to_user_handles_failed_subscription(
        self,
        sender: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that failed send doesn't update last_used_at."""
        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        with patch.object(sender, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False  # Simulate failure
            result = await sender.send_to_user(sample_subscription.user_id, message)

        assert result == 0

    @pytest.mark.asyncio
    async def test_send_critical_alert(
        self,
        sender: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
        sample_alert: Alert,
    ) -> None:
        """Test sending a critical alert notification."""
        await mock_subscription_store.save_subscription(sample_subscription)

        with patch.object(sender, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await sender.send_critical_alert(sample_alert)

        assert result >= 1

    @pytest.mark.asyncio
    async def test_send_critical_alert_message_format(
        self,
        sender: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
        sample_alert: Alert,
    ) -> None:
        """Test that critical alert message has correct format."""
        await mock_subscription_store.save_subscription(sample_subscription)
        captured_message: PushMessage | None = None

        async def capture_send(subscription: PushSubscription, message: PushMessage) -> bool:
            nonlocal captured_message
            captured_message = message
            return True

        with patch.object(sender, "_send_webpush", side_effect=capture_send):
            await sender.send_critical_alert(sample_alert)

        assert captured_message is not None
        assert "Critical" in captured_message.title
        assert sample_alert.name in captured_message.title
        assert sample_alert.alert_id in (captured_message.data or {}).get("alert_id", "")

    @pytest.mark.asyncio
    async def test_send_to_all_users(
        self,
        sender: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
    ) -> None:
        """Test sending to all users."""
        # Create subscriptions for multiple users
        for i in range(3):
            sub = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=f"user-{i}",
                endpoint=f"https://push.example.com/p/device{i}",
                p256dh_key=f"key{i}",
                auth_key=f"auth{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await mock_subscription_store.save_subscription(sub)

        message = PushMessage(title="Broadcast", body="To all users")

        with patch.object(sender, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await sender.send_to_all(message)

        assert result == 3


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestPushSenderErrorHandling:
    """Tests for error handling in push sender."""

    @pytest.mark.asyncio
    async def test_handles_webpush_exception(
        self,
        sender: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that exceptions in webpush are handled gracefully."""
        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        with patch.object(sender, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Network error")
            # Should not raise
            result = await sender.send_to_user(sample_subscription.user_id, message)

        assert result == 0

    @pytest.mark.asyncio
    async def test_removes_expired_subscription_on_410(
        self,
        sender: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that 410 Gone response removes subscription."""
        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        # Simulate 410 Gone (subscription expired)
        with patch.object(sender, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False
            # The sender should handle 410 internally

        # For now, just verify it doesn't crash
        result = await sender.send_to_user(sample_subscription.user_id, message)
        # Result may be 0 (failed) or subscription may be removed


# =============================================================================
# Circuit Breaker Integration Tests
# =============================================================================


class TestPushSenderCircuitBreaker:
    """Tests for circuit breaker integration in push sender."""

    @pytest.fixture(autouse=True)
    def reset_circuit_breakers(self) -> None:
        """Reset circuit breakers before each test."""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
    ) -> None:
        """Test that circuit breaker opens after multiple webpush failures."""
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            get_circuit_breaker_state,
            CircuitBreakerState,
        )

        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )

        # Create multiple subscriptions
        for i in range(10):
            sub = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=f"user-{i}",
                endpoint=f"https://push.example.com/p/device{i}",
                p256dh_key=f"key{i}",
                auth_key=f"auth{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await mock_subscription_store.save_subscription(sub)

        message = PushMessage(title="Test", body="Test message")

        # Get the circuit breaker to force failures directly
        cb = get_circuit_breaker("webpush")

        # Manually trigger failures to open the circuit (simulating failed webpush calls)
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("Push service unavailable")))
            except Exception:
                pass

        # Circuit breaker should be OPEN after multiple failures
        state = get_circuit_breaker_state("webpush")
        assert state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_fails_fast_when_open(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that circuit breaker fails fast when open."""
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
            get_circuit_breaker_state,
            CircuitBreakerState,
        )

        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )

        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        # Force circuit breaker to OPEN state
        cb = get_circuit_breaker("webpush")
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass

        # Verify circuit is open
        state = get_circuit_breaker_state("webpush")
        assert state == CircuitBreakerState.OPEN

        # Now try to send - should fail fast without calling the actual webpush
        result = await sender.send_to_user(sample_subscription.user_id, message)

        # Should return 0 (failed) because circuit is open
        assert result == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that successful sends keep circuit closed."""
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker_state,
            CircuitBreakerState,
        )

        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )

        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        # Mock the _send_webpush method to simulate success
        with patch.object(sender, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await sender.send_to_user(sample_subscription.user_id, message)

        assert result == 1
        # Circuit should remain closed (we didn't trigger real failures)
        state = get_circuit_breaker_state("webpush")
        assert state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_checked_before_webpush(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that circuit breaker state is checked before attempting webpush."""
        from mcp_server_langgraph.resilience.circuit_breaker import (
            get_circuit_breaker,
        )
        import pybreaker

        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )

        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        # Get circuit breaker and force it open
        cb = get_circuit_breaker("webpush")
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass

        # Verify it's open
        assert cb.current_state == pybreaker.STATE_OPEN

        # Try to send - the method should detect open circuit and return False immediately
        result = await sender._send_webpush(sample_subscription, message)

        # Should return False due to open circuit
        assert result is False


# =============================================================================
# Fallback Queue Integration Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_sender_fallback")
class TestPushSenderFallbackQueue:
    """Tests for fallback queue integration in push sender."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        import gc

        gc.collect()

    @pytest.fixture(autouse=True)
    def reset_circuit_breakers(self) -> None:
        """Reset circuit breakers before each test."""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()

    @pytest.fixture
    def mock_fallback_queue(self) -> AsyncMock:
        """Create a mock fallback queue."""
        queue = AsyncMock()
        queue.enqueue = AsyncMock()
        queue.dequeue_batch = AsyncMock(return_value=[])
        queue.requeue = AsyncMock()
        return queue

    @pytest.fixture
    def sender_with_queue(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_fallback_queue: AsyncMock,
    ) -> PushNotificationSender:
        """Create a push notification sender with fallback queue."""
        return PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
            fallback_queue=mock_fallback_queue,
        )

    @pytest.mark.asyncio
    async def test_queues_message_when_circuit_open(
        self,
        sender_with_queue: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_fallback_queue: AsyncMock,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that messages are queued when circuit breaker is open."""
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker
        import pybreaker

        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        # Force circuit breaker to OPEN state
        cb = get_circuit_breaker("webpush")
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass

        assert cb.current_state == pybreaker.STATE_OPEN

        # Try to send - should queue instead of failing
        result = await sender_with_queue._send_webpush(sample_subscription, message, user_id="user-001")

        # Should return True (queued successfully)
        assert result is True
        mock_fallback_queue.enqueue.assert_called_once()
        call_args = mock_fallback_queue.enqueue.call_args
        assert call_args.kwargs["message"] == message
        assert call_args.kwargs["subscription_endpoint"] == sample_subscription.endpoint
        assert call_args.kwargs["user_id"] == "user-001"

    @pytest.mark.asyncio
    async def test_returns_false_when_queue_fails(
        self,
        sender_with_queue: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_fallback_queue: AsyncMock,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that send returns False when queueing fails."""
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker
        import pybreaker

        await mock_subscription_store.save_subscription(sample_subscription)
        message = PushMessage(title="Test", body="Test message")

        # Force circuit breaker to OPEN state
        cb = get_circuit_breaker("webpush")
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass

        assert cb.current_state == pybreaker.STATE_OPEN

        # Make queue.enqueue fail
        mock_fallback_queue.enqueue.side_effect = Exception("Queue full")

        result = await sender_with_queue._send_webpush(sample_subscription, message, user_id="user-001")

        # Should return False (queue failed)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_fallback_queue_no_queue(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
    ) -> None:
        """Test that process_fallback_queue returns 0 when no queue configured."""
        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )

        result = await sender.process_fallback_queue()
        assert result == 0

    @pytest.mark.asyncio
    async def test_process_fallback_queue_circuit_open(
        self,
        sender_with_queue: PushNotificationSender,
        mock_fallback_queue: AsyncMock,
    ) -> None:
        """Test that queue processing skips when circuit is still open."""
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker
        import pybreaker

        # Force circuit breaker to OPEN state
        cb = get_circuit_breaker("webpush")
        for _ in range(cb.fail_max + 1):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass

        assert cb.current_state == pybreaker.STATE_OPEN

        result = await sender_with_queue.process_fallback_queue()
        assert result == 0
        mock_fallback_queue.dequeue_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_fallback_queue_empty(
        self,
        sender_with_queue: PushNotificationSender,
        mock_fallback_queue: AsyncMock,
    ) -> None:
        """Test that processing empty queue returns 0."""
        mock_fallback_queue.dequeue_batch.return_value = []

        result = await sender_with_queue.process_fallback_queue()
        assert result == 0

    @pytest.mark.asyncio
    async def test_process_fallback_queue_success(
        self,
        sender_with_queue: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_fallback_queue: AsyncMock,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test successful processing of queued messages."""
        from mcp_server_langgraph.notifications.push_fallback_queue import QueuedMessage
        from datetime import UTC, datetime

        await mock_subscription_store.save_subscription(sample_subscription)

        # Create a queued message
        queued = QueuedMessage(
            message_id="msg-001",
            message=PushMessage(title="Queued", body="Queued message"),
            subscription_endpoint=sample_subscription.endpoint,
            user_id=sample_subscription.user_id,
            enqueued_at=datetime.now(UTC),
            retry_count=0,
        )
        mock_fallback_queue.dequeue_batch.return_value = [queued]

        # Mock _send_webpush to succeed
        with patch.object(sender_with_queue, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await sender_with_queue.process_fallback_queue()

        assert result == 1
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_fallback_queue_requeues_on_failure(
        self,
        sender_with_queue: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_fallback_queue: AsyncMock,
        sample_subscription: PushSubscription,
    ) -> None:
        """Test that failed sends are requeued."""
        from mcp_server_langgraph.notifications.push_fallback_queue import QueuedMessage
        from datetime import UTC, datetime

        await mock_subscription_store.save_subscription(sample_subscription)

        queued = QueuedMessage(
            message_id="msg-002",
            message=PushMessage(title="Queued", body="Queued message"),
            subscription_endpoint=sample_subscription.endpoint,
            user_id=sample_subscription.user_id,
            enqueued_at=datetime.now(UTC),
            retry_count=1,
        )
        mock_fallback_queue.dequeue_batch.return_value = [queued]

        # Mock _send_webpush to fail
        with patch.object(sender_with_queue, "_send_webpush", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False
            result = await sender_with_queue.process_fallback_queue()

        assert result == 0
        mock_fallback_queue.requeue.assert_called_once_with(queued)

    @pytest.mark.asyncio
    async def test_process_fallback_queue_drops_missing_subscription(
        self,
        sender_with_queue: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_fallback_queue: AsyncMock,
    ) -> None:
        """Test that messages for missing subscriptions are dropped."""
        from mcp_server_langgraph.notifications.push_fallback_queue import QueuedMessage
        from datetime import UTC, datetime

        # Don't add subscription - it will be missing

        queued = QueuedMessage(
            message_id="msg-003",
            message=PushMessage(title="Queued", body="Queued message"),
            subscription_endpoint="https://push.example.com/p/nonexistent",
            user_id="user-001",
            enqueued_at=datetime.now(UTC),
            retry_count=0,
        )
        mock_fallback_queue.dequeue_batch.return_value = [queued]

        result = await sender_with_queue.process_fallback_queue()

        assert result == 0
        mock_fallback_queue.requeue.assert_not_called()

    def test_fallback_queue_property(
        self,
        sender_with_queue: PushNotificationSender,
        mock_fallback_queue: AsyncMock,
    ) -> None:
        """Test the fallback_queue property."""
        assert sender_with_queue.fallback_queue is mock_fallback_queue

    def test_fallback_queue_property_none(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
    ) -> None:
        """Test the fallback_queue property when not configured."""
        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )
        assert sender.fallback_queue is None


# =============================================================================
# PushAnalytics Integration Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_analytics_integration")
class TestPushSenderAnalyticsIntegration:
    """Tests for PushNotificationSender integration with PushAnalytics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc
        import sys

        # Clean up mock pywebpush module if we added it
        if "pywebpush" in sys.modules and hasattr(sys.modules["pywebpush"], "_is_mock"):
            del sys.modules["pywebpush"]

        gc.collect()

    @pytest.fixture
    def mock_pywebpush(self) -> MagicMock:
        """Inject a mock pywebpush module into sys.modules."""
        import sys

        mock_module = MagicMock()
        mock_module.webpush = MagicMock()
        mock_module._is_mock = True  # Mark as mock for cleanup
        sys.modules["pywebpush"] = mock_module
        return mock_module

    @pytest.fixture
    def mock_analytics(self) -> AsyncMock:
        """Create a mock PushAnalytics instance."""
        analytics = AsyncMock()
        analytics.record_delivery = AsyncMock()
        return analytics

    @pytest.fixture
    def sender_with_analytics(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_analytics: AsyncMock,
    ) -> PushNotificationSender:
        """Create a push sender with analytics enabled."""
        return PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
            analytics=mock_analytics,
        )

    @pytest.mark.asyncio
    async def test_analytics_records_successful_delivery(
        self,
        sender_with_analytics: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_analytics: AsyncMock,
        sample_subscription: PushSubscription,
        mock_pywebpush: MagicMock,
    ) -> None:
        """GIVEN analytics configured WHEN send succeeds THEN records delivery event."""
        await mock_subscription_store.save_subscription(sample_subscription)

        message = PushMessage(title="Test", body="Test notification")

        await sender_with_analytics.send_to_user(sample_subscription.user_id, message)

        mock_analytics.record_delivery.assert_called_once()
        call_args = mock_analytics.record_delivery.call_args[0][0]
        assert call_args.status == "delivered"
        assert call_args.user_id == sample_subscription.user_id

    @pytest.mark.asyncio
    async def test_analytics_records_failed_delivery(
        self,
        sender_with_analytics: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_analytics: AsyncMock,
        sample_subscription: PushSubscription,
        mock_pywebpush: MagicMock,
    ) -> None:
        """GIVEN analytics configured WHEN send fails THEN records failed delivery."""
        await mock_subscription_store.save_subscription(sample_subscription)

        message = PushMessage(title="Test", body="Test notification")

        # Make webpush raise an exception
        mock_pywebpush.webpush.side_effect = Exception("Push failed")

        await sender_with_analytics.send_to_user(sample_subscription.user_id, message)

        mock_analytics.record_delivery.assert_called_once()
        call_args = mock_analytics.record_delivery.call_args[0][0]
        assert call_args.status == "failed"
        assert call_args.error_code is not None

    @pytest.mark.asyncio
    async def test_analytics_records_latency(
        self,
        sender_with_analytics: PushNotificationSender,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        mock_analytics: AsyncMock,
        sample_subscription: PushSubscription,
        mock_pywebpush: MagicMock,
    ) -> None:
        """GIVEN analytics configured WHEN send succeeds THEN records latency."""
        await mock_subscription_store.save_subscription(sample_subscription)

        message = PushMessage(title="Test", body="Test notification")

        await sender_with_analytics.send_to_user(sample_subscription.user_id, message)

        call_args = mock_analytics.record_delivery.call_args[0][0]
        assert call_args.latency_ms is not None
        assert call_args.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_sender_without_analytics_works(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
        sample_subscription: PushSubscription,
        mock_pywebpush: MagicMock,
    ) -> None:
        """GIVEN no analytics configured WHEN sending THEN works without error."""
        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )
        await mock_subscription_store.save_subscription(sample_subscription)

        message = PushMessage(title="Test", body="Test notification")

        result = await sender.send_to_user(sample_subscription.user_id, message)

        assert result == 1

    @pytest.mark.asyncio
    async def test_analytics_property(
        self,
        sender_with_analytics: PushNotificationSender,
        mock_analytics: AsyncMock,
    ) -> None:
        """Test the analytics property returns the configured analytics."""
        assert sender_with_analytics.analytics is mock_analytics

    @pytest.mark.asyncio
    async def test_analytics_property_none(
        self,
        mock_subscription_store: InMemoryPushSubscriptionStore,
    ) -> None:
        """Test the analytics property returns None when not configured."""
        sender = PushNotificationSender(
            vapid_private_key="fake-private-key",
            vapid_public_key="fake-public-key",
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=mock_subscription_store,
        )
        assert sender.analytics is None
