"""
Push Notification API Endpoints

Endpoints for managing Web Push notification subscriptions.
Supports subscribing and unsubscribing to push notifications.

Features:
- Proper dependency injection for PushSubscriptionStore
- Authentication required for subscription management
- Supports both InMemory (dev) and PostgreSQL (prod) backends

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.notifications.push_store import (
    InMemoryPushSubscriptionStore,
    PushSubscription as PushSubscriptionModel,
    PushSubscriptionStore,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Security Constants
# =============================================================================

# Maximum push subscriptions per user (prevents device spam)
MAX_SUBSCRIPTIONS_PER_USER: int = 5


# =============================================================================
# RBAC Helpers
# =============================================================================


def is_admin_user(current_user: dict[str, Any]) -> bool:
    """
    Check if the current user has admin role.

    Args:
        current_user: User dict from authentication middleware.

    Returns:
        True if user has admin role, False otherwise.
    """
    roles = current_user.get("roles", [])
    return "admin" in roles


async def verify_subscription_ownership(
    store: PushSubscriptionStore,
    endpoint: str,
    user_id: str,
    is_admin: bool,
) -> None:
    """
    Verify that the user owns the subscription or is an admin.

    SECURITY: Prevents users from managing other users' subscriptions.
    Admins can manage all subscriptions.

    Args:
        store: Push subscription store to look up the subscription.
        endpoint: The push service endpoint URL to check.
        user_id: The user ID of the requesting user.
        is_admin: Whether the requesting user has admin role.

    Raises:
        HTTPException: 404 if subscription not found, 403 if not authorized.
    """
    subscription = await store.get_by_endpoint(endpoint)

    if subscription is None:
        logger.warning(
            "Subscription not found for ownership check",
            extra={"endpoint": endpoint[:50], "user_id": user_id},
        )
        raise HTTPException(
            status_code=404,
            detail="Subscription not found",
        )

    # Admins can manage any subscription
    if is_admin:
        return

    # Check ownership
    if subscription.user_id != user_id:
        logger.warning(
            "Unauthorized subscription access attempt",
            extra={
                "endpoint": endpoint[:50],
                "requesting_user": user_id,
                "owner_user": subscription.user_id,
            },
        )
        raise HTTPException(
            status_code=403,
            detail="Not authorized to manage this subscription",
        )

notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


# =============================================================================
# Dependency Injection
# =============================================================================


# Global push subscription store instance (configurable for production)
_push_subscription_store: PushSubscriptionStore | None = None


def get_push_subscription_store() -> PushSubscriptionStore:
    """
    Get the global push subscription store instance.

    In development, uses InMemoryPushSubscriptionStore.
    In production, can be configured to use PostgresPushSubscriptionStore.

    To use PostgreSQL in production, call set_push_subscription_store()
    during application startup with a properly configured store.
    """
    global _push_subscription_store
    if _push_subscription_store is None:
        _push_subscription_store = InMemoryPushSubscriptionStore()
    return _push_subscription_store


def set_push_subscription_store(store: PushSubscriptionStore | None) -> None:
    """
    Set the global push subscription store (for production configuration or testing).

    Args:
        store: PushSubscriptionStore implementation to use, or None to reset.

    Example:
        # In app_factory.py for production
        from mcp_server_langgraph.notifications.push_store import PostgresPushSubscriptionStore
        from mcp_server_langgraph.database.session import get_session_maker

        session_maker = get_session_maker(settings.database_url)
        store = PostgresPushSubscriptionStore(session_maker)
        set_push_subscription_store(store)
    """
    global _push_subscription_store
    _push_subscription_store = store


# Type alias for push subscription store dependency
PushStoreDepends = Annotated[PushSubscriptionStore, Depends(get_push_subscription_store)]

# Type alias for current user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


# =============================================================================
# Request/Response Models
# =============================================================================


class PushSubscriptionKeys(BaseModel):
    """Keys for push subscription."""

    p256dh: str = Field(..., description="P-256 public key")
    auth: str = Field(..., description="Authentication secret")


class PushSubscriptionRequest(BaseModel):
    """Push subscription payload from the browser."""

    endpoint: str = Field(..., description="Push service endpoint URL")
    keys: PushSubscriptionKeys = Field(..., description="Subscription keys")
    expirationTime: int | None = Field(None, description="Optional expiration time (ms)")
    deviceName: str | None = Field(None, description="Optional device name for identification")


class UnsubscribeRequest(BaseModel):
    """Request to unsubscribe from push notifications."""

    endpoint: str = Field(..., description="Push service endpoint URL to unsubscribe")


class NotificationResponse(BaseModel):
    """Response for notification operations."""

    success: bool
    message: str


class SubscriptionInfo(BaseModel):
    """Information about a push subscription."""

    id: str
    endpoint: str
    device_name: str | None
    created_at: str
    last_used_at: str | None


# =============================================================================
# API Endpoints
# =============================================================================


@notifications_router.post("/push/subscribe")
async def subscribe_to_notifications(
    subscription: PushSubscriptionRequest,
    current_user: CurrentUser,
    store: PushStoreDepends,
    request: Request,
) -> NotificationResponse:
    """Subscribe to push notifications.

    Registers a push subscription endpoint for receiving notifications.
    The subscription includes the endpoint URL and encryption keys.
    Requires authentication.

    Args:
        subscription: Push subscription details from the browser
        current_user: Authenticated user making the request
        store: Push subscription store dependency
        request: FastAPI request object for user agent

    Returns:
        Success status and message
    """
    user_id = current_user.get("user_id") or current_user.get("sub", "unknown")
    user_agent = request.headers.get("user-agent", "Unknown")

    logger.info(
        "Received push subscription request",
        extra={
            "user_id": user_id,
            "endpoint": subscription.endpoint[:50],
        },
    )

    # SECURITY: Check subscription limit per user (prevents device spam)
    existing_subscriptions = await store.get_subscriptions_for_user(user_id)
    if len(existing_subscriptions) >= MAX_SUBSCRIPTIONS_PER_USER:
        logger.warning(
            "User exceeded maximum push subscriptions",
            extra={
                "user_id": user_id,
                "current_count": len(existing_subscriptions),
                "max_allowed": MAX_SUBSCRIPTIONS_PER_USER,
            },
        )
        raise HTTPException(
            status_code=429,
            detail=f"Maximum of {MAX_SUBSCRIPTIONS_PER_USER} push subscriptions per user. "
            "Please remove an existing subscription first.",
        )

    # Calculate expiration if provided (ms to datetime)
    expires_at = None
    if subscription.expirationTime:
        expires_at = datetime.fromtimestamp(subscription.expirationTime / 1000, tz=UTC)

    # Create subscription model
    sub = PushSubscriptionModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        endpoint=subscription.endpoint,
        p256dh_key=subscription.keys.p256dh,
        auth_key=subscription.keys.auth,
        user_agent=user_agent,
        device_name=subscription.deviceName,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        expires_at=expires_at,
    )

    try:
        await store.save_subscription(sub)
        logger.info(
            f"Stored push subscription for user {user_id}",
            extra={"subscription_id": sub.id, "endpoint": subscription.endpoint[:50]},
        )
        return NotificationResponse(
            success=True, message="Successfully subscribed to push notifications"
        )
    except Exception as e:
        logger.exception(f"Failed to store subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to store push subscription")


@notifications_router.delete("/push/unsubscribe")
async def unsubscribe_from_notifications(
    request_body: UnsubscribeRequest,
    current_user: CurrentUser,
    store: PushStoreDepends,
) -> NotificationResponse:
    """Unsubscribe from push notifications.

    Removes a push subscription endpoint for the authenticated user.

    Args:
        request_body: Unsubscribe request with endpoint URL
        current_user: Authenticated user making the request
        store: Push subscription store dependency

    Returns:
        Success status and message
    """
    user_id = current_user.get("user_id") or current_user.get("sub", "unknown")
    is_admin = is_admin_user(current_user)

    logger.info(
        "Received push unsubscription request",
        extra={
            "user_id": user_id,
            "endpoint": request_body.endpoint[:50],
        },
    )

    # SECURITY: Verify the user owns the subscription or is an admin
    await verify_subscription_ownership(
        store=store,
        endpoint=request_body.endpoint,
        user_id=user_id,
        is_admin=is_admin,
    )

    try:
        await store.delete_subscription(request_body.endpoint)
        logger.info(
            f"Removed push subscription for user {user_id}",
            extra={"endpoint": request_body.endpoint[:50]},
        )
        return NotificationResponse(
            success=True, message="Successfully unsubscribed from push notifications"
        )
    except Exception as e:
        logger.exception(f"Failed to remove subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove push subscription")


@notifications_router.get("/push/subscriptions")
async def list_user_subscriptions(
    current_user: CurrentUser,
    store: PushStoreDepends,
) -> list[SubscriptionInfo]:
    """List all push subscriptions for the authenticated user.

    Returns:
        List of subscription information for the user
    """
    user_id = current_user.get("user_id") or current_user.get("sub", "unknown")

    subscriptions = await store.get_subscriptions_for_user(user_id)

    return [
        SubscriptionInfo(
            id=sub.id,
            endpoint=sub.endpoint[:50] + "..." if len(sub.endpoint) > 50 else sub.endpoint,
            device_name=sub.device_name,
            created_at=sub.created_at.isoformat() if sub.created_at else "",
            last_used_at=sub.last_used_at.isoformat() if sub.last_used_at else None,
        )
        for sub in subscriptions
    ]


# =============================================================================
# Legacy Endpoints (Deprecated - for backwards compatibility)
# =============================================================================

# Legacy in-memory storage (deprecated)
_legacy_subscriptions: dict[str, PushSubscriptionRequest] = {}


@notifications_router.post("/subscribe")
async def subscribe_legacy(
    subscription: PushSubscriptionRequest,
) -> NotificationResponse:
    """Legacy subscribe endpoint (deprecated).

    Use POST /push/subscribe instead for authenticated subscriptions.
    """
    logger.warning(
        "Using deprecated /subscribe endpoint - use /push/subscribe instead",
        extra={"endpoint": subscription.endpoint[:50]},
    )
    _legacy_subscriptions[subscription.endpoint] = subscription
    return NotificationResponse(
        success=True, message="Subscribed (deprecated - use /push/subscribe)"
    )


@notifications_router.post("/unsubscribe")
async def unsubscribe_legacy(
    request_body: UnsubscribeRequest,
) -> NotificationResponse:
    """Legacy unsubscribe endpoint (deprecated).

    Use DELETE /push/unsubscribe instead for authenticated unsubscription.
    """
    logger.warning(
        "Using deprecated /unsubscribe endpoint - use /push/unsubscribe instead",
        extra={"endpoint": request_body.endpoint[:50]},
    )
    _legacy_subscriptions.pop(request_body.endpoint, None)
    return NotificationResponse(
        success=True, message="Unsubscribed (deprecated - use /push/unsubscribe)"
    )
