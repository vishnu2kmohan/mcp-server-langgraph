"""
Tests for Push Notification API Endpoints

TDD tests for the push notification subscription endpoints.
Tests cover:
- Subscribe to push notifications
- Unsubscribe from push notifications
- Authentication requirements
"""

import gc

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.app import app

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_subscription():
    """Sample push subscription payload."""
    return {
        "endpoint": "https://fcm.googleapis.com/fcm/send/mock-endpoint",
        "keys": {"p256dh": "mock-p256dh-key", "auth": "mock-auth-key"},
    }


@pytest.mark.xdist_group(name="testnotificationsubscribe")
class TestNotificationSubscribe:
    """Tests for POST /api/v1/notifications/subscribe."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_with_valid_subscription_returns_success(self, client, mock_subscription):
        """Should successfully subscribe to push notifications (legacy endpoint)."""
        # Legacy endpoint uses in-memory storage, no mocking needed
        response = client.post(
            "/api/v1/notifications/subscribe",
            json=mock_subscription,
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "deprecated" in data["message"].lower()  # Legacy endpoint warns about deprecation

    def test_subscribe_missing_endpoint(self, client):
        """Should reject subscription without endpoint."""
        response = client.post(
            "/api/v1/notifications/subscribe",
            json={"keys": {"p256dh": "key", "auth": "auth"}},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 422

    def test_subscribe_missing_keys(self, client):
        """Should reject subscription without keys."""
        response = client.post(
            "/api/v1/notifications/subscribe",
            json={"endpoint": "https://example.com/endpoint"},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 422


@pytest.mark.xdist_group(name="testnotificationunsubscribe")
class TestNotificationUnsubscribe:
    """Tests for POST /api/v1/notifications/unsubscribe."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unsubscribe_with_valid_endpoint_returns_success(self, client):
        """Should successfully unsubscribe from push notifications (legacy endpoint)."""
        # Legacy endpoint uses in-memory storage, no mocking needed
        response = client.post(
            "/api/v1/notifications/unsubscribe",
            json={"endpoint": "https://fcm.googleapis.com/fcm/send/mock-endpoint"},
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deprecated" in data["message"].lower()  # Legacy endpoint warns about deprecation

    def test_unsubscribe_missing_endpoint(self, client):
        """Should reject unsubscribe without endpoint."""
        response = client.post("/api/v1/notifications/unsubscribe", json={}, headers={"Authorization": "Bearer mock-token"})

        assert response.status_code == 422


@pytest.mark.xdist_group(name="testnotificationendpointexists")
class TestNotificationEndpointExists:
    """Tests to verify notification endpoints are registered."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_endpoint_exists(self, client):
        """Should have subscribe endpoint registered."""
        # OPTIONS request should not return 404
        response = client.options("/api/v1/notifications/subscribe")
        assert response.status_code != 404

    def test_unsubscribe_endpoint_exists(self, client):
        """Should have unsubscribe endpoint registered."""
        # OPTIONS request should not return 404
        response = client.options("/api/v1/notifications/unsubscribe")
        assert response.status_code != 404


@pytest.mark.xdist_group(name="testnotificationrbac")
class TestNotificationRBACOwnership:
    """Tests for RBAC ownership checks on push subscriptions.

    Security: Users should only be able to manage their own subscriptions.
    Admins can manage all subscriptions.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_verify_subscription_ownership_function_exists(self):
        """
        GIVEN the notifications module
        WHEN importing verify_subscription_ownership
        THEN should export the ownership check function.
        """
        from mcp_server_langgraph.api.v1.notifications import (
            verify_subscription_ownership,
        )

        assert verify_subscription_ownership is not None
        assert callable(verify_subscription_ownership)

    @pytest.mark.asyncio
    async def test_ownership_check_allows_owner(self):
        """
        GIVEN a subscription owned by user-123
        WHEN user-123 tries to access it
        THEN should allow access (no exception).
        """
        from mcp_server_langgraph.api.v1.notifications import (
            verify_subscription_ownership,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )
        from datetime import datetime, UTC

        store = InMemoryPushSubscriptionStore()
        subscription = PushSubscription(
            id="sub-001",
            user_id="user-123",
            endpoint="https://push.example.com/abc",
            p256dh_key="key",
            auth_key="auth",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(subscription)

        # Should not raise
        await verify_subscription_ownership(
            store=store,
            endpoint="https://push.example.com/abc",
            user_id="user-123",
            is_admin=False,
        )

    @pytest.mark.asyncio
    async def test_ownership_check_denies_non_owner(self):
        """
        GIVEN a subscription owned by user-123
        WHEN user-456 tries to access it
        THEN should raise HTTPException with 403.
        """
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.notifications import (
            verify_subscription_ownership,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )
        from datetime import datetime, UTC

        store = InMemoryPushSubscriptionStore()
        subscription = PushSubscription(
            id="sub-001",
            user_id="user-123",
            endpoint="https://push.example.com/abc",
            p256dh_key="key",
            auth_key="auth",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(subscription)

        with pytest.raises(HTTPException) as exc_info:
            await verify_subscription_ownership(
                store=store,
                endpoint="https://push.example.com/abc",
                user_id="user-456",  # Different user
                is_admin=False,
            )

        assert exc_info.value.status_code == 403
        assert "not authorized" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_ownership_check_allows_admin(self):
        """
        GIVEN a subscription owned by user-123
        WHEN an admin tries to access it
        THEN should allow access (admins can manage all subscriptions).
        """
        from mcp_server_langgraph.api.v1.notifications import (
            verify_subscription_ownership,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )
        from datetime import datetime, UTC

        store = InMemoryPushSubscriptionStore()
        subscription = PushSubscription(
            id="sub-001",
            user_id="user-123",
            endpoint="https://push.example.com/abc",
            p256dh_key="key",
            auth_key="auth",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(subscription)

        # Should not raise - admin can access any subscription
        await verify_subscription_ownership(
            store=store,
            endpoint="https://push.example.com/abc",
            user_id="admin-user",  # Different user but admin
            is_admin=True,
        )

    @pytest.mark.asyncio
    async def test_ownership_check_handles_nonexistent(self):
        """
        GIVEN a non-existent subscription endpoint
        WHEN checking ownership
        THEN should raise HTTPException with 404.
        """
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.notifications import (
            verify_subscription_ownership,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
        )

        store = InMemoryPushSubscriptionStore()

        with pytest.raises(HTTPException) as exc_info:
            await verify_subscription_ownership(
                store=store,
                endpoint="https://nonexistent.example.com",
                user_id="user-123",
                is_admin=False,
            )

        assert exc_info.value.status_code == 404


@pytest.mark.xdist_group(name="testnotificationadmin")
class TestNotificationAdminEndpoints:
    """Tests for admin-only push notification management endpoints."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_admin_function_exists(self):
        """
        GIVEN the notifications module
        WHEN importing is_admin_user
        THEN should export the admin check function.
        """
        from mcp_server_langgraph.api.v1.notifications import is_admin_user

        assert is_admin_user is not None
        assert callable(is_admin_user)

    def test_is_admin_returns_true_for_admin_role(self):
        """
        GIVEN a user with admin role
        WHEN checking is_admin_user
        THEN should return True.
        """
        from mcp_server_langgraph.api.v1.notifications import is_admin_user

        user = {"user_id": "admin-1", "roles": ["admin"]}
        assert is_admin_user(user) is True

    def test_is_admin_returns_false_for_regular_user(self):
        """
        GIVEN a user without admin role
        WHEN checking is_admin_user
        THEN should return False.
        """
        from mcp_server_langgraph.api.v1.notifications import is_admin_user

        user = {"user_id": "user-1", "roles": ["user"]}
        assert is_admin_user(user) is False

    def test_is_admin_returns_false_for_user_without_roles(self):
        """
        GIVEN a user with no roles
        WHEN checking is_admin_user
        THEN should return False.
        """
        from mcp_server_langgraph.api.v1.notifications import is_admin_user

        user = {"user_id": "user-1", "roles": []}
        assert is_admin_user(user) is False

        user_no_roles_key = {"user_id": "user-1"}
        assert is_admin_user(user_no_roles_key) is False


@pytest.mark.xdist_group(name="testnotificationsubscriptionlist")
class TestNotificationSubscriptionListRBAC:
    """Tests for GET /api/v1/notifications/push/subscriptions RBAC.

    Security: Users should only see their own subscriptions.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_subscriptions_returns_only_user_subscriptions(self):
        """
        GIVEN subscriptions for multiple users in the store
        WHEN user-123 requests their subscriptions
        THEN should only return subscriptions owned by user-123.
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.api.v1.notifications import (
            list_user_subscriptions,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )

        store = InMemoryPushSubscriptionStore()

        # Create subscriptions for different users
        sub_user_123 = PushSubscription(
            id="sub-001",
            user_id="user-123",
            endpoint="https://push.example.com/user123",
            p256dh_key="key1",
            auth_key="auth1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        sub_user_456 = PushSubscription(
            id="sub-002",
            user_id="user-456",
            endpoint="https://push.example.com/user456",
            p256dh_key="key2",
            auth_key="auth2",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(sub_user_123)
        await store.save_subscription(sub_user_456)

        # Mock current user as user-123
        current_user = {"user_id": "user-123", "roles": ["user"]}

        # Call the endpoint function directly
        result = await list_user_subscriptions(current_user=current_user, store=store)

        # Should only return user-123's subscription
        assert len(result) == 1
        assert result[0].id == "sub-001"

    @pytest.mark.asyncio
    async def test_list_subscriptions_empty_for_new_user(self):
        """
        GIVEN a user with no subscriptions
        WHEN they request their subscriptions
        THEN should return an empty list.
        """
        from mcp_server_langgraph.api.v1.notifications import (
            list_user_subscriptions,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
        )

        store = InMemoryPushSubscriptionStore()
        current_user = {"user_id": "new-user", "roles": ["user"]}

        result = await list_user_subscriptions(current_user=current_user, store=store)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_subscriptions_truncates_long_endpoints(self):
        """
        GIVEN a subscription with a very long endpoint URL
        WHEN listing subscriptions
        THEN should truncate endpoint to 50 chars + '...'.
        """
        from datetime import UTC, datetime

        from mcp_server_langgraph.api.v1.notifications import (
            list_user_subscriptions,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )

        store = InMemoryPushSubscriptionStore()
        long_endpoint = "https://fcm.googleapis.com/fcm/send/" + "x" * 100

        sub = PushSubscription(
            id="sub-001",
            user_id="user-123",
            endpoint=long_endpoint,
            p256dh_key="key1",
            auth_key="auth1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(sub)

        current_user = {"user_id": "user-123", "roles": ["user"]}
        result = await list_user_subscriptions(current_user=current_user, store=store)

        # Endpoint should be truncated
        assert len(result) == 1
        assert result[0].endpoint.endswith("...")
        assert len(result[0].endpoint) == 53  # 50 chars + "..."


@pytest.mark.xdist_group(name="testnotificationsecurity")
class TestNotificationSecurityHardening:
    """Tests for push notification security hardening.

    Security features:
    - Rate limiting on /push/subscribe endpoint
    - Subscription limit per user (max 5 devices)
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_push_subscribe_rate_limit_configured(self):
        """
        GIVEN the rate limiter configuration
        WHEN checking PATH_RATE_LIMITS
        THEN should have rate limit for /push/subscribe endpoint.
        """
        from mcp_server_langgraph.middleware.rate_limiter import PATH_RATE_LIMITS

        # Should have rate limit for push subscribe
        assert "/api/v1/notifications/push/subscribe" in PATH_RATE_LIMITS
        # Should be reasonably restrictive (10/minute to prevent spam)
        limit = PATH_RATE_LIMITS["/api/v1/notifications/push/subscribe"]
        assert "10/minute" in limit or "5/minute" in limit

    def test_max_subscriptions_per_user_constant_exists(self):
        """
        GIVEN the notifications module
        WHEN importing MAX_SUBSCRIPTIONS_PER_USER
        THEN should exist and be set to a reasonable limit.
        """
        from mcp_server_langgraph.api.v1.notifications import (
            MAX_SUBSCRIPTIONS_PER_USER,
        )

        assert MAX_SUBSCRIPTIONS_PER_USER is not None
        assert isinstance(MAX_SUBSCRIPTIONS_PER_USER, int)
        assert MAX_SUBSCRIPTIONS_PER_USER >= 3  # At least 3 devices
        assert MAX_SUBSCRIPTIONS_PER_USER <= 10  # Not too many

    @pytest.mark.asyncio
    async def test_subscribe_rejects_when_at_max_subscriptions(self):
        """
        GIVEN a user already at MAX_SUBSCRIPTIONS_PER_USER limit
        WHEN they try to subscribe another device
        THEN should raise HTTPException with 429 status.
        """
        from datetime import UTC, datetime
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.notifications import (
            MAX_SUBSCRIPTIONS_PER_USER,
            PushSubscriptionKeys,
            PushSubscriptionRequest,
            subscribe_to_notifications,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )

        store = InMemoryPushSubscriptionStore()

        # Fill up to max subscriptions
        for i in range(MAX_SUBSCRIPTIONS_PER_USER):
            sub = PushSubscription(
                id=f"sub-{i:03d}",
                user_id="user-123",
                endpoint=f"https://push.example.com/device{i}",
                p256dh_key=f"key{i}",
                auth_key=f"auth{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await store.save_subscription(sub)

        # Try to subscribe one more
        current_user = {"user_id": "user-123", "roles": ["user"]}
        new_subscription = PushSubscriptionRequest(
            endpoint="https://push.example.com/new-device",
            keys=PushSubscriptionKeys(p256dh="new-key", auth="new-auth"),
        )
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "TestBrowser/1.0"

        with pytest.raises(HTTPException) as exc_info:
            await subscribe_to_notifications(
                subscription=new_subscription,
                current_user=current_user,
                store=store,
                request=mock_request,
            )

        assert exc_info.value.status_code == 429
        assert "maximum" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_subscribe_allows_when_under_limit(self):
        """
        GIVEN a user with fewer than MAX_SUBSCRIPTIONS_PER_USER subscriptions
        WHEN they subscribe a new device
        THEN should succeed.
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.api.v1.notifications import (
            PushSubscriptionKeys,
            PushSubscriptionRequest,
            subscribe_to_notifications,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
        )

        store = InMemoryPushSubscriptionStore()
        current_user = {"user_id": "user-123", "roles": ["user"]}

        new_subscription = PushSubscriptionRequest(
            endpoint="https://push.example.com/first-device",
            keys=PushSubscriptionKeys(p256dh="key", auth="auth"),
        )
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "TestBrowser/1.0"

        # Should succeed
        result = await subscribe_to_notifications(
            subscription=new_subscription,
            current_user=current_user,
            store=store,
            request=mock_request,
        )

        assert result.success is True
