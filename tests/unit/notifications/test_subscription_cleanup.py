"""
Push Subscription Cleanup Job Tests.

TDD tests for the background cleanup job that removes expired push subscriptions:
- Cleanup job lifecycle (start, stop)
- Expired subscription detection
- Cleanup metrics recording
- Graceful shutdown

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import asyncio
import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
import uuid

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.notifications,
]


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="test_subscription_cleanup")
class TestSubscriptionCleanupJob:
    """Tests for the push subscription cleanup job."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_cleanup_job_removes_expired_subscriptions(self) -> None:
        """
        GIVEN a subscription store with expired subscriptions
        WHEN the cleanup job runs
        THEN expired subscriptions should be deleted.
        """
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )
        from mcp_server_langgraph.notifications.cleanup import (
            SubscriptionCleanupJob,
        )

        store = InMemoryPushSubscriptionStore()

        # Create an expired subscription
        expired_sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-001",
            endpoint="https://push.example.com/p/expired",
            p256dh_key="key1",
            auth_key="auth1",
            created_at=datetime.now(UTC) - timedelta(days=90),
            updated_at=datetime.now(UTC) - timedelta(days=90),
            expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired
        )
        await store.save_subscription(expired_sub)

        # Create an active subscription
        active_sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-002",
            endpoint="https://push.example.com/p/active",
            p256dh_key="key2",
            auth_key="auth2",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=30),  # Active
        )
        await store.save_subscription(active_sub)

        cleanup_job = SubscriptionCleanupJob(store)

        # Run cleanup
        cleaned_count = await cleanup_job.run_cleanup()

        # Expired subscription should be removed
        assert cleaned_count == 1
        expired = await store.get_by_endpoint(expired_sub.endpoint)
        assert expired is None

        # Active subscription should remain
        active = await store.get_by_endpoint(active_sub.endpoint)
        assert active is not None

    async def test_cleanup_job_records_metrics(self) -> None:
        """
        GIVEN a cleanup job execution
        WHEN subscriptions are cleaned
        THEN metrics should be recorded.
        """
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )
        from mcp_server_langgraph.notifications.cleanup import (
            SubscriptionCleanupJob,
        )

        store = InMemoryPushSubscriptionStore()

        # Create expired subscriptions
        for i in range(3):
            sub = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=f"user-{i:03d}",
                endpoint=f"https://push.example.com/p/expired-{i}",
                p256dh_key=f"key{i}",
                auth_key=f"auth{i}",
                created_at=datetime.now(UTC) - timedelta(days=90),
                updated_at=datetime.now(UTC) - timedelta(days=90),
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
            await store.save_subscription(sub)

        cleanup_job = SubscriptionCleanupJob(store)

        with patch("mcp_server_langgraph.notifications.cleanup.record_cleanup_run") as mock_record:
            await cleanup_job.run_cleanup()

            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[1]["cleaned_count"] == 3
            assert call_args[1]["duration_seconds"] >= 0

    async def test_cleanup_job_handles_empty_store(self) -> None:
        """
        GIVEN an empty subscription store
        WHEN the cleanup job runs
        THEN it should complete without error.
        """
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
        )
        from mcp_server_langgraph.notifications.cleanup import (
            SubscriptionCleanupJob,
        )

        store = InMemoryPushSubscriptionStore()
        cleanup_job = SubscriptionCleanupJob(store)

        cleaned_count = await cleanup_job.run_cleanup()

        assert cleaned_count == 0

    async def test_cleanup_job_removes_stale_subscriptions(self) -> None:
        """
        GIVEN subscriptions that haven't been used for 90+ days
        WHEN the cleanup job runs
        THEN stale subscriptions should be removed.
        """
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )
        from mcp_server_langgraph.notifications.cleanup import (
            SubscriptionCleanupJob,
        )

        store = InMemoryPushSubscriptionStore()

        # Create a stale subscription (no explicit expiry, but not used for 90 days)
        stale_sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id="user-001",
            endpoint="https://push.example.com/p/stale",
            p256dh_key="key1",
            auth_key="auth1",
            created_at=datetime.now(UTC) - timedelta(days=100),
            updated_at=datetime.now(UTC) - timedelta(days=100),
            last_used_at=datetime.now(UTC) - timedelta(days=95),
        )
        await store.save_subscription(stale_sub)

        cleanup_job = SubscriptionCleanupJob(store, stale_days=90)

        cleaned_count = await cleanup_job.run_cleanup()

        assert cleaned_count == 1

    async def test_cleanup_job_updates_active_subscriptions_gauge(self) -> None:
        """
        GIVEN subscriptions in the store
        WHEN the cleanup job runs
        THEN the active subscriptions gauge should be updated.
        """
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
            PushSubscription,
        )
        from mcp_server_langgraph.notifications.cleanup import (
            SubscriptionCleanupJob,
        )

        store = InMemoryPushSubscriptionStore()

        # Create active subscriptions
        for i in range(5):
            sub = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=f"user-{i:03d}",
                endpoint=f"https://push.example.com/p/active-{i}",
                p256dh_key=f"key{i}",
                auth_key=f"auth{i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await store.save_subscription(sub)

        cleanup_job = SubscriptionCleanupJob(store)

        with patch("mcp_server_langgraph.notifications.cleanup.update_active_subscriptions") as mock_update:
            await cleanup_job.run_cleanup()

            mock_update.assert_called_once_with(count=5)


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="test_subscription_cleanup")
class TestBackgroundCleanupTask:
    """Tests for background cleanup task management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_start_background_cleanup_creates_task(self) -> None:
        """
        GIVEN a cleanup job
        WHEN starting background cleanup
        THEN a background task should be created.
        """
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
        )
        from mcp_server_langgraph.notifications.cleanup import (
            SubscriptionCleanupJob,
        )

        store = InMemoryPushSubscriptionStore()
        cleanup_job = SubscriptionCleanupJob(store, interval_seconds=60)

        # Start and immediately stop
        cleanup_job.start_background_cleanup()
        assert cleanup_job.is_running

        cleanup_job.stop_background_cleanup()
        assert not cleanup_job.is_running

    async def test_stop_background_cleanup_graceful_shutdown(self) -> None:
        """
        GIVEN a running background cleanup task
        WHEN stopping the cleanup
        THEN it should stop gracefully.
        """
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
        )
        from mcp_server_langgraph.notifications.cleanup import (
            SubscriptionCleanupJob,
        )

        store = InMemoryPushSubscriptionStore()
        cleanup_job = SubscriptionCleanupJob(store, interval_seconds=1)

        cleanup_job.start_background_cleanup()
        assert cleanup_job.is_running

        # Allow one cleanup cycle
        await asyncio.sleep(0.1)

        # Stop should complete without timeout
        cleanup_job.stop_background_cleanup()
        assert not cleanup_job.is_running

    async def test_cleanup_job_configurable_interval(self) -> None:
        """
        GIVEN a cleanup job with custom interval
        WHEN initialized
        THEN the interval should be set correctly.
        """
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
        )
        from mcp_server_langgraph.notifications.cleanup import (
            SubscriptionCleanupJob,
        )

        store = InMemoryPushSubscriptionStore()

        # Default interval
        job_default = SubscriptionCleanupJob(store)
        assert job_default.interval_seconds == 3600  # 1 hour default

        # Custom interval
        job_custom = SubscriptionCleanupJob(store, interval_seconds=1800)
        assert job_custom.interval_seconds == 1800
