"""
Unit Tests for Push Notification Fallback Queue.

Tests the Redis-backed fallback queue for push notifications when
the circuit breaker is open.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import asyncio
import gc
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from mcp_server_langgraph.notifications.push_fallback_queue import (
        PushFallbackQueue,
        QueuedMessage,
    )


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_fallback_queue")
class TestPushFallbackQueueEnqueue:
    """Tests for enqueueing messages to the fallback queue."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_enqueue_message_stores_in_redis(self) -> None:
        """Test that enqueue stores message in Redis list."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
            QueuedMessage,
        )
        from mcp_server_langgraph.notifications.push_sender import PushMessage

        redis = AsyncMock()
        redis.lpush = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        message = PushMessage(title="Test", body="Test message")
        queued = await queue.enqueue(
            message=message,
            subscription_endpoint="https://push.example.com/abc123",
            user_id="user-1",
        )

        assert queued.message_id is not None
        assert queued.message == message
        assert queued.subscription_endpoint == "https://push.example.com/abc123"
        assert queued.user_id == "user-1"
        redis.lpush.assert_called_once()
        redis.expire.assert_called_once_with("push:queue", 3600)

    @pytest.mark.asyncio
    async def test_enqueue_message_serializes_correctly(self) -> None:
        """Test that message is serialized to JSON correctly."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
        )
        from mcp_server_langgraph.notifications.push_sender import PushMessage

        redis = AsyncMock()
        captured_data = None

        async def capture_lpush(key: str, data: str) -> int:
            nonlocal captured_data
            captured_data = data
            return 1

        redis.lpush = AsyncMock(side_effect=capture_lpush)
        redis.expire = AsyncMock(return_value=True)

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        message = PushMessage(
            title="Alert",
            body="Critical alert",
            tag="alert-123",
            data={"alert_id": "123"},
        )
        await queue.enqueue(
            message=message,
            subscription_endpoint="https://push.example.com/xyz",
            user_id="admin-1",
        )

        assert captured_data is not None
        parsed = json.loads(captured_data)
        assert parsed["message"]["title"] == "Alert"
        assert parsed["message"]["body"] == "Critical alert"
        assert parsed["message"]["tag"] == "alert-123"
        assert parsed["subscription_endpoint"] == "https://push.example.com/xyz"
        assert parsed["user_id"] == "admin-1"

    @pytest.mark.asyncio
    async def test_enqueue_respects_max_queue_size(self) -> None:
        """Test that queue enforces maximum size limit."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
            QueueFullError,
        )
        from mcp_server_langgraph.notifications.push_sender import PushMessage

        redis = AsyncMock()
        redis.llen = AsyncMock(return_value=10000)  # At max
        redis.lpush = AsyncMock(return_value=10001)
        redis.expire = AsyncMock(return_value=True)

        queue = PushFallbackQueue(
            redis=redis,
            queue_key="push:queue",
            ttl_seconds=3600,
            max_size=10000,
        )

        message = PushMessage(title="Test", body="Test")

        with pytest.raises(QueueFullError) as exc_info:
            await queue.enqueue(
                message=message,
                subscription_endpoint="https://push.example.com/xyz",
            )

        assert "Queue full" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_fallback_queue")
class TestPushFallbackQueueDequeue:
    """Tests for dequeueing messages from the fallback queue."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dequeue_returns_message_from_redis(self) -> None:
        """Test that dequeue retrieves message from Redis."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
        )

        redis = AsyncMock()
        stored_message = json.dumps({
            "message_id": "msg-123",
            "message": {"title": "Test", "body": "Hello"},
            "subscription_endpoint": "https://push.example.com/abc",
            "user_id": "user-1",
            "enqueued_at": datetime.now(UTC).isoformat(),
            "retry_count": 0,
        })
        redis.rpop = AsyncMock(return_value=stored_message)

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        queued = await queue.dequeue()

        assert queued is not None
        assert queued.message_id == "msg-123"
        assert queued.message.title == "Test"
        assert queued.message.body == "Hello"
        assert queued.subscription_endpoint == "https://push.example.com/abc"
        redis.rpop.assert_called_once_with("push:queue")

    @pytest.mark.asyncio
    async def test_dequeue_returns_none_when_empty(self) -> None:
        """Test that dequeue returns None when queue is empty."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
        )

        redis = AsyncMock()
        redis.rpop = AsyncMock(return_value=None)

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        queued = await queue.dequeue()

        assert queued is None

    @pytest.mark.asyncio
    async def test_dequeue_batch_returns_multiple_messages(self) -> None:
        """Test that dequeue_batch retrieves multiple messages."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
        )

        redis = AsyncMock()
        messages = [
            json.dumps({
                "message_id": f"msg-{i}",
                "message": {"title": f"Test {i}", "body": f"Body {i}"},
                "subscription_endpoint": f"https://push.example.com/{i}",
                "user_id": "user-1",
                "enqueued_at": datetime.now(UTC).isoformat(),
                "retry_count": 0,
            })
            for i in range(5)
        ]

        # Mock rpop to return messages one at a time
        redis.rpop = AsyncMock(side_effect=messages + [None])

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        batch = await queue.dequeue_batch(max_count=10)

        assert len(batch) == 5
        assert batch[0].message_id == "msg-0"
        assert batch[4].message_id == "msg-4"


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_fallback_queue")
class TestPushFallbackQueueRetry:
    """Tests for retry logic in the fallback queue."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_requeue_increments_retry_count(self) -> None:
        """Test that requeue increments the retry count."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
            QueuedMessage,
        )
        from mcp_server_langgraph.notifications.push_sender import PushMessage

        redis = AsyncMock()
        redis.lpush = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        original = QueuedMessage(
            message_id="msg-123",
            message=PushMessage(title="Test", body="Body"),
            subscription_endpoint="https://push.example.com/abc",
            user_id="user-1",
            enqueued_at=datetime.now(UTC),
            retry_count=2,
        )

        requeued = await queue.requeue(original)

        assert requeued.retry_count == 3
        assert requeued.message_id == "msg-123"

    @pytest.mark.asyncio
    async def test_requeue_fails_after_max_retries(self) -> None:
        """Test that requeue fails after max retry attempts."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            MaxRetriesExceededError,
            PushFallbackQueue,
            QueuedMessage,
        )
        from mcp_server_langgraph.notifications.push_sender import PushMessage

        redis = AsyncMock()

        queue = PushFallbackQueue(
            redis=redis,
            queue_key="push:queue",
            ttl_seconds=3600,
            max_retries=3,
        )

        original = QueuedMessage(
            message_id="msg-123",
            message=PushMessage(title="Test", body="Body"),
            subscription_endpoint="https://push.example.com/abc",
            user_id="user-1",
            enqueued_at=datetime.now(UTC),
            retry_count=3,  # At max
        )

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            await queue.requeue(original)

        assert "msg-123" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_fallback_queue")
class TestPushFallbackQueueMetrics:
    """Tests for queue metrics and monitoring."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_queue_length(self) -> None:
        """Test getting current queue length."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
        )

        redis = AsyncMock()
        redis.llen = AsyncMock(return_value=42)

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        length = await queue.get_length()

        assert length == 42
        redis.llen.assert_called_once_with("push:queue")

    @pytest.mark.asyncio
    async def test_clear_queue(self) -> None:
        """Test clearing the entire queue."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
        )

        redis = AsyncMock()
        redis.delete = AsyncMock(return_value=1)

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        deleted = await queue.clear()

        assert deleted is True
        redis.delete.assert_called_once_with("push:queue")


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_fallback_queue")
class TestPushFallbackQueueIntegration:
    """Integration-style unit tests for the fallback queue."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_enqueue_dequeue_roundtrip(self) -> None:
        """Test that a message survives enqueue/dequeue roundtrip."""
        from mcp_server_langgraph.notifications.push_fallback_queue import (
            PushFallbackQueue,
        )
        from mcp_server_langgraph.notifications.push_sender import PushMessage

        # Simulate Redis with in-memory list
        queue_data: list[str] = []

        async def mock_lpush(key: str, data: str) -> int:
            queue_data.insert(0, data)
            return len(queue_data)

        async def mock_rpop(key: str) -> str | None:
            if queue_data:
                return queue_data.pop()
            return None

        redis = AsyncMock()
        redis.lpush = AsyncMock(side_effect=mock_lpush)
        redis.rpop = AsyncMock(side_effect=mock_rpop)
        redis.expire = AsyncMock(return_value=True)
        redis.llen = AsyncMock(side_effect=lambda k: len(queue_data))

        queue = PushFallbackQueue(redis=redis, queue_key="push:queue", ttl_seconds=3600)

        # Enqueue
        original_message = PushMessage(
            title="Critical Alert",
            body="Server is down!",
            tag="alert-critical-1",
            data={"alert_id": "abc-123", "severity": "critical"},
            actions=[{"action": "view", "title": "View"}],
        )

        queued = await queue.enqueue(
            message=original_message,
            subscription_endpoint="https://fcm.googleapis.com/fcm/send/abc",
            user_id="admin-1",
        )

        assert await queue.get_length() == 1

        # Dequeue
        dequeued = await queue.dequeue()

        assert dequeued is not None
        assert dequeued.message.title == "Critical Alert"
        assert dequeued.message.body == "Server is down!"
        assert dequeued.message.tag == "alert-critical-1"
        assert dequeued.message.data == {"alert_id": "abc-123", "severity": "critical"}
        assert dequeued.subscription_endpoint == "https://fcm.googleapis.com/fcm/send/abc"
        assert dequeued.user_id == "admin-1"
        assert await queue.get_length() == 0
