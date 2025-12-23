"""
Push Subscription Store Tests.

TDD tests for the push subscription storage system.

Features:
- Save and retrieve push subscriptions
- Delete subscriptions by endpoint
- Get all subscriptions for a user
- Handle subscription expiry
- Get all admin subscriptions

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from mcp_server_langgraph.notifications.push_store import (
    InMemoryPushSubscriptionStore,
    PushSubscription,
    PushSubscriptionStore,
)

pytestmark = pytest.mark.unit

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_subscription() -> PushSubscription:
    """Create a sample push subscription for testing."""
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
        expires_at=None,
        last_used_at=None,
    )


@pytest.fixture
def store() -> InMemoryPushSubscriptionStore:
    """Create an in-memory store for testing."""
    return InMemoryPushSubscriptionStore()


# =============================================================================
# PushSubscription Model Tests
# =============================================================================


class TestPushSubscription:
    """Tests for the PushSubscription dataclass."""

    def test_create_subscription(self, sample_subscription: PushSubscription) -> None:
        """Test creating a subscription with all fields."""
        assert sample_subscription.user_id == "user-001"
        assert sample_subscription.endpoint == "https://push.example.com/p/abc123"
        assert sample_subscription.p256dh_key == "BGV2vxH1234567890abcdef"
        assert sample_subscription.auth_key == "auth123secret"

    def test_is_expired_when_no_expiration(self, sample_subscription: PushSubscription) -> None:
        """Subscription without expires_at should not be expired."""
        assert not sample_subscription.is_expired()

    def test_is_expired_when_future_expiration(self) -> None:
        """Subscription with future expires_at should not be expired."""
        sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-001",
            endpoint="https://push.example.com/p/abc123",
            p256dh_key="BGV2vxH1234567890abcdef",
            auth_key="auth123secret",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        assert not sub.is_expired()

    def test_is_expired_when_past_expiration(self) -> None:
        """Subscription with past expires_at should be expired."""
        sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-001",
            endpoint="https://push.example.com/p/abc123",
            p256dh_key="BGV2vxH1234567890abcdef",
            auth_key="auth123secret",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert sub.is_expired()


# =============================================================================
# InMemoryPushSubscriptionStore Tests
# =============================================================================


class TestInMemoryPushSubscriptionStore:
    """Tests for the in-memory push subscription store."""

    @pytest.mark.asyncio
    async def test_save_subscription(
        self, store: InMemoryPushSubscriptionStore, sample_subscription: PushSubscription
    ) -> None:
        """Test saving a subscription."""
        await store.save_subscription(sample_subscription)

        # Verify subscription is saved
        result = await store.get_subscriptions_for_user(sample_subscription.user_id)
        assert len(result) == 1
        assert result[0].endpoint == sample_subscription.endpoint

    @pytest.mark.asyncio
    async def test_get_subscriptions_for_user(self, store: InMemoryPushSubscriptionStore) -> None:
        """Test getting all subscriptions for a user."""
        user_id = "user-001"

        # Create multiple subscriptions for the same user
        for i in range(3):
            sub = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                endpoint=f"https://push.example.com/p/device{i}",
                p256dh_key=f"key{i}",
                auth_key=f"auth{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await store.save_subscription(sub)

        # Get subscriptions for user
        result = await store.get_subscriptions_for_user(user_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_subscriptions_for_user_empty(self, store: InMemoryPushSubscriptionStore) -> None:
        """Test getting subscriptions for a user with none."""
        result = await store.get_subscriptions_for_user("nonexistent-user")
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_subscription(
        self, store: InMemoryPushSubscriptionStore, sample_subscription: PushSubscription
    ) -> None:
        """Test deleting a subscription by endpoint."""
        await store.save_subscription(sample_subscription)

        # Delete the subscription
        await store.delete_subscription(sample_subscription.endpoint)

        # Verify it's gone
        result = await store.get_subscriptions_for_user(sample_subscription.user_id)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_subscription(self, store: InMemoryPushSubscriptionStore) -> None:
        """Test deleting a subscription that doesn't exist (should not raise)."""
        # Should not raise
        await store.delete_subscription("https://nonexistent.com/endpoint")

    @pytest.mark.asyncio
    async def test_delete_expired_subscriptions(self, store: InMemoryPushSubscriptionStore) -> None:
        """Test deleting all expired subscriptions."""
        # Create expired subscription
        expired_sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-001",
            endpoint="https://push.example.com/expired",
            p256dh_key="key1",
            auth_key="auth1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        await store.save_subscription(expired_sub)

        # Create non-expired subscription
        valid_sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-001",
            endpoint="https://push.example.com/valid",
            p256dh_key="key2",
            auth_key="auth2",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        await store.save_subscription(valid_sub)

        # Create subscription without expiration
        no_expiry_sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-001",
            endpoint="https://push.example.com/no-expiry",
            p256dh_key="key3",
            auth_key="auth3",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            expires_at=None,
        )
        await store.save_subscription(no_expiry_sub)

        # Delete expired subscriptions
        deleted_count = await store.delete_expired_subscriptions()
        assert deleted_count == 1

        # Verify only valid subscriptions remain
        result = await store.get_subscriptions_for_user("user-001")
        assert len(result) == 2
        endpoints = [s.endpoint for s in result]
        assert "https://push.example.com/valid" in endpoints
        assert "https://push.example.com/no-expiry" in endpoints
        assert "https://push.example.com/expired" not in endpoints

    @pytest.mark.asyncio
    async def test_update_last_used_at(
        self, store: InMemoryPushSubscriptionStore, sample_subscription: PushSubscription
    ) -> None:
        """Test updating the last_used_at timestamp."""
        await store.save_subscription(sample_subscription)
        assert sample_subscription.last_used_at is None

        # Update last used
        new_time = datetime.now(UTC)
        await store.update_last_used(sample_subscription.endpoint, new_time)

        # Verify it's updated
        result = await store.get_subscriptions_for_user(sample_subscription.user_id)
        assert len(result) == 1
        assert result[0].last_used_at == new_time

    @pytest.mark.asyncio
    async def test_get_by_endpoint(self, store: InMemoryPushSubscriptionStore, sample_subscription: PushSubscription) -> None:
        """Test getting a subscription by endpoint."""
        await store.save_subscription(sample_subscription)

        result = await store.get_by_endpoint(sample_subscription.endpoint)
        assert result is not None
        assert result.user_id == sample_subscription.user_id

    @pytest.mark.asyncio
    async def test_get_by_endpoint_not_found(self, store: InMemoryPushSubscriptionStore) -> None:
        """Test getting a subscription by endpoint that doesn't exist."""
        result = await store.get_by_endpoint("https://nonexistent.com/endpoint")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_subscriptions(self, store: InMemoryPushSubscriptionStore) -> None:
        """Test getting all subscriptions."""
        # Create subscriptions for multiple users
        for i in range(5):
            sub = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=f"user-{i % 2}",  # Alternating users
                endpoint=f"https://push.example.com/device{i}",
                p256dh_key=f"key{i}",
                auth_key=f"auth{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await store.save_subscription(sub)

        # Get all subscriptions
        result = await store.get_all_subscriptions()
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_subscription_endpoint_uniqueness(self, store: InMemoryPushSubscriptionStore) -> None:
        """Test that saving a subscription with same endpoint updates existing."""
        endpoint = "https://push.example.com/unique"

        # Create first subscription
        sub1 = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-001",
            endpoint=endpoint,
            p256dh_key="key1",
            auth_key="auth1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(sub1)

        # Create second subscription with same endpoint (different user)
        sub2 = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-002",  # Different user
            endpoint=endpoint,  # Same endpoint
            p256dh_key="key2",
            auth_key="auth2",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(sub2)

        # Should only have one subscription with that endpoint
        result = await store.get_by_endpoint(endpoint)
        assert result is not None
        assert result.user_id == "user-002"  # Should be updated to new user


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestPushSubscriptionStoreProtocol:
    """Verify InMemoryPushSubscriptionStore implements the protocol."""

    def test_implements_protocol(self) -> None:
        """Verify the store implements the protocol interface."""
        store = InMemoryPushSubscriptionStore()
        assert isinstance(store, PushSubscriptionStore)
