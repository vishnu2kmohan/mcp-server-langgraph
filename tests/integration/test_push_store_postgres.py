"""
PostgreSQL Integration Tests for Push Subscription Store.

TDD integration tests for PostgresPushSubscriptionStore with real PostgreSQL.
Tests CRUD operations, expiry cleanup, and concurrent access patterns.

Follows memory safety patterns for pytest-xdist.
Uses SQLAlchemy async sessions with test database.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mcp_server_langgraph.notifications.push_store import (
    PostgresPushSubscriptionStore,
    PushSubscription,
    PushSubscriptionStore,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for the module."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _database_available() -> bool:
    """Check if the test database is available."""
    import socket

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "9432"))

    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


@pytest.fixture(scope="module")
async def test_engine():
    """Create a test database engine."""
    if not _database_available():
        pytest.skip("PostgreSQL not available for integration tests")

    # Use test database URL from environment or default
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:9432/agent_studio_test",
    )

    try:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

    except Exception:
        # Try gdpr_test database as fallback
        database_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:9432/gdpr_test",
        )
        try:
            engine = create_async_engine(
                database_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")

    yield engine

    await engine.dispose()


@pytest.fixture(scope="module")
async def setup_database(test_engine):
    """
    Setup push_subscriptions table for testing.

    Handles two scenarios:
    1. Fresh database - creates the table
    2. Existing database (from migrations) - uses existing table
    """
    from mcp_server_langgraph.models.base import Base
    import mcp_server_langgraph.notifications.push_store  # noqa: F401

    tables_created = False

    async with test_engine.begin() as conn:
        # Check if table already exists
        result = await conn.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'push_subscriptions')")
        )
        tables_exist = result.scalar()

        if not tables_exist:
            # Fresh database - create table
            await conn.run_sync(Base.metadata.create_all)
            tables_created = True

    yield

    # Only cleanup if we created the table
    if tables_created:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session_maker(test_engine, setup_database):
    """Create a session maker for the store."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return session_factory


@pytest.fixture
async def store(session_maker):
    """Create a PostgresPushSubscriptionStore for testing."""
    return PostgresPushSubscriptionStore(session_maker)


@pytest.fixture
def sample_subscription() -> PushSubscription:
    """Create a sample push subscription."""
    return PushSubscription(
        id=str(uuid4()),
        user_id=f"user-{uuid4()}",
        endpoint=f"https://push.example.com/p/{uuid4()}",
        p256dh_key=f"BGV2vxH-{uuid4()}",
        auth_key=f"auth-{uuid4()}",
        user_agent="Mozilla/5.0 Chrome/120.0",
        device_name="Work Laptop",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ============================================================================
# Protocol Implementation Tests
# ============================================================================


@pytest.mark.xdist_group(name="push_store_integration")
class TestPostgresPushStoreProtocol:
    """Tests for protocol implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_implements_push_subscription_store_protocol(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore instance
        WHEN checking protocol implementation
        THEN should implement PushSubscriptionStore protocol.
        """
        assert isinstance(store, PushSubscriptionStore)

    async def test_has_required_methods(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore instance
        WHEN checking methods
        THEN should have all required protocol methods.
        """
        assert hasattr(store, "save_subscription")
        assert hasattr(store, "get_subscriptions_for_user")
        assert hasattr(store, "get_all_subscriptions")
        assert hasattr(store, "get_by_endpoint")
        assert hasattr(store, "delete_subscription")
        assert hasattr(store, "delete_expired_subscriptions")
        assert hasattr(store, "update_last_used")


# ============================================================================
# CRUD Tests
# ============================================================================


@pytest.mark.xdist_group(name="push_store_integration")
class TestPostgresPushStoreCRUD:
    """Tests for CRUD operations with real PostgreSQL."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_save_and_retrieve_subscription(self, store, sample_subscription):
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN saving a subscription
        THEN should be retrievable by endpoint.
        """
        await store.save_subscription(sample_subscription)

        # Retrieve by endpoint
        retrieved = await store.get_by_endpoint(sample_subscription.endpoint)

        assert retrieved is not None
        assert retrieved.id == sample_subscription.id
        assert retrieved.user_id == sample_subscription.user_id
        assert retrieved.endpoint == sample_subscription.endpoint
        assert retrieved.p256dh_key == sample_subscription.p256dh_key
        assert retrieved.auth_key == sample_subscription.auth_key
        assert retrieved.user_agent == sample_subscription.user_agent
        assert retrieved.device_name == sample_subscription.device_name

    async def test_get_subscriptions_for_user(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore with multiple subscriptions
        WHEN getting subscriptions for a user
        THEN should return only that user's subscriptions.
        """
        user_id = f"user-multi-{uuid4()}"

        # Create multiple subscriptions for the same user
        for i in range(3):
            subscription = PushSubscription(
                id=str(uuid4()),
                user_id=user_id,
                endpoint=f"https://push.example.com/p/{uuid4()}",
                p256dh_key=f"key-{i}",
                auth_key=f"auth-{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await store.save_subscription(subscription)

        # Create subscription for different user
        other_subscription = PushSubscription(
            id=str(uuid4()),
            user_id=f"other-user-{uuid4()}",
            endpoint=f"https://push.example.com/p/{uuid4()}",
            p256dh_key="other-key",
            auth_key="other-auth",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(other_subscription)

        # Get subscriptions for our user
        user_subscriptions = await store.get_subscriptions_for_user(user_id)

        assert len(user_subscriptions) == 3
        assert all(s.user_id == user_id for s in user_subscriptions)

    async def test_delete_subscription(self, store, sample_subscription):
        """
        GIVEN a PostgresPushSubscriptionStore with a subscription
        WHEN deleting the subscription
        THEN should no longer be retrievable.
        """
        await store.save_subscription(sample_subscription)

        # Verify it exists
        exists = await store.get_by_endpoint(sample_subscription.endpoint)
        assert exists is not None

        # Delete it
        await store.delete_subscription(sample_subscription.endpoint)

        # Verify it's gone
        deleted = await store.get_by_endpoint(sample_subscription.endpoint)
        assert deleted is None

    async def test_update_existing_subscription(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore with an existing subscription
        WHEN saving subscription with same endpoint
        THEN should update the existing record.
        """
        endpoint = f"https://push.example.com/p/{uuid4()}"

        # Create initial subscription
        original = PushSubscription(
            id=str(uuid4()),
            user_id="original-user",
            endpoint=endpoint,
            p256dh_key="original-key",
            auth_key="original-auth",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(original)

        # Update with new subscription (same endpoint)
        updated = PushSubscription(
            id=original.id,  # Keep same ID
            user_id="updated-user",
            endpoint=endpoint,
            p256dh_key="updated-key",
            auth_key="updated-auth",
            created_at=original.created_at,
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(updated)

        # Retrieve and verify update
        retrieved = await store.get_by_endpoint(endpoint)
        assert retrieved is not None
        assert retrieved.p256dh_key == "updated-key"
        assert retrieved.auth_key == "updated-auth"
        assert retrieved.user_id == "updated-user"

    async def test_get_by_endpoint_not_found(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN getting subscription by non-existent endpoint
        THEN should return None.
        """
        result = await store.get_by_endpoint("https://nonexistent.example.com/p/xyz")
        assert result is None


# ============================================================================
# Expiry and Cleanup Tests
# ============================================================================


@pytest.mark.xdist_group(name="push_store_integration")
class TestPostgresPushStoreExpiry:
    """Tests for subscription expiry and cleanup."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_delete_expired_subscriptions(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore with expired subscriptions
        WHEN deleting expired subscriptions
        THEN should delete only expired ones.
        """
        now = datetime.now(UTC)
        test_prefix = f"expiry-test-{uuid4()}"

        # Create expired subscription
        expired = PushSubscription(
            id=str(uuid4()),
            user_id=f"{test_prefix}-expired",
            endpoint=f"https://push.example.com/p/expired-{uuid4()}",
            p256dh_key="expired-key",
            auth_key="expired-auth",
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=30),
            expires_at=now - timedelta(days=1),  # Expired yesterday
        )
        await store.save_subscription(expired)

        # Create valid subscription
        valid = PushSubscription(
            id=str(uuid4()),
            user_id=f"{test_prefix}-valid",
            endpoint=f"https://push.example.com/p/valid-{uuid4()}",
            p256dh_key="valid-key",
            auth_key="valid-auth",
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=30),  # Expires in 30 days
        )
        await store.save_subscription(valid)

        # Create subscription without expiry (never expires)
        no_expiry = PushSubscription(
            id=str(uuid4()),
            user_id=f"{test_prefix}-no-expiry",
            endpoint=f"https://push.example.com/p/no-expiry-{uuid4()}",
            p256dh_key="no-expiry-key",
            auth_key="no-expiry-auth",
            created_at=now,
            updated_at=now,
            expires_at=None,
        )
        await store.save_subscription(no_expiry)

        # Delete expired subscriptions
        deleted_count = await store.delete_expired_subscriptions()

        # Should have deleted at least the expired one
        assert deleted_count >= 1

        # Verify expired is gone
        expired_check = await store.get_by_endpoint(expired.endpoint)
        assert expired_check is None

        # Verify valid is still there
        valid_check = await store.get_by_endpoint(valid.endpoint)
        assert valid_check is not None

        # Verify no-expiry is still there
        no_expiry_check = await store.get_by_endpoint(no_expiry.endpoint)
        assert no_expiry_check is not None

    async def test_update_last_used(self, store, sample_subscription):
        """
        GIVEN a PostgresPushSubscriptionStore with a subscription
        WHEN updating last_used_at
        THEN should persist the timestamp.
        """
        await store.save_subscription(sample_subscription)

        # Update last_used_at
        new_timestamp = datetime.now(UTC)
        await store.update_last_used(sample_subscription.endpoint, new_timestamp)

        # Verify update
        retrieved = await store.get_by_endpoint(sample_subscription.endpoint)
        assert retrieved is not None
        assert retrieved.last_used_at is not None
        # Compare with small tolerance for timestamp precision
        assert abs((retrieved.last_used_at - new_timestamp).total_seconds()) < 1

    async def test_update_last_used_nonexistent(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN updating last_used_at for non-existent endpoint
        THEN should not raise an error.
        """
        # Should not raise
        await store.update_last_used(
            "https://nonexistent.example.com/p/xyz",
            datetime.now(UTC),
        )


# ============================================================================
# Get All Subscriptions Tests
# ============================================================================


@pytest.mark.xdist_group(name="push_store_integration")
class TestPostgresPushStoreGetAll:
    """Tests for get_all_subscriptions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_get_all_subscriptions(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore with multiple subscriptions
        WHEN getting all subscriptions
        THEN should return all subscriptions.
        """
        test_prefix = f"get-all-{uuid4()}"

        # Create subscriptions for different users
        created_endpoints = []
        for i in range(3):
            subscription = PushSubscription(
                id=str(uuid4()),
                user_id=f"{test_prefix}-user-{i}",
                endpoint=f"https://push.example.com/p/{test_prefix}-{i}",
                p256dh_key=f"key-{i}",
                auth_key=f"auth-{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await store.save_subscription(subscription)
            created_endpoints.append(subscription.endpoint)

        # Get all subscriptions
        all_subscriptions = await store.get_all_subscriptions()

        # Should include our subscriptions
        all_endpoints = [s.endpoint for s in all_subscriptions]
        for endpoint in created_endpoints:
            assert endpoint in all_endpoints


# ============================================================================
# Edge Cases and Data Integrity Tests
# ============================================================================


@pytest.mark.xdist_group(name="push_store_integration")
class TestPostgresPushStoreEdgeCases:
    """Tests for edge cases and data integrity."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_subscription_with_long_endpoint(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN saving subscription with very long endpoint
        THEN should handle correctly.
        """
        long_endpoint = f"https://push.example.com/p/{'x' * 500}"

        subscription = PushSubscription(
            id=str(uuid4()),
            user_id="long-endpoint-user",
            endpoint=long_endpoint,
            p256dh_key="key",
            auth_key="auth",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(subscription)

        retrieved = await store.get_by_endpoint(long_endpoint)
        assert retrieved is not None
        assert retrieved.endpoint == long_endpoint

    async def test_subscription_with_special_characters(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN saving subscription with special characters in user_agent
        THEN should handle correctly.
        """
        subscription = PushSubscription(
            id=str(uuid4()),
            user_id="special-chars-user",
            endpoint=f"https://push.example.com/p/{uuid4()}",
            p256dh_key="key",
            auth_key="auth",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) 'quotes' \"double\" <brackets>",
            device_name="Test Device with Unicode: 日本語 🎉",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(subscription)

        retrieved = await store.get_by_endpoint(subscription.endpoint)
        assert retrieved is not None
        assert "quotes" in retrieved.user_agent
        assert "日本語" in retrieved.device_name

    async def test_subscription_with_null_optional_fields(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN saving subscription with None for optional fields
        THEN should handle correctly.
        """
        subscription = PushSubscription(
            id=str(uuid4()),
            user_id="null-fields-user",
            endpoint=f"https://push.example.com/p/{uuid4()}",
            p256dh_key="key",
            auth_key="auth",
            user_agent=None,
            device_name=None,
            expires_at=None,
            last_used_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await store.save_subscription(subscription)

        retrieved = await store.get_by_endpoint(subscription.endpoint)
        assert retrieved is not None
        assert retrieved.user_agent is None
        assert retrieved.device_name is None
        assert retrieved.expires_at is None
        assert retrieved.last_used_at is None

    async def test_concurrent_saves_same_endpoint(self, store):
        """
        GIVEN concurrent save operations for same endpoint
        WHEN both complete
        THEN last write wins (upsert behavior).
        """
        import asyncio

        endpoint = f"https://push.example.com/p/concurrent-{uuid4()}"

        async def save_subscription(key_suffix: str):
            subscription = PushSubscription(
                id=str(uuid4()),
                user_id=f"concurrent-user-{key_suffix}",
                endpoint=endpoint,
                p256dh_key=f"key-{key_suffix}",
                auth_key=f"auth-{key_suffix}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await store.save_subscription(subscription)
            return key_suffix

        # Run saves concurrently
        await asyncio.gather(
            save_subscription("first"),
            save_subscription("second"),
        )

        # One of them should win
        retrieved = await store.get_by_endpoint(endpoint)
        assert retrieved is not None
        assert retrieved.p256dh_key in ["key-first", "key-second"]


# ============================================================================
# Performance Tests (Optional - Skip in CI)
# ============================================================================


@pytest.mark.xdist_group(name="push_store_integration")
@pytest.mark.skipif(
    os.getenv("RUN_PERFORMANCE_TESTS") != "true",
    reason="Performance tests require RUN_PERFORMANCE_TESTS=true",
)
class TestPostgresPushStorePerformance:
    """Performance tests for push subscription store."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_bulk_subscription_insert(self, store):
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN saving many subscriptions
        THEN should complete in reasonable time.
        """
        import time

        user_id = f"bulk-user-{uuid4()}"

        start = time.monotonic()

        for i in range(100):
            subscription = PushSubscription(
                id=str(uuid4()),
                user_id=user_id,
                endpoint=f"https://push.example.com/p/bulk-{uuid4()}",
                p256dh_key=f"key-{i}",
                auth_key=f"auth-{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await store.save_subscription(subscription)

        elapsed = time.monotonic() - start

        # Should complete within 10 seconds
        assert elapsed < 10, f"Bulk insert took too long: {elapsed}s"

        # Verify all were saved
        user_subs = await store.get_subscriptions_for_user(user_id)
        assert len(user_subs) == 100
