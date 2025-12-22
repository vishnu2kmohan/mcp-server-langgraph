"""
Push Notification Metrics for Observability.

Provides OpenTelemetry metrics for push notification delivery:
- Notification send success/failure rates
- Delivery latency histogram
- Subscription lifecycle (create, delete, expire)
- Cleanup job performance

These metrics integrate with the existing observability stack.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from opentelemetry import metrics

# Get meter from observability stack
meter = metrics.get_meter(__name__)


# ==============================================================================
# Push Notification Delivery Metrics
# ==============================================================================

push_sent_counter = meter.create_counter(
    name="push.notifications.sent",
    description="Total push notifications sent",
    unit="1",
)

push_latency_histogram = meter.create_histogram(
    name="push.notifications.latency",
    description="Push notification delivery latency in seconds",
    unit="s",
)


# ==============================================================================
# Subscription Lifecycle Metrics
# ==============================================================================

subscription_created_counter = meter.create_counter(
    name="push.subscriptions.created",
    description="Total push subscriptions created",
    unit="1",
)

subscription_deleted_counter = meter.create_counter(
    name="push.subscriptions.deleted",
    description="Total push subscriptions deleted",
    unit="1",
)

subscription_expired_counter = meter.create_counter(
    name="push.subscriptions.expired",
    description="Total push subscriptions expired (410 Gone)",
    unit="1",
)

active_subscriptions_gauge = meter.create_gauge(
    name="push.subscriptions.active",
    description="Current number of active push subscriptions",
    unit="1",
)


# ==============================================================================
# Cleanup Job Metrics
# ==============================================================================

cleanup_runs_counter = meter.create_counter(
    name="push.cleanup.runs",
    description="Total cleanup job executions",
    unit="1",
)

cleanup_duration_histogram = meter.create_histogram(
    name="push.cleanup.duration",
    description="Cleanup job duration in seconds",
    unit="s",
)

subscriptions_cleaned_counter = meter.create_counter(
    name="push.cleanup.subscriptions_cleaned",
    description="Total subscriptions cleaned up by cleanup job",
    unit="1",
)


# ==============================================================================
# Helper Functions
# ==============================================================================


def record_push_sent(
    user_id: str,
    success: bool,
    reason: str | None = None,
) -> None:
    """
    Record a push notification send attempt.

    Args:
        user_id: The user ID the notification was sent to.
        success: Whether the notification was delivered successfully.
        reason: Reason for failure (if success=False).
    """
    labels: dict[str, str] = {
        "status": "success" if success else "failure",
        "user_id": user_id[:8],  # Truncate for cardinality control
    }
    if not success and reason:
        labels["reason"] = reason
    push_sent_counter.add(1, labels)


def record_push_latency(duration_seconds: float) -> None:
    """
    Record push notification delivery latency.

    Args:
        duration_seconds: Time taken to deliver the notification.
    """
    push_latency_histogram.record(duration_seconds)


def record_subscription_created(user_id: str) -> None:
    """
    Record a new push subscription creation.

    Args:
        user_id: The user who created the subscription.
    """
    subscription_created_counter.add(1, {"user_id": user_id[:8]})


def record_subscription_deleted(reason: str) -> None:
    """
    Record a push subscription deletion.

    Args:
        reason: Why the subscription was deleted (user_request, expired, 410_gone).
    """
    subscription_deleted_counter.add(1, {"reason": reason})


def record_subscription_expired() -> None:
    """Record a push subscription that expired (410 Gone from browser)."""
    subscription_expired_counter.add(1)


def update_active_subscriptions(count: int) -> None:
    """
    Update the active subscriptions gauge.

    Args:
        count: Current number of active subscriptions.
    """
    active_subscriptions_gauge.set(count)


def record_cleanup_run(cleaned_count: int, duration_seconds: float) -> None:
    """
    Record a cleanup job execution.

    Args:
        cleaned_count: Number of subscriptions cleaned up.
        duration_seconds: Time taken for the cleanup job.
    """
    cleanup_runs_counter.add(1)
    cleanup_duration_histogram.record(duration_seconds)
    subscriptions_cleaned_counter.add(cleaned_count)
