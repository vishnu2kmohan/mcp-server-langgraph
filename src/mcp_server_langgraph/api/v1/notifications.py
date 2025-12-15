"""
Push Notification API Endpoints

Endpoints for managing Web Push notification subscriptions.
Supports subscribing and unsubscribing to push notifications.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


class PushSubscriptionKeys(BaseModel):
    """Keys for push subscription."""

    p256dh: str = Field(..., description="P-256 public key")
    auth: str = Field(..., description="Authentication secret")


class PushSubscription(BaseModel):
    """Push subscription payload from the browser."""

    endpoint: str = Field(..., description="Push service endpoint URL")
    keys: PushSubscriptionKeys = Field(..., description="Subscription keys")
    expirationTime: int | None = Field(None, description="Optional expiration time")


class UnsubscribeRequest(BaseModel):
    """Request to unsubscribe from push notifications."""

    endpoint: str = Field(..., description="Push service endpoint URL to unsubscribe")


class NotificationResponse(BaseModel):
    """Response for notification operations."""

    success: bool
    message: str


# In-memory storage for subscriptions (in production, use a database)
_subscriptions: dict[str, PushSubscription] = {}


def store_subscription(subscription: PushSubscription) -> bool:
    """Store a push subscription.

    In production, this should persist to a database.
    """
    try:
        _subscriptions[subscription.endpoint] = subscription
        logger.info(f"Stored push subscription: {subscription.endpoint[:50]}...")
        return True
    except Exception as e:
        logger.exception(f"Failed to store subscription: {e}")
        return False


def remove_subscription(endpoint: str) -> bool:
    """Remove a push subscription.

    In production, this should remove from a database.
    """
    try:
        if endpoint in _subscriptions:
            del _subscriptions[endpoint]
            logger.info(f"Removed push subscription: {endpoint[:50]}...")
        return True
    except Exception as e:
        logger.exception(f"Failed to remove subscription: {e}")
        return False


@notifications_router.post("/subscribe")
async def subscribe_to_notifications(
    subscription: PushSubscription,
) -> NotificationResponse:
    """Subscribe to push notifications.

    Registers a push subscription endpoint for receiving notifications.
    The subscription includes the endpoint URL and encryption keys.

    Args:
        subscription: Push subscription details from the browser

    Returns:
        Success status and message
    """
    logger.info(f"Received push subscription request for endpoint: {subscription.endpoint[:50]}...")

    success = store_subscription(subscription)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to store push subscription")

    return NotificationResponse(success=True, message="Successfully subscribed to push notifications")


@notifications_router.post("/unsubscribe")
async def unsubscribe_from_notifications(
    request: UnsubscribeRequest,
) -> NotificationResponse:
    """Unsubscribe from push notifications.

    Removes a push subscription endpoint.

    Args:
        request: Unsubscribe request with endpoint URL

    Returns:
        Success status and message
    """
    logger.info(f"Received push unsubscription request for endpoint: {request.endpoint[:50]}...")

    success = remove_subscription(request.endpoint)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove push subscription")

    return NotificationResponse(success=True, message="Successfully unsubscribed from push notifications")
