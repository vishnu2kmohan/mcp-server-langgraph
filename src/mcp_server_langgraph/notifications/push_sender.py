"""
Push Notification Sender Module.

Service for sending Web Push notifications using VAPID authentication.
Handles sending to users, broadcasting to all, and critical alert notifications.

Features:
- VAPID-authenticated Web Push notifications
- Automatic subscription cleanup on 410 Gone
- Last-used timestamp tracking
- Critical alert formatting

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

if TYPE_CHECKING:

    from mcp_server_langgraph.notifications.push_analytics import (
        PushAnalytics,
    )
    from mcp_server_langgraph.notifications.push_fallback_queue import (
        PushFallbackQueue,
    )
    from mcp_server_langgraph.notifications.push_store import (
        PushSubscription,
        PushSubscriptionStore,
    )
    from mcp_server_langgraph.observability.query.interfaces import Alert

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class PushMessage:
    """
    Push notification message content.

    Follows the Web Push API notification format.

    Attributes:
        title: Notification title.
        body: Notification body text.
        icon: URL to notification icon.
        badge: URL to badge icon (for mobile).
        tag: Tag for grouping similar notifications.
        data: Custom data payload for the notification.
        actions: List of notification actions.
    """

    title: str
    body: str
    icon: str | None = None
    badge: str | None = None
    tag: str | None = None
    data: dict[str, Any] | None = None
    actions: list[dict[str, str]] | None = None

    def to_payload(self) -> dict[str, Any]:
        """
        Convert to JSON-serializable payload.

        Returns:
            Dict suitable for JSON serialization and sending via webpush.
        """
        payload: dict[str, Any] = {
            "title": self.title,
            "body": self.body,
        }

        if self.icon:
            payload["icon"] = self.icon
        if self.badge:
            payload["badge"] = self.badge
        if self.tag:
            payload["tag"] = self.tag
        if self.data:
            payload["data"] = self.data
        if self.actions:
            payload["actions"] = self.actions

        return payload


# =============================================================================
# Push Notification Sender Service
# =============================================================================


class PushNotificationSender:
    """
    Service for sending Web Push notifications.

    Uses VAPID (Voluntary Application Server Identification) for authentication
    with push services.

    Attributes:
        vapid_private_key: VAPID private key (base64 encoded).
        vapid_public_key: VAPID public key (base64 encoded).
        vapid_claims: VAPID claims (must include 'sub' with contact email).
        subscription_store: Store for managing push subscriptions.
    """

    def __init__(
        self,
        vapid_private_key: str,
        vapid_public_key: str,
        vapid_claims: dict[str, str],
        subscription_store: PushSubscriptionStore,
        fallback_queue: PushFallbackQueue | None = None,
        analytics: PushAnalytics | None = None,
    ) -> None:
        """
        Initialize the push notification sender.

        Args:
            vapid_private_key: VAPID private key for signing.
            vapid_public_key: VAPID public key for clients.
            vapid_claims: VAPID claims (must include 'sub').
            subscription_store: Store for push subscriptions.
            fallback_queue: Optional fallback queue for circuit breaker failures.
            analytics: Optional PushAnalytics for recording delivery metrics.
        """
        self._vapid_private_key = vapid_private_key
        self._vapid_public_key = vapid_public_key
        self._vapid_claims = vapid_claims
        self._subscription_store = subscription_store
        self._fallback_queue = fallback_queue
        self._analytics = analytics

    async def send_to_user(
        self,
        user_id: str,
        message: PushMessage,
    ) -> int:
        """
        Send a push notification to all subscriptions for a user.

        Args:
            user_id: The user to send to.
            message: The message to send.

        Returns:
            Number of successful sends.
        """
        subscriptions = await self._subscription_store.get_subscriptions_for_user(
            user_id
        )

        if not subscriptions:
            logger.debug(f"No push subscriptions for user {user_id}")
            return 0

        success_count = 0
        for subscription in subscriptions:
            try:
                if await self._send_webpush(subscription, message, user_id=user_id):
                    success_count += 1
                    # Update last_used_at on success
                    await self._subscription_store.update_last_used(
                        subscription.endpoint, datetime.now(UTC)
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to send push notification: {e}",
                    extra={"user_id": user_id, "endpoint": subscription.endpoint[:50]},
                )

        logger.info(
            f"Sent push notification to user {user_id}: {success_count}/{len(subscriptions)} successful"
        )
        return success_count

    async def send_to_all(
        self,
        message: PushMessage,
    ) -> int:
        """
        Send a push notification to all subscriptions.

        Args:
            message: The message to send.

        Returns:
            Number of successful sends.
        """
        subscriptions = await self._subscription_store.get_all_subscriptions()

        if not subscriptions:
            logger.debug("No push subscriptions to send to")
            return 0

        success_count = 0
        for subscription in subscriptions:
            try:
                if await self._send_webpush(subscription, message):
                    success_count += 1
                    await self._subscription_store.update_last_used(
                        subscription.endpoint, datetime.now(UTC)
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to send push notification: {e}",
                    extra={"endpoint": subscription.endpoint[:50]},
                )

        logger.info(
            f"Sent broadcast push notification: {success_count}/{len(subscriptions)} successful"
        )
        return success_count

    async def send_critical_alert(
        self,
        alert: Alert,
    ) -> int:
        """
        Send a critical alert push notification to all subscribers.

        Formats the alert into a push message with appropriate urgency styling.

        Args:
            alert: The critical alert to notify about.

        Returns:
            Number of successful sends.
        """
        message = PushMessage(
            title=f"Critical: {alert.name}",
            body=alert.message[:200] if alert.message else f"Alert {alert.name} is firing",
            icon="/icons/icon-192.png",
            badge="/icons/badge-72.png",
            tag=f"alert-{alert.alert_id}",
            data={
                "alert_id": alert.alert_id,
                "type": "critical_alert",
                "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
            },
            actions=[
                {"action": "view", "title": "View Alert"},
                {"action": "dismiss", "title": "Dismiss"},
            ],
        )

        logger.info(
            f"Sending critical alert notification for {alert.name}",
            extra={"alert_id": alert.alert_id},
        )

        return await self.send_to_all(message)

    async def _send_webpush(
        self,
        subscription: PushSubscription,
        message: PushMessage,
        user_id: str | None = None,
        notification_id: str | None = None,
    ) -> bool:
        """
        Send a webpush notification to a single subscription.

        This method handles the actual webpush API call and error handling,
        with circuit breaker protection to prevent cascade failures.
        When the circuit is open and a fallback queue is configured,
        messages are queued for later delivery.

        Args:
            subscription: The subscription to send to.
            message: The message to send.
            user_id: Optional user ID for fallback queue tracking.
            notification_id: Optional notification ID for analytics tracking.

        Returns:
            True if the send was successful (or queued), False otherwise.
        """
        import time
        import uuid

        import pybreaker

        # Generate notification ID if not provided
        if notification_id is None:
            notification_id = str(uuid.uuid4())

        # Start timing for latency measurement
        start_time = time.monotonic()

        # Get circuit breaker for webpush service
        circuit_breaker = get_circuit_breaker("webpush")

        # Check if circuit is open - queue or fail fast
        if circuit_breaker.current_state == pybreaker.STATE_OPEN:
            if self._fallback_queue is not None:
                try:
                    await self._fallback_queue.enqueue(
                        message=message,
                        subscription_endpoint=subscription.endpoint,
                        user_id=user_id,
                    )
                    logger.info(
                        "Circuit breaker open, queued notification for later delivery",
                        extra={"endpoint": subscription.endpoint[:50]},
                    )
                    return True  # Queued successfully
                except Exception as e:
                    logger.warning(
                        f"Failed to queue notification: {e}",
                        extra={"endpoint": subscription.endpoint[:50]},
                    )
                    return False
            else:
                logger.warning(
                    "Circuit breaker open for webpush, skipping notification",
                    extra={"endpoint": subscription.endpoint[:50]},
                )
                return False

        try:
            # Import pywebpush here to avoid circular imports and allow mocking
            from pywebpush import webpush  # type: ignore[import-not-found]

            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key,
                },
            }

            payload = json.dumps(message.to_payload())

            # Execute webpush call and record result with circuit breaker
            try:
                webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=self._vapid_private_key,
                    vapid_claims=self._vapid_claims,
                )

                # Calculate latency
                latency_ms = int((time.monotonic() - start_time) * 1000)

                # Record success with circuit breaker
                with circuit_breaker._lock:
                    circuit_breaker._state_storage.increment_counter()
                    for listener in circuit_breaker.listeners:
                        listener.success(circuit_breaker)
                    circuit_breaker.state.on_success()

                # Record analytics if configured
                if self._analytics is not None:
                    from mcp_server_langgraph.notifications.push_analytics import (
                        DeliveryEvent,
                    )

                    await self._analytics.record_delivery(
                        DeliveryEvent(
                            notification_id=notification_id,
                            user_id=user_id or subscription.user_id,
                            status="delivered",
                            timestamp=datetime.now(UTC),
                            latency_ms=latency_ms,
                        )
                    )

                logger.debug(
                    f"Successfully sent push notification to {subscription.endpoint[:50]}..."
                )
                return True

            except Exception as e:
                # Calculate latency for failed attempt
                latency_ms = int((time.monotonic() - start_time) * 1000)

                # Record failure with circuit breaker
                with circuit_breaker._lock:
                    if circuit_breaker.is_system_error(e):
                        circuit_breaker._inc_counter()
                        for listener in circuit_breaker.listeners:  # type: ignore[assignment]
                            listener.failure(circuit_breaker, e)
                        try:
                            circuit_breaker.state.on_failure(e)
                        except pybreaker.CircuitBreakerError:
                            # Circuit just opened
                            logger.warning(
                                "Circuit breaker opened for webpush service",
                                extra={"endpoint": subscription.endpoint[:50]},
                            )

                # Record failed delivery in analytics
                if self._analytics is not None:
                    from mcp_server_langgraph.notifications.push_analytics import (
                        DeliveryEvent,
                    )

                    error_code = str(e)[:100] if e else "unknown_error"
                    await self._analytics.record_delivery(
                        DeliveryEvent(
                            notification_id=notification_id,
                            user_id=user_id or subscription.user_id,
                            status="failed",
                            timestamp=datetime.now(UTC),
                            latency_ms=latency_ms,
                            error_code=error_code,
                        )
                    )

                # Check for 410 Gone (subscription expired)
                error_str = str(e)
                if "410" in error_str or "Gone" in error_str:
                    logger.info(
                        f"Removing expired subscription: {subscription.endpoint[:50]}..."
                    )
                    await self._subscription_store.delete_subscription(
                        subscription.endpoint
                    )
                else:
                    logger.warning(
                        f"WebPush error: {e}",
                        extra={"endpoint": subscription.endpoint[:50]},
                    )
                return False

        except ImportError:
            logger.warning(
                "pywebpush not installed. Install with: pip install pywebpush"
            )
            return False

    async def process_fallback_queue(self, batch_size: int = 100) -> int:
        """
        Process messages from the fallback queue.

        Attempts to send queued messages when the circuit breaker allows.
        Messages that fail are requeued (up to max retries).

        Args:
            batch_size: Maximum number of messages to process in one batch.

        Returns:
            Number of messages successfully sent.
        """
        if self._fallback_queue is None:
            logger.debug("No fallback queue configured, nothing to process")
            return 0

        import pybreaker

        from mcp_server_langgraph.notifications.push_fallback_queue import (
            MaxRetriesExceededError,
        )

        circuit_breaker = get_circuit_breaker("webpush")

        # Don't process if circuit is still open
        if circuit_breaker.current_state == pybreaker.STATE_OPEN:
            logger.debug("Circuit breaker still open, not processing fallback queue")
            return 0

        messages = await self._fallback_queue.dequeue_batch(max_count=batch_size)
        if not messages:
            logger.debug("No messages in fallback queue")
            return 0

        success_count = 0
        for queued in messages:
            # Reconstruct subscription from endpoint
            subscriptions = (
                await self._subscription_store.get_subscriptions_for_user(
                    queued.user_id
                )
                if queued.user_id
                else await self._subscription_store.get_all_subscriptions()
            )

            # Find matching subscription by endpoint
            subscription = next(
                (s for s in subscriptions if s.endpoint == queued.subscription_endpoint),
                None,
            )

            if subscription is None:
                logger.info(
                    f"Subscription no longer exists, dropping queued message {queued.message_id}"
                )
                continue

            try:
                # Try to send (this will check circuit breaker again)
                if await self._send_webpush(
                    subscription, queued.message, user_id=queued.user_id
                ):
                    success_count += 1
                    await self._subscription_store.update_last_used(
                        subscription.endpoint, datetime.now(UTC)
                    )
                else:
                    # Send failed but circuit might have opened - requeue
                    try:
                        await self._fallback_queue.requeue(queued)
                    except MaxRetriesExceededError:
                        logger.warning(
                            f"Message {queued.message_id} exceeded max retries, dropping"
                        )
            except Exception as e:
                logger.warning(
                    f"Error processing queued message {queued.message_id}: {e}"
                )
                try:
                    await self._fallback_queue.requeue(queued)
                except MaxRetriesExceededError:
                    logger.warning(
                        f"Message {queued.message_id} exceeded max retries, dropping"
                    )

        logger.info(
            f"Processed fallback queue: {success_count}/{len(messages)} successful"
        )
        return success_count

    @property
    def fallback_queue(self) -> PushFallbackQueue | None:
        """Get the fallback queue instance."""
        return self._fallback_queue

    @property
    def analytics(self) -> PushAnalytics | None:
        """Get the analytics instance."""
        return self._analytics
