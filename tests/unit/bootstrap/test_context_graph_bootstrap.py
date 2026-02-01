"""
Unit tests for Context Graph Bootstrap Module.

TDD RED Phase: Tests for bootstrap/context_graph.py module.

Tests:
- ContextGraphState dataclass
- init_context_graph function
- Feature flag gating
- Component initialization
- Cleanup lifecycle
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_context_graph_bootstrap")
class TestContextGraphState:
    """Tests for ContextGraphState dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_graph_state_has_emitter_field(self) -> None:
        """ContextGraphState should have emitter field."""
        from mcp_server_langgraph.bootstrap.context_graph import ContextGraphState

        state = ContextGraphState()
        assert hasattr(state, "emitter")
        assert state.emitter is None

    def test_context_graph_state_has_repository_field(self) -> None:
        """ContextGraphState should have repository field."""
        from mcp_server_langgraph.bootstrap.context_graph import ContextGraphState

        state = ContextGraphState()
        assert hasattr(state, "repository")
        assert state.repository is None

    def test_context_graph_state_has_retention_task_field(self) -> None:
        """ContextGraphState should have retention_task field."""
        from mcp_server_langgraph.bootstrap.context_graph import ContextGraphState

        state = ContextGraphState()
        assert hasattr(state, "retention_task")
        assert state.retention_task is None

    def test_context_graph_state_has_cleanup_method(self) -> None:
        """ContextGraphState should have cleanup method."""
        from mcp_server_langgraph.bootstrap.context_graph import ContextGraphState

        assert hasattr(ContextGraphState, "cleanup")


@pytest.mark.xdist_group(name="test_context_graph_bootstrap")
class TestInitContextGraph:
    """Tests for init_context_graph function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_context_graph_function_exists(self) -> None:
        """init_context_graph function should exist."""
        from mcp_server_langgraph.bootstrap.context_graph import init_context_graph

        assert callable(init_context_graph)

    @pytest.mark.asyncio
    async def test_init_context_graph_returns_none_when_disabled(self) -> None:
        """init_context_graph should return None when feature flag is disabled."""
        from mcp_server_langgraph.bootstrap.context_graph import init_context_graph

        mock_settings = MagicMock()

        with patch("mcp_server_langgraph.bootstrap.context_graph.feature_flags") as mock_flags:
            mock_flags.enable_context_graph = False

            result = await init_context_graph(mock_settings)

        assert result is None

    @pytest.mark.asyncio
    async def test_init_context_graph_returns_state_when_enabled(self) -> None:
        """init_context_graph should return ContextGraphState when enabled."""
        from mcp_server_langgraph.bootstrap.context_graph import (
            ContextGraphState,
            init_context_graph,
        )

        mock_settings = MagicMock()

        with (
            patch("mcp_server_langgraph.bootstrap.context_graph.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.repositories.decision_trace.PostgresDecisionTraceRepository") as mock_repo_cls,
            patch("mcp_server_langgraph.agents.decision_emitter.DecisionEmitter") as mock_emitter_cls,
            patch(
                "mcp_server_langgraph.schedulers.decision_retention.start_retention_scheduler",
                new_callable=AsyncMock,
            ) as mock_scheduler,
            patch("mcp_server_langgraph.core.dependencies.get_async_session") as mock_session,
        ):
            mock_flags.enable_context_graph = True

            # Mock emitter
            mock_emitter = AsyncMock(return_value=None)
            mock_emitter.start = AsyncMock(return_value=None)
            mock_emitter_cls.return_value = mock_emitter

            # Mock repository
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo

            # Mock scheduler
            mock_task = MagicMock()
            mock_scheduler.return_value = mock_task

            result = await init_context_graph(mock_settings)

        assert result is not None
        assert isinstance(result, ContextGraphState)
        assert result.emitter is mock_emitter
        assert result.repository is mock_repo
        mock_emitter.start.assert_called_once()


@pytest.mark.xdist_group(name="test_context_graph_bootstrap")
class TestContextGraphStateCleanup:
    """Tests for ContextGraphState cleanup lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_stops_emitter(self) -> None:
        """cleanup() should stop the emitter."""
        from mcp_server_langgraph.bootstrap.context_graph import ContextGraphState

        mock_emitter = AsyncMock(return_value=None)
        mock_emitter.stop = AsyncMock(return_value=None)

        state = ContextGraphState(
            emitter=mock_emitter,
            repository=None,
            retention_task=None,
        )

        await state.cleanup()

        mock_emitter.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_cancels_retention_task(self) -> None:
        """cleanup() should cancel the retention task."""
        import asyncio

        from mcp_server_langgraph.bootstrap.context_graph import ContextGraphState

        # Create a real asyncio task that we can cancel
        cancel_event = asyncio.Event()

        async def long_running():
            try:
                await asyncio.sleep(3600)  # Long wait that will be cancelled
            except asyncio.CancelledError:
                cancel_event.set()
                raise

        task = asyncio.create_task(long_running())
        # Let the task start running
        await asyncio.sleep(0)

        state = ContextGraphState(
            emitter=None,
            repository=None,
            retention_task=task,
        )

        await state.cleanup()

        # Verify the task was cancelled
        assert task.cancelled() or cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_cleanup_handles_none_components(self) -> None:
        """cleanup() should handle None components gracefully."""
        from mcp_server_langgraph.bootstrap.context_graph import ContextGraphState

        state = ContextGraphState(
            emitter=None,
            repository=None,
            retention_task=None,
        )

        # Should not raise
        await state.cleanup()


@pytest.mark.xdist_group(name="test_context_graph_bootstrap")
class TestContextGraphExports:
    """Tests for module exports."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_context_graph_state_exported(self) -> None:
        """ContextGraphState should be exported from module."""
        from mcp_server_langgraph.bootstrap import context_graph

        assert hasattr(context_graph, "ContextGraphState")

    def test_init_context_graph_exported(self) -> None:
        """init_context_graph should be exported from module."""
        from mcp_server_langgraph.bootstrap import context_graph

        assert hasattr(context_graph, "init_context_graph")
