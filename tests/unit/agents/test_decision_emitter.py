"""
Unit tests for DecisionEmitter.

TDD RED Phase: Tests for the decision trace emitter that captures agent decisions.

Key Features Tested:
- Singleton pattern with start/stop lifecycle
- Feature flag gating (enable_context_graph)
- Sampling rate support
- Sequence number generation per session
- Async queue for non-blocking persistence
- OTEL correlation (trace_id, span_id)
- Field truncation (query, rationale)
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_decision_emitter")
class TestDecisionEmitterBasics:
    """Tests for DecisionEmitter basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emitter_accepts_repository(self) -> None:
        """DecisionEmitter should accept a repository."""
        from mcp_server_langgraph.agents.decision_emitter import DecisionEmitter

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        assert emitter._repository is mock_repo

    def test_emitter_has_start_method(self) -> None:
        """DecisionEmitter should have start method."""
        from mcp_server_langgraph.agents.decision_emitter import DecisionEmitter

        assert hasattr(DecisionEmitter, "start")

    def test_emitter_has_stop_method(self) -> None:
        """DecisionEmitter should have stop method."""
        from mcp_server_langgraph.agents.decision_emitter import DecisionEmitter

        assert hasattr(DecisionEmitter, "stop")

    def test_emitter_has_emit_method(self) -> None:
        """DecisionEmitter should have emit method."""
        from mcp_server_langgraph.agents.decision_emitter import DecisionEmitter

        assert hasattr(DecisionEmitter, "emit")


@pytest.mark.xdist_group(name="test_decision_emitter")
class TestDecisionContext:
    """Tests for DecisionContext dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_decision_context_fields(self) -> None:
        """DecisionContext should have required fields."""
        from mcp_server_langgraph.agents.decision_emitter import DecisionContext

        ctx = DecisionContext(
            run_id="run-abc123",
            session_id="session-456",
            workflow_id="workflow-789",
            project_id="project:backend",
            organization_id="org:acme",
            user_id="user:alice",
        )

        assert ctx.run_id == "run-abc123"
        assert ctx.session_id == "session-456"
        assert ctx.workflow_id == "workflow-789"
        assert ctx.project_id == "project:backend"
        assert ctx.organization_id == "org:acme"
        assert ctx.user_id == "user:alice"

    def test_decision_context_optional_fields(self) -> None:
        """DecisionContext should allow None for optional fields."""
        from mcp_server_langgraph.agents.decision_emitter import DecisionContext

        ctx = DecisionContext(
            run_id="run-abc123",
            session_id="session-456",
            workflow_id=None,
            project_id=None,
            organization_id="org:acme",
            user_id="user:alice",
        )

        assert ctx.workflow_id is None
        assert ctx.project_id is None


@pytest.mark.xdist_group(name="test_decision_emitter")
class TestDecisionEmitterEmit:
    """Tests for DecisionEmitter.emit() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_emit_returns_none_when_disabled(self) -> None:
        """emit() should return None when context graph is disabled."""
        from mcp_server_langgraph.agents.decision_emitter import (
            DecisionContext,
            DecisionEmitter,
        )

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        ctx = DecisionContext(
            run_id="run-abc",
            session_id="session-123",
            workflow_id=None,
            project_id=None,
            organization_id="org:acme",
            user_id="user:alice",
        )

        with patch("mcp_server_langgraph.agents.decision_emitter.feature_flags") as mock_flags:
            mock_flags.enable_context_graph = False

            result = await emitter.emit(
                context=ctx,
                decision_type="routing",
                decision_stage="action",
                query_text="How do I deploy?",
                chosen_action="call_deploy_tool",
                confidence=0.95,
                rationale="User wants deployment",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_emit_returns_trace_id_when_enabled(self) -> None:
        """emit() should return trace_id when context graph is enabled."""
        from mcp_server_langgraph.agents.decision_emitter import (
            DecisionContext,
            DecisionEmitter,
        )

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        ctx = DecisionContext(
            run_id="run-abc",
            session_id="session-123",
            workflow_id=None,
            project_id=None,
            organization_id="org:acme",
            user_id="user:alice",
        )

        with patch("mcp_server_langgraph.agents.decision_emitter.feature_flags") as mock_flags:
            mock_flags.enable_context_graph = True
            mock_flags.context_graph_sampling_rate = 1.0
            mock_flags.context_graph_async_persistence = False

            result = await emitter.emit(
                context=ctx,
                decision_type="routing",
                decision_stage="action",
                query_text="How do I deploy?",
                chosen_action="call_deploy_tool",
                confidence=0.95,
                rationale="User wants deployment",
            )

        assert result is not None
        assert isinstance(result, str)
        # Should be a UUID format
        assert len(result) == 36

    @pytest.mark.asyncio
    async def test_emit_truncates_long_query(self) -> None:
        """emit() should truncate query_text to MAX_QUERY_LENGTH."""
        from mcp_server_langgraph.agents.decision_emitter import (
            MAX_QUERY_LENGTH,
            DecisionContext,
            DecisionEmitter,
        )

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        ctx = DecisionContext(
            run_id="run-abc",
            session_id="session-123",
            workflow_id=None,
            project_id=None,
            organization_id="org:acme",
            user_id="user:alice",
        )

        long_query = "x" * 1000  # Much longer than MAX_QUERY_LENGTH

        with patch("mcp_server_langgraph.agents.decision_emitter.feature_flags") as mock_flags:
            mock_flags.enable_context_graph = True
            mock_flags.context_graph_sampling_rate = 1.0
            mock_flags.context_graph_async_persistence = False

            await emitter.emit(
                context=ctx,
                decision_type="routing",
                decision_stage="action",
                query_text=long_query,
                chosen_action="test_action",
                confidence=0.9,
                rationale="Test",
            )

        # Verify the truncated query was passed to repository
        call_args = mock_repo.create.call_args[0][0]
        assert len(call_args["query_text"]) == MAX_QUERY_LENGTH

    @pytest.mark.asyncio
    async def test_emit_truncates_long_rationale(self) -> None:
        """emit() should truncate rationale to MAX_RATIONALE_LENGTH."""
        from mcp_server_langgraph.agents.decision_emitter import (
            MAX_RATIONALE_LENGTH,
            DecisionContext,
            DecisionEmitter,
        )

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        ctx = DecisionContext(
            run_id="run-abc",
            session_id="session-123",
            workflow_id=None,
            project_id=None,
            organization_id="org:acme",
            user_id="user:alice",
        )

        long_rationale = "r" * 2000  # Much longer than MAX_RATIONALE_LENGTH

        with patch("mcp_server_langgraph.agents.decision_emitter.feature_flags") as mock_flags:
            mock_flags.enable_context_graph = True
            mock_flags.context_graph_sampling_rate = 1.0
            mock_flags.context_graph_async_persistence = False

            await emitter.emit(
                context=ctx,
                decision_type="routing",
                decision_stage="action",
                query_text="Test query",
                chosen_action="test_action",
                confidence=0.9,
                rationale=long_rationale,
            )

        # Verify the truncated rationale was passed to repository
        call_args = mock_repo.create.call_args[0][0]
        assert len(call_args["rationale"]) == MAX_RATIONALE_LENGTH


@pytest.mark.xdist_group(name="test_decision_emitter")
class TestDecisionEmitterSampling:
    """Tests for sampling rate functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_emit_with_zero_sampling_returns_none(self) -> None:
        """emit() should return None when sampling rate is 0."""
        from mcp_server_langgraph.agents.decision_emitter import (
            DecisionContext,
            DecisionEmitter,
        )

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        ctx = DecisionContext(
            run_id="run-abc",
            session_id="session-123",
            workflow_id=None,
            project_id=None,
            organization_id="org:acme",
            user_id="user:alice",
        )

        with patch("mcp_server_langgraph.agents.decision_emitter.feature_flags") as mock_flags:
            mock_flags.enable_context_graph = True
            mock_flags.context_graph_sampling_rate = 0.0

            result = await emitter.emit(
                context=ctx,
                decision_type="routing",
                decision_stage="action",
                query_text="Test",
                chosen_action="test_action",
                confidence=0.9,
                rationale="Test",
            )

        assert result is None
        mock_repo.create.assert_not_called()


@pytest.mark.xdist_group(name="test_decision_emitter")
class TestDecisionEmitterSequencing:
    """Tests for sequence number generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sequence_numbers_increment_per_session(self) -> None:
        """Sequence numbers should increment per session."""
        from mcp_server_langgraph.agents.decision_emitter import (
            DecisionContext,
            DecisionEmitter,
        )

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        ctx = DecisionContext(
            run_id="run-abc",
            session_id="session-123",
            workflow_id=None,
            project_id=None,
            organization_id="org:acme",
            user_id="user:alice",
        )

        with patch("mcp_server_langgraph.agents.decision_emitter.feature_flags") as mock_flags:
            mock_flags.enable_context_graph = True
            mock_flags.context_graph_sampling_rate = 1.0
            mock_flags.context_graph_async_persistence = False

            # Emit twice for same session
            await emitter.emit(
                context=ctx,
                decision_type="routing",
                decision_stage="action",
                query_text="Query 1",
                chosen_action="action_1",
                confidence=0.9,
                rationale="Rationale 1",
            )
            await emitter.emit(
                context=ctx,
                decision_type="tool_selection",
                decision_stage="action",
                query_text="Query 2",
                chosen_action="action_2",
                confidence=0.85,
                rationale="Rationale 2",
            )

        # Verify sequence numbers
        calls = mock_repo.create.call_args_list
        assert calls[0][0][0]["sequence_number"] == 0
        assert calls[1][0][0]["sequence_number"] == 1


@pytest.mark.xdist_group(name="test_decision_emitter")
class TestDecisionEmitterAsync:
    """Tests for async persistence functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_emit_uses_queue_when_async_enabled(self) -> None:
        """emit() should use queue when async persistence is enabled."""
        from mcp_server_langgraph.agents.decision_emitter import (
            DecisionContext,
            DecisionEmitter,
        )

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        ctx = DecisionContext(
            run_id="run-abc",
            session_id="session-123",
            workflow_id=None,
            project_id=None,
            organization_id="org:acme",
            user_id="user:alice",
        )

        with patch("mcp_server_langgraph.agents.decision_emitter.feature_flags") as mock_flags:
            mock_flags.enable_context_graph = True
            mock_flags.context_graph_sampling_rate = 1.0
            mock_flags.context_graph_async_persistence = True

            await emitter.emit(
                context=ctx,
                decision_type="routing",
                decision_stage="action",
                query_text="Test",
                chosen_action="test_action",
                confidence=0.9,
                rationale="Test",
            )

        # When async is enabled, create should not be called directly
        mock_repo.create.assert_not_called()
        # Queue should have the item
        assert emitter._queue.qsize() == 1


@pytest.mark.xdist_group(name="test_decision_emitter")
class TestDecisionEmitterLifecycle:
    """Tests for start/stop lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_start_creates_worker_task(self) -> None:
        """start() should create a background worker task."""
        from mcp_server_langgraph.agents.decision_emitter import DecisionEmitter

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        await emitter.start()

        try:
            assert emitter._worker_task is not None
            assert not emitter._worker_task.done()
        finally:
            await emitter.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_worker_task(self) -> None:
        """stop() should cancel the worker task."""
        from mcp_server_langgraph.agents.decision_emitter import DecisionEmitter

        mock_repo = AsyncMock(return_value=None)
        emitter = DecisionEmitter(repository=mock_repo)

        await emitter.start()
        await emitter.stop()

        assert emitter._worker_task is None or emitter._worker_task.done()


@pytest.mark.xdist_group(name="test_decision_emitter")
class TestDecisionEmitterConstants:
    """Tests for module constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_max_query_length_defined(self) -> None:
        """MAX_QUERY_LENGTH should be defined."""
        from mcp_server_langgraph.agents.decision_emitter import MAX_QUERY_LENGTH

        assert MAX_QUERY_LENGTH == 500

    def test_max_rationale_length_defined(self) -> None:
        """MAX_RATIONALE_LENGTH should be defined."""
        from mcp_server_langgraph.agents.decision_emitter import MAX_RATIONALE_LENGTH

        assert MAX_RATIONALE_LENGTH == 1000
