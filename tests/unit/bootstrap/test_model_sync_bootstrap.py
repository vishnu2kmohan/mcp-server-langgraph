"""
Unit tests for Model Sync Bootstrap Module.

TDD RED Phase: Tests for bootstrap/model_sync.py module.

This module initializes the LiteLLM model sync scheduler that periodically
syncs pricing from LiteLLM to the ModelRegistry.

Tests:
- ModelSyncState dataclass
- init_model_sync function
- Feature flag gating
- Scheduler lifecycle
- Cleanup handling

Sprint 1 - Enhanced Model Selector: LiteLLM Dynamic Model Sync
"""

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_model_sync_bootstrap")
class TestModelSyncState:
    """Tests for ModelSyncState dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_sync_state_class_exists(self) -> None:
        """ModelSyncState class should exist in bootstrap.model_sync."""
        from mcp_server_langgraph.bootstrap.model_sync import ModelSyncState

        assert ModelSyncState is not None

    def test_model_sync_state_has_sync_task_field(self) -> None:
        """ModelSyncState should have sync_task field."""
        from mcp_server_langgraph.bootstrap.model_sync import ModelSyncState

        state = ModelSyncState()
        assert hasattr(state, "sync_task")
        assert state.sync_task is None

    def test_model_sync_state_has_sync_instance_field(self) -> None:
        """ModelSyncState should have sync_instance field."""
        from mcp_server_langgraph.bootstrap.model_sync import ModelSyncState

        state = ModelSyncState()
        assert hasattr(state, "sync_instance")
        assert state.sync_instance is None

    def test_model_sync_state_has_cleanup_method(self) -> None:
        """ModelSyncState should have cleanup method."""
        from mcp_server_langgraph.bootstrap.model_sync import ModelSyncState

        state = ModelSyncState()
        assert hasattr(state, "cleanup")
        assert callable(state.cleanup)


@pytest.mark.xdist_group(name="test_model_sync_bootstrap")
class TestInitModelSync:
    """Tests for init_model_sync function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_model_sync_function_exists(self) -> None:
        """init_model_sync function should exist."""
        from mcp_server_langgraph.bootstrap.model_sync import init_model_sync

        assert callable(init_model_sync)

    @pytest.mark.asyncio
    async def test_init_model_sync_returns_none_when_disabled(self) -> None:
        """init_model_sync should return None when feature flag is disabled."""
        from mcp_server_langgraph.bootstrap.model_sync import init_model_sync

        mock_settings = MagicMock()

        with patch("mcp_server_langgraph.bootstrap.model_sync.feature_flags") as mock_flags:
            mock_flags.enable_litellm_model_sync = False

            result = await init_model_sync(mock_settings)

        assert result is None

    @pytest.mark.asyncio
    async def test_init_model_sync_returns_state_when_enabled(self) -> None:
        """init_model_sync should return ModelSyncState when enabled."""
        from mcp_server_langgraph.bootstrap.model_sync import (
            ModelSyncState,
            init_model_sync,
        )

        mock_settings = MagicMock()

        with (
            patch("mcp_server_langgraph.bootstrap.model_sync.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.agents.litellm_model_sync.LiteLLMModelSync") as mock_sync_cls,
            patch(
                "mcp_server_langgraph.agents.litellm_model_sync.start_model_sync_scheduler",
                new_callable=AsyncMock,
            ) as mock_scheduler,
        ):
            mock_flags.enable_litellm_model_sync = True

            # Mock sync instance
            mock_sync = MagicMock()
            mock_sync_cls.return_value = mock_sync

            # Mock scheduler task
            mock_task = MagicMock(spec=asyncio.Task)
            mock_scheduler.return_value = mock_task

            result = await init_model_sync(mock_settings)

        assert result is not None
        assert isinstance(result, ModelSyncState)

    @pytest.mark.asyncio
    async def test_init_model_sync_starts_scheduler(self) -> None:
        """init_model_sync should start the sync scheduler."""
        from mcp_server_langgraph.bootstrap.model_sync import init_model_sync

        mock_settings = MagicMock()

        with (
            patch("mcp_server_langgraph.bootstrap.model_sync.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.agents.litellm_model_sync.LiteLLMModelSync"),
            patch(
                "mcp_server_langgraph.agents.litellm_model_sync.start_model_sync_scheduler",
                new_callable=AsyncMock,
            ) as mock_scheduler,
        ):
            mock_flags.enable_litellm_model_sync = True
            mock_task = MagicMock(spec=asyncio.Task)
            mock_scheduler.return_value = mock_task

            result = await init_model_sync(mock_settings)

        mock_scheduler.assert_called_once()
        assert result.sync_task is mock_task

    @pytest.mark.asyncio
    async def test_init_model_sync_creates_sync_instance(self) -> None:
        """init_model_sync should create LiteLLMModelSync instance."""
        from mcp_server_langgraph.bootstrap.model_sync import init_model_sync

        mock_settings = MagicMock()

        with (
            patch("mcp_server_langgraph.bootstrap.model_sync.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.agents.litellm_model_sync.LiteLLMModelSync") as mock_sync_cls,
            patch(
                "mcp_server_langgraph.agents.litellm_model_sync.start_model_sync_scheduler",
                new_callable=AsyncMock,
            ),
        ):
            mock_flags.enable_litellm_model_sync = True
            mock_sync = MagicMock()
            mock_sync_cls.return_value = mock_sync

            result = await init_model_sync(mock_settings)

        mock_sync_cls.assert_called_once()
        assert result.sync_instance is mock_sync


@pytest.mark.xdist_group(name="test_model_sync_bootstrap")
class TestModelSyncStateCleanup:
    """Tests for ModelSyncState cleanup lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_cancels_sync_task(self) -> None:
        """cleanup() should cancel the sync task."""
        from mcp_server_langgraph.bootstrap.model_sync import ModelSyncState

        # Create a real asyncio task that we can cancel
        cancel_event = asyncio.Event()

        async def long_running():
            try:
                await asyncio.sleep(3600)  # noqa: sleep-duration - Long wait that will be cancelled
            except asyncio.CancelledError:
                cancel_event.set()
                raise

        task = asyncio.create_task(long_running())
        # Let the task start running
        await asyncio.sleep(0)

        state = ModelSyncState(
            sync_task=task,
            sync_instance=None,
        )

        await state.cleanup()

        # Verify the task was cancelled
        assert task.cancelled() or cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_cleanup_handles_none_task(self) -> None:
        """cleanup() should handle None task gracefully."""
        from mcp_server_langgraph.bootstrap.model_sync import ModelSyncState

        state = ModelSyncState(
            sync_task=None,
            sync_instance=None,
        )

        # Should not raise
        await state.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_handles_already_done_task(self) -> None:
        """cleanup() should handle already-done task gracefully."""
        from mcp_server_langgraph.bootstrap.model_sync import ModelSyncState

        # Create a task that completes immediately
        async def quick_task():
            return "done"

        task = asyncio.create_task(quick_task())
        await asyncio.sleep(0)  # Let it complete

        state = ModelSyncState(
            sync_task=task,
            sync_instance=None,
        )

        # Should not raise
        await state.cleanup()


@pytest.mark.xdist_group(name="test_model_sync_bootstrap")
class TestModelSyncExports:
    """Tests for module exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_sync_state_exported(self) -> None:
        """ModelSyncState should be exported from module."""
        from mcp_server_langgraph.bootstrap import model_sync

        assert hasattr(model_sync, "ModelSyncState")

    def test_init_model_sync_exported(self) -> None:
        """init_model_sync should be exported from module."""
        from mcp_server_langgraph.bootstrap import model_sync

        assert hasattr(model_sync, "init_model_sync")


@pytest.mark.xdist_group(name="test_model_sync_bootstrap")
class TestModelSyncBootstrapIntegration:
    """Tests for model sync integration in bootstrap/__init__.py."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_sync_state_exported_from_bootstrap_package(self) -> None:
        """ModelSyncState should be exported from bootstrap package."""
        from mcp_server_langgraph.bootstrap import ModelSyncState

        assert ModelSyncState is not None

    def test_init_model_sync_exported_from_bootstrap_package(self) -> None:
        """init_model_sync should be exported from bootstrap package."""
        from mcp_server_langgraph.bootstrap import init_model_sync

        assert init_model_sync is not None

    def test_app_state_has_model_sync_field(self) -> None:
        """AppState should have model_sync field for ModelSyncState."""
        from mcp_server_langgraph.bootstrap import AppState

        state = AppState()
        assert hasattr(state, "model_sync")
        assert state.model_sync is None
