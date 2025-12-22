"""
Notifications Module.

Provides real-time notification broadcasting for the Agent Studio frontend.

Features:
- NotificationBroadcaster: WebSocket-based real-time notifications
- NotificationPreferences: User preferences for notification types
- InMemoryPreferencesRepository: Development/test preferences storage
- PushSubscription: Web Push API subscription data
- PushSubscriptionStore: Push subscription persistence protocol
- VAPIDKeyRotator: Automated VAPID key rotation
- PushFallbackQueue: Redis-backed queue for circuit breaker fallback
- PushAnalytics: Delivery and engagement analytics

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
from mcp_server_langgraph.notifications.cleanup import (
    SubscriptionCleanupJob,
)
from mcp_server_langgraph.notifications.preferences import (
    InMemoryPreferencesRepository,
    NotificationPreferences,
    PreferencesRepository,
    RedisPreferencesRepository,
    should_send_notification,
)
from mcp_server_langgraph.notifications.push_analytics import (
    AnalyticsReport,
    AnalyticsStore,
    DeliveryEvent,
    DeliverySummary,
    EngagementEvent,
    EngagementSummary,
    LatencySummary,
    PushAnalytics,
)
from mcp_server_langgraph.notifications.push_fallback_queue import (
    MaxRetriesExceededError,
    PushFallbackQueue,
    QueuedMessage,
    QueueFullError,
)
from mcp_server_langgraph.notifications.push_metrics import (
    record_cleanup_run,
    record_push_latency,
    record_push_sent,
    record_subscription_created,
    record_subscription_deleted,
    record_subscription_expired,
    update_active_subscriptions,
)
from mcp_server_langgraph.notifications.push_sender import (
    PushMessage,
    PushNotificationSender,
)
from mcp_server_langgraph.notifications.push_store import (
    InMemoryPushSubscriptionStore,
    PushSubscription,
    PushSubscriptionStore,
)
from mcp_server_langgraph.notifications.vapid_rotation import (
    InMemoryVAPIDKeyRepository,
    VAPIDKeyPair,
    VAPIDKeyRepository,
    VAPIDKeyRotationService,
)

__all__ = [
    # Broadcasting
    "NotificationBroadcaster",
    # Preferences
    "NotificationPreferences",
    "PreferencesRepository",
    "InMemoryPreferencesRepository",
    "RedisPreferencesRepository",
    "should_send_notification",
    # Push subscription support
    "PushSubscription",
    "PushSubscriptionStore",
    "InMemoryPushSubscriptionStore",
    "PushMessage",
    "PushNotificationSender",
    # VAPID key rotation
    "InMemoryVAPIDKeyRepository",
    "VAPIDKeyPair",
    "VAPIDKeyRepository",
    "VAPIDKeyRotationService",
    # Fallback queue
    "PushFallbackQueue",
    "QueuedMessage",
    "QueueFullError",
    "MaxRetriesExceededError",
    # Analytics
    "PushAnalytics",
    "AnalyticsStore",
    "AnalyticsReport",
    "DeliveryEvent",
    "DeliverySummary",
    "EngagementEvent",
    "EngagementSummary",
    "LatencySummary",
    # Metrics
    "record_cleanup_run",
    "record_push_latency",
    "record_push_sent",
    "record_subscription_created",
    "record_subscription_deleted",
    "record_subscription_expired",
    "update_active_subscriptions",
    # Cleanup
    "SubscriptionCleanupJob",
]
