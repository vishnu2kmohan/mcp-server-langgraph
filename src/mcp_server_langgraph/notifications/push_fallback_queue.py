"""
Push Notification Fallback Queue Module.

Redis-backed queue for storing push notifications when the circuit breaker is open.
Enables graceful degradation by queuing messages for later delivery.

Features:
- FIFO queue semantics (enqueue at head, dequeue from tail)
- Automatic TTL for queue expiration
- Max queue size enforcement
- Retry count tracking
- Batch dequeue for efficient processing

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from mcp_server_langgraph.notifications.push_sender import PushMessage

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class QueueFullError(Exception):
    """Raised when the queue is at maximum capacity."""

    def __init__(self, current_size: int, max_size: int) -> None:
        self.current_size = current_size
        self.max_size = max_size
        super().__init__(f"Queue full: {current_size}/{max_size}")


class MaxRetriesExceededError(Exception):
    """Raised when a message has exceeded maximum retry attempts."""

    def __init__(self, message_id: str, retry_count: int, max_retries: int) -> None:
        self.message_id = message_id
        self.retry_count = retry_count
        self.max_retries = max_retries
        super().__init__(
            f"Message {message_id} exceeded max retries: {retry_count}/{max_retries}"
        )


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class QueuedMessage:
    """
    A push message queued for later delivery.

    Attributes:
        message_id: Unique identifier for this queued message.
        message: The push message to send.
        subscription_endpoint: Target subscription endpoint.
        user_id: Optional user ID for the subscription owner.
        enqueued_at: When the message was enqueued.
        retry_count: Number of delivery attempts.
    """

    message_id: str
    message: PushMessage
    subscription_endpoint: str
    enqueued_at: datetime
    user_id: str | None = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "message_id": self.message_id,
            "message": self.message.to_payload(),
            "subscription_endpoint": self.subscription_endpoint,
            "user_id": self.user_id,
            "enqueued_at": self.enqueued_at.isoformat(),
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedMessage:
        """Deserialize from dictionary."""
        from mcp_server_langgraph.notifications.push_sender import PushMessage

        message_data = data["message"]
        message = PushMessage(
            title=message_data.get("title", ""),
            body=message_data.get("body", ""),
            icon=message_data.get("icon"),
            badge=message_data.get("badge"),
            tag=message_data.get("tag"),
            data=message_data.get("data"),
            actions=message_data.get("actions"),
        )

        return cls(
            message_id=data["message_id"],
            message=message,
            subscription_endpoint=data["subscription_endpoint"],
            user_id=data.get("user_id"),
            enqueued_at=datetime.fromisoformat(data["enqueued_at"]),
            retry_count=data.get("retry_count", 0),
        )


# =============================================================================
# Fallback Queue Implementation
# =============================================================================


class PushFallbackQueue:
    """
    Redis-backed fallback queue for push notifications.

    When the circuit breaker is open, push notifications are queued here
    for later delivery when the circuit closes.

    Attributes:
        redis: Redis async client.
        queue_key: Redis key for the queue list.
        ttl_seconds: Time-to-live for the queue.
        max_size: Maximum number of messages in queue.
        max_retries: Maximum retry attempts per message.
    """

    def __init__(
        self,
        redis: Redis,
        queue_key: str = "push:fallback:queue",
        ttl_seconds: int = 3600,
        max_size: int = 10000,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the fallback queue.

        Args:
            redis: Redis async client.
            queue_key: Redis key for the queue list.
            ttl_seconds: TTL for queue (default: 1 hour).
            max_size: Max messages in queue (default: 10,000).
            max_retries: Max retry attempts (default: 3).
        """
        self._redis = redis
        self._queue_key = queue_key
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._max_retries = max_retries

    async def enqueue(
        self,
        message: PushMessage,
        subscription_endpoint: str,
        user_id: str | None = None,
    ) -> QueuedMessage:
        """
        Add a message to the fallback queue.

        Args:
            message: The push message to queue.
            subscription_endpoint: Target subscription endpoint.
            user_id: Optional user ID for the subscription owner.

        Returns:
            The queued message with assigned ID.

        Raises:
            QueueFullError: If queue is at maximum capacity.
        """
        # Check queue size
        current_size = await self.get_length()
        if current_size >= self._max_size:
            logger.warning(
                f"Push fallback queue full: {current_size}/{self._max_size}"
            )
            raise QueueFullError(current_size, self._max_size)

        # Create queued message
        queued = QueuedMessage(
            message_id=str(uuid.uuid4()),
            message=message,
            subscription_endpoint=subscription_endpoint,
            user_id=user_id,
            enqueued_at=datetime.now(UTC),
            retry_count=0,
        )

        # Store in Redis
        data = json.dumps(queued.to_dict())
        await self._redis.lpush(self._queue_key, data)  # type: ignore[misc]
        await self._redis.expire(self._queue_key, self._ttl_seconds)

        logger.debug(
            f"Enqueued push message {queued.message_id} for {subscription_endpoint[:50]}..."
        )

        return queued

    async def dequeue(self) -> QueuedMessage | None:
        """
        Remove and return the next message from the queue.

        Uses RPOP for FIFO semantics (oldest message first).

        Returns:
            The next queued message, or None if queue is empty.
        """
        data = await self._redis.rpop(self._queue_key)  # type: ignore[misc]
        if data is None:
            return None

        try:
            parsed = json.loads(data)
            return QueuedMessage.from_dict(parsed)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse queued message: {e}")
            return None

    async def dequeue_batch(self, max_count: int = 100) -> list[QueuedMessage]:
        """
        Remove and return multiple messages from the queue.

        Args:
            max_count: Maximum number of messages to dequeue.

        Returns:
            List of queued messages (may be less than max_count).
        """
        messages: list[QueuedMessage] = []

        for _ in range(max_count):
            msg = await self.dequeue()
            if msg is None:
                break
            messages.append(msg)

        return messages

    async def requeue(self, message: QueuedMessage) -> QueuedMessage:
        """
        Re-add a message to the queue after a failed delivery attempt.

        Increments retry count and checks against max retries.

        Args:
            message: The message to requeue.

        Returns:
            The requeued message with incremented retry count.

        Raises:
            MaxRetriesExceededError: If max retries exceeded.
        """
        if message.retry_count >= self._max_retries:
            logger.warning(
                f"Message {message.message_id} exceeded max retries "
                f"({message.retry_count}/{self._max_retries})"
            )
            raise MaxRetriesExceededError(
                message.message_id,
                message.retry_count,
                self._max_retries,
            )

        # Create updated message with incremented retry count
        requeued = QueuedMessage(
            message_id=message.message_id,
            message=message.message,
            subscription_endpoint=message.subscription_endpoint,
            user_id=message.user_id,
            enqueued_at=message.enqueued_at,
            retry_count=message.retry_count + 1,
        )

        # Store in Redis
        data = json.dumps(requeued.to_dict())
        await self._redis.lpush(self._queue_key, data)  # type: ignore[misc]
        await self._redis.expire(self._queue_key, self._ttl_seconds)

        logger.debug(
            f"Requeued message {requeued.message_id} (retry {requeued.retry_count})"
        )

        return requeued

    async def get_length(self) -> int:
        """
        Get the current number of messages in the queue.

        Returns:
            Number of messages in queue.
        """
        length = await self._redis.llen(self._queue_key)  # type: ignore[misc]
        return int(length) if length else 0

    async def clear(self) -> bool:
        """
        Clear all messages from the queue.

        Returns:
            True if queue was deleted, False if it didn't exist.
        """
        result = await self._redis.delete(self._queue_key)
        logger.info("Cleared push fallback queue")
        return bool(result)

    @property
    def queue_key(self) -> str:
        """Get the Redis key for this queue."""
        return self._queue_key

    @property
    def max_size(self) -> int:
        """Get the maximum queue size."""
        return self._max_size

    @property
    def max_retries(self) -> int:
        """Get the maximum retry count."""
        return self._max_retries
