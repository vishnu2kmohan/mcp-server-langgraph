"""
PostgresPushSubscriptionStore Unit Tests.

TDD tests for the PostgreSQL-backed push subscription store.

Features tested:
- Save and retrieve subscriptions
- Get subscriptions by user
- Delete subscriptions
- Update last_used_at timestamp
- Delete expired subscriptions
- Get all subscriptions

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.notifications.push_store import (
    PushSubscription,
    PushSubscriptionStore,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.notifications,
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_subscription() -> PushSubscription:
    """Create a sample push subscription."""
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
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock(return_value=None)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def mock_session_maker(mock_session: AsyncMock) -> MagicMock:
    """Create a mock session maker."""
    session_maker = MagicMock()
    session_maker.return_value = mock_session
    return session_maker


# =============================================================================
# PostgresPushSubscriptionStore Class Existence Tests
# =============================================================================


@pytest.mark.xdist_group(name="postgres_push_store")
class TestPostgresPushSubscriptionStoreExists:
    """Tests for PostgresPushSubscriptionStore class existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_postgres_push_store_class_exists(self) -> None:
        """
        GIVEN the push_store module
        WHEN importing PostgresPushSubscriptionStore
        THEN should export the class.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
        )

        assert PostgresPushSubscriptionStore is not None

    def test_postgres_push_store_implements_protocol(self, mock_session_maker: MagicMock) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore instance
        WHEN checking protocol implementation
        THEN should implement PushSubscriptionStore protocol.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
        )

        store = PostgresPushSubscriptionStore(mock_session_maker)
        assert isinstance(store, PushSubscriptionStore)


# =============================================================================
# PostgresPushSubscriptionStore CRUD Tests
# =============================================================================


@pytest.mark.xdist_group(name="postgres_push_store")
class TestPostgresPushSubscriptionStoreCRUD:
    """Tests for CRUD operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_subscription(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
        sample_subscription: PushSubscription,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN saving a subscription
        THEN should execute insert statement.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
        )

        # Mock the execute to return no existing record
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        store = PostgresPushSubscriptionStore(mock_session_maker)
        await store.save_subscription(sample_subscription)

        # Should have called execute (for select) and add (for insert)
        mock_session.execute.assert_called()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_subscriptions_for_user(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore with user subscriptions
        WHEN getting subscriptions for a user
        THEN should return list of subscriptions.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
            PushSubscriptionRecord,
        )

        # Create mock records
        mock_record = MagicMock(spec=PushSubscriptionRecord)
        mock_record.id = str(uuid.uuid4())
        mock_record.user_id = "user-001"
        mock_record.endpoint = "https://push.example.com/p/abc"
        mock_record.p256dh_key = "key123"
        mock_record.auth_key = "auth123"
        mock_record.user_agent = "Chrome"
        mock_record.device_name = "Laptop"
        mock_record.created_at = datetime.now(UTC)
        mock_record.updated_at = datetime.now(UTC)
        mock_record.expires_at = None
        mock_record.last_used_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_session.execute.return_value = mock_result

        store = PostgresPushSubscriptionStore(mock_session_maker)
        subscriptions = await store.get_subscriptions_for_user("user-001")

        assert len(subscriptions) == 1
        assert subscriptions[0].user_id == "user-001"

    @pytest.mark.asyncio
    async def test_delete_subscription(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN deleting a subscription by endpoint
        THEN should execute delete statement.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
        )

        store = PostgresPushSubscriptionStore(mock_session_maker)
        await store.delete_subscription("https://push.example.com/p/abc")

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_used(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN updating last_used_at
        THEN should execute update statement.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
            PushSubscriptionRecord,
        )

        # Mock existing record
        mock_record = MagicMock(spec=PushSubscriptionRecord)
        mock_record.endpoint = "https://push.example.com/p/abc"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result

        store = PostgresPushSubscriptionStore(mock_session_maker)
        await store.update_last_used(
            "https://push.example.com/p/abc",
            datetime.now(UTC),
        )

        # Should have updated the record
        assert mock_record.last_used_at is not None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_subscriptions(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore with multiple subscriptions
        WHEN getting all subscriptions
        THEN should return all subscriptions.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
            PushSubscriptionRecord,
        )

        # Create mock records for different users
        records = []
        for i in range(3):
            mock_record = MagicMock(spec=PushSubscriptionRecord)
            mock_record.id = str(uuid.uuid4())
            mock_record.user_id = f"user-{i}"
            mock_record.endpoint = f"https://push.example.com/p/{i}"
            mock_record.p256dh_key = f"key{i}"
            mock_record.auth_key = f"auth{i}"
            mock_record.user_agent = "Chrome"
            mock_record.device_name = None
            mock_record.created_at = datetime.now(UTC)
            mock_record.updated_at = datetime.now(UTC)
            mock_record.expires_at = None
            mock_record.last_used_at = None
            records.append(mock_record)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = records
        mock_session.execute.return_value = mock_result

        store = PostgresPushSubscriptionStore(mock_session_maker)
        subscriptions = await store.get_all_subscriptions()

        assert len(subscriptions) == 3

    @pytest.mark.asyncio
    async def test_delete_expired_subscriptions(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore with expired subscriptions
        WHEN deleting expired subscriptions
        THEN should return count of deleted subscriptions.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
        )

        # Mock delete result
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        store = PostgresPushSubscriptionStore(mock_session_maker)
        deleted = await store.delete_expired_subscriptions()

        assert deleted == 5
        mock_session.commit.assert_called_once()


# =============================================================================
# PostgresPushSubscriptionStore Edge Cases
# =============================================================================


@pytest.mark.xdist_group(name="postgres_push_store")
class TestPostgresPushSubscriptionStoreEdgeCases:
    """Tests for edge cases and error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_by_endpoint(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN getting subscription by endpoint
        THEN should return the subscription or None.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
            PushSubscriptionRecord,
        )

        mock_record = MagicMock(spec=PushSubscriptionRecord)
        mock_record.id = str(uuid.uuid4())
        mock_record.user_id = "user-001"
        mock_record.endpoint = "https://push.example.com/p/abc"
        mock_record.p256dh_key = "key123"
        mock_record.auth_key = "auth123"
        mock_record.user_agent = None
        mock_record.device_name = None
        mock_record.created_at = datetime.now(UTC)
        mock_record.updated_at = datetime.now(UTC)
        mock_record.expires_at = None
        mock_record.last_used_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result

        store = PostgresPushSubscriptionStore(mock_session_maker)
        subscription = await store.get_by_endpoint("https://push.example.com/p/abc")

        assert subscription is not None
        assert subscription.endpoint == "https://push.example.com/p/abc"

    @pytest.mark.asyncio
    async def test_get_by_endpoint_not_found(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore
        WHEN getting subscription by non-existent endpoint
        THEN should return None.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        store = PostgresPushSubscriptionStore(mock_session_maker)
        subscription = await store.get_by_endpoint("https://nonexistent.example.com")

        assert subscription is None

    @pytest.mark.asyncio
    async def test_save_updates_existing_subscription(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
        sample_subscription: PushSubscription,
    ) -> None:
        """
        GIVEN a PostgresPushSubscriptionStore with existing subscription
        WHEN saving subscription with same endpoint
        THEN should update existing record.
        """
        from mcp_server_langgraph.notifications.push_store import (
            PostgresPushSubscriptionStore,
            PushSubscriptionRecord,
        )

        # Mock existing record
        existing_record = MagicMock(spec=PushSubscriptionRecord)
        existing_record.endpoint = sample_subscription.endpoint

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_record
        mock_session.execute.return_value = mock_result

        store = PostgresPushSubscriptionStore(mock_session_maker)
        await store.save_subscription(sample_subscription)

        # Should not call add (update existing instead)
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()
        # Should have updated the record
        assert existing_record.p256dh_key == sample_subscription.p256dh_key
