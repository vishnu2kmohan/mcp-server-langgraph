"""
Push Subscription Cleanup Job.

Background job that periodically cleans up expired and stale push subscriptions:
- Removes subscriptions with explicit expiry dates that have passed
- Removes subscriptions that haven't been used for a configurable number of days
- Records metrics for cleanup operations

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta

from mcp_server_langgraph.notifications.push_metrics import (
    record_cleanup_run,
    update_active_subscriptions,
)
from mcp_server_langgraph.notifications.push_store import PushSubscriptionStore

logger = logging.getLogger(__name__)


class SubscriptionCleanupJob:
    """
    Background job for cleaning up expired push subscriptions.

    Runs periodically to remove:
    - Subscriptions with expires_at in the past
    - Subscriptions that haven't been used for stale_days

    Usage:
        store = InMemoryPushSubscriptionStore()
        cleanup_job = SubscriptionCleanupJob(store)
        cleanup_job.start_background_cleanup()
        # ... on shutdown:
        cleanup_job.stop_background_cleanup()
    """

    def __init__(
        self,
        store: PushSubscriptionStore,
        interval_seconds: int = 3600,  # 1 hour default
        stale_days: int = 90,  # Consider stale after 90 days of no use
    ) -> None:
        """
        Initialize the cleanup job.

        Args:
            store: Push subscription store to clean up.
            interval_seconds: Seconds between cleanup runs.
            stale_days: Days of inactivity before marking subscription stale.
        """
        self._store = store
        self._interval_seconds = interval_seconds
        self._stale_days = stale_days
        self._running = False
        self._task: asyncio.Task[None] | None = None

    @property
    def interval_seconds(self) -> int:
        """Get the cleanup interval in seconds."""
        return self._interval_seconds

    @property
    def stale_days(self) -> int:
        """Get the stale threshold in days."""
        return self._stale_days

    @property
    def is_running(self) -> bool:
        """Check if the background cleanup is running."""
        return self._running

    async def run_cleanup(self) -> int:
        """
        Run a single cleanup cycle.

        Returns:
            Number of subscriptions cleaned up.
        """
        start_time = time.monotonic()
        cleaned_count = 0

        try:
            now = datetime.now(UTC)
            stale_cutoff = now - timedelta(days=self._stale_days)

            # Get all subscriptions
            all_subs = await self._store.get_all_subscriptions()

            # Identify subscriptions to clean up
            endpoints_to_delete: list[str] = []
            for sub in all_subs:
                should_delete = False

                # Check explicit expiry
                if sub.expires_at is not None and sub.expires_at < now:
                    should_delete = True
                    logger.debug(
                        f"Subscription {sub.endpoint[:40]} expired at {sub.expires_at}"
                    )

                # Check for staleness (last_used_at or updated_at)
                last_activity = sub.last_used_at or sub.updated_at
                if last_activity is not None and last_activity < stale_cutoff:
                    should_delete = True
                    logger.debug(
                        f"Subscription {sub.endpoint[:40]} is stale "
                        f"(last activity: {last_activity})"
                    )

                if should_delete:
                    endpoints_to_delete.append(sub.endpoint)

            # Delete expired/stale subscriptions
            for endpoint in endpoints_to_delete:
                await self._store.delete_subscription(endpoint)
                cleaned_count += 1

            # Update active subscriptions gauge
            remaining_subs = await self._store.get_all_subscriptions()
            update_active_subscriptions(count=len(remaining_subs))

            duration = time.monotonic() - start_time

            if cleaned_count > 0:
                logger.info(
                    f"Cleanup completed: removed {cleaned_count} subscriptions "
                    f"in {duration:.2f}s"
                )
            else:
                logger.debug("Cleanup completed: no subscriptions to remove")

            # Record metrics
            record_cleanup_run(cleaned_count=cleaned_count, duration_seconds=duration)

            return cleaned_count

        except Exception:
            logger.exception("Error during subscription cleanup")
            raise

    def start_background_cleanup(self) -> None:
        """Start the background cleanup task."""
        if self._running:
            logger.warning("Background cleanup already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._background_loop())
        logger.info(
            f"Started background cleanup job (interval: {self._interval_seconds}s, "
            f"stale threshold: {self._stale_days} days)"
        )

    def stop_background_cleanup(self) -> None:
        """Stop the background cleanup task."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None
        logger.info("Stopped background cleanup job")

    async def _background_loop(self) -> None:
        """Background loop that runs cleanup periodically."""
        while self._running:
            try:
                await self.run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in background cleanup loop")

            # Wait for next interval (or until stopped)
            try:
                await asyncio.sleep(self._interval_seconds)
            except asyncio.CancelledError:
                break
