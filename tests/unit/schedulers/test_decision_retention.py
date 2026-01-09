"""
Unit tests for Decision Retention Scheduler.

TDD RED Phase: Tests for schedulers/decision_retention.py module.

Tests:
- start_retention_scheduler function
- _retention_loop background task
- Feature flag integration
- Repository cleanup calls
"""

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_decision_retention")
class TestDecisionRetentionScheduler:
    """Tests for start_retention_scheduler function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_start_retention_scheduler_exists(self) -> None:
        """start_retention_scheduler function should exist."""
        from mcp_server_langgraph.schedulers.decision_retention import (
            start_retention_scheduler,
        )

        assert callable(start_retention_scheduler)

    @pytest.mark.asyncio
    async def test_start_retention_scheduler_returns_task(self) -> None:
        """start_retention_scheduler should return an asyncio.Task."""
        from mcp_server_langgraph.schedulers.decision_retention import (
            start_retention_scheduler,
        )

        mock_repo = AsyncMock()

        task = await start_retention_scheduler(mock_repo)

        try:
            assert isinstance(task, asyncio.Task)
            assert not task.done()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_start_retention_scheduler_task_has_name(self) -> None:
        """The created task should have name 'decision_retention_scheduler'."""
        from mcp_server_langgraph.schedulers.decision_retention import (
            start_retention_scheduler,
        )

        mock_repo = AsyncMock()

        task = await start_retention_scheduler(mock_repo)

        try:
            assert task.get_name() == "decision_retention_scheduler"
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


@pytest.mark.xdist_group(name="test_decision_retention")
class TestRetentionLoop:
    """Tests for _retention_loop background task."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retention_loop_calls_delete_expired(self) -> None:
        """_retention_loop should call delete_expired on repository."""
        from mcp_server_langgraph.schedulers.decision_retention import _retention_loop

        mock_repo = AsyncMock()
        mock_repo.delete_expired = AsyncMock(return_value=0)

        with (
            patch(
                "mcp_server_langgraph.schedulers.decision_retention.feature_flags"
            ) as mock_flags,
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_flags.context_graph_retention_days = 90

            # Make sleep raise CancelledError after first call to break the loop
            call_count = 0

            async def controlled_sleep(seconds):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call is initial delay
                    return
                # Second call breaks the loop
                raise asyncio.CancelledError()

            mock_sleep.side_effect = controlled_sleep

            with pytest.raises(asyncio.CancelledError):
                await _retention_loop(mock_repo)

        mock_repo.delete_expired.assert_called_once_with(90)

    @pytest.mark.asyncio
    async def test_retention_loop_uses_feature_flag_retention_days(self) -> None:
        """_retention_loop should use context_graph_retention_days from feature flags."""
        from mcp_server_langgraph.schedulers.decision_retention import _retention_loop

        mock_repo = AsyncMock()
        mock_repo.delete_expired = AsyncMock(return_value=10)

        with (
            patch(
                "mcp_server_langgraph.schedulers.decision_retention.feature_flags"
            ) as mock_flags,
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            # Use custom retention days
            mock_flags.context_graph_retention_days = 365

            call_count = 0

            async def controlled_sleep(seconds):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return
                raise asyncio.CancelledError()

            mock_sleep.side_effect = controlled_sleep

            with pytest.raises(asyncio.CancelledError):
                await _retention_loop(mock_repo)

        # Verify the retention days value was passed correctly
        mock_repo.delete_expired.assert_called_once_with(365)

    @pytest.mark.asyncio
    async def test_retention_loop_handles_exceptions(self) -> None:
        """_retention_loop should continue after exceptions."""
        from mcp_server_langgraph.schedulers.decision_retention import _retention_loop

        mock_repo = AsyncMock()
        # First call raises, second succeeds
        mock_repo.delete_expired = AsyncMock(
            side_effect=[Exception("DB error"), 5]
        )

        with (
            patch(
                "mcp_server_langgraph.schedulers.decision_retention.feature_flags"
            ) as mock_flags,
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_flags.context_graph_retention_days = 90

            call_count = 0

            async def controlled_sleep(seconds):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # Initial delay
                    return
                if call_count == 2:
                    # After error, continue
                    return
                # Third call breaks the loop
                raise asyncio.CancelledError()

            mock_sleep.side_effect = controlled_sleep

            with pytest.raises(asyncio.CancelledError):
                await _retention_loop(mock_repo)

        # Should have been called twice (once error, once success)
        assert mock_repo.delete_expired.call_count == 2


@pytest.mark.xdist_group(name="test_decision_retention")
class TestRetentionConstants:
    """Tests for module constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cleanup_interval_defined(self) -> None:
        """CLEANUP_INTERVAL_SECONDS should be defined as 24 hours."""
        from mcp_server_langgraph.schedulers.decision_retention import (
            CLEANUP_INTERVAL_SECONDS,
        )

        assert CLEANUP_INTERVAL_SECONDS == 86400  # 24 hours in seconds


@pytest.mark.xdist_group(name="test_decision_retention")
class TestRetentionExports:
    """Tests for module exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_start_retention_scheduler_exported(self) -> None:
        """start_retention_scheduler should be exported from module."""
        from mcp_server_langgraph.schedulers import decision_retention

        assert hasattr(decision_retention, "start_retention_scheduler")

    def test_retention_loop_exported(self) -> None:
        """_retention_loop should be exported from module (for testing)."""
        from mcp_server_langgraph.schedulers import decision_retention

        assert hasattr(decision_retention, "_retention_loop")
