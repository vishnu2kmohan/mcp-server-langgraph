"""
Unit tests for Conversation Intelligence in StudioOrchestrator.

Tests intent_detect, context_optimize, and goal_track task types.

Sprint 3: Conversation Intelligence
- Intent detection classifies user intent before submit
- Context optimization suggests trimming when approaching token limit
- Goal tracking tracks session goals across multiple messages

TDD: Tests written FIRST before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents]


# =============================================================================
# Intent Detection Tests
# =============================================================================


@pytest.mark.xdist_group(name="conversation_intelligence_intent")
class TestIntentDetect:
    """Test intent_detect task type."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_intent_detect_returns_intent_type(self) -> None:
        """Test that intent_detect returns an intent classification."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        # Mock AIUXService with detect_intent method
        mock_service = MagicMock()
        mock_service.detect_intent = AsyncMock(
            return_value={
                "intent": "code_request",
                "confidence": 0.92,
                "sub_intents": ["generate", "explain"],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="intent_detect",
            user_id="test-user",
            session_id="session-123",
            data={"query": "Can you write a Python function to parse JSON?"},
        )

        results = await orchestrator.execute([task])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result is not None
        assert "intent" in results[0].result
        assert results[0].result["intent"] == "code_request"

    @pytest.mark.asyncio
    async def test_intent_detect_returns_confidence_score(self) -> None:
        """Test that intent_detect includes confidence score."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.detect_intent = AsyncMock(
            return_value={
                "intent": "question",
                "confidence": 0.85,
                "sub_intents": ["clarification"],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="intent_detect",
            user_id="test-user",
            session_id="session-123",
            data={"query": "What is the difference between REST and GraphQL?"},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is True
        assert results[0].result is not None
        assert "confidence" in results[0].result
        assert 0 <= results[0].result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_intent_detect_handles_empty_query(self) -> None:
        """Test that intent_detect handles empty query gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.detect_intent = AsyncMock(
            return_value={
                "intent": "unknown",
                "confidence": 0.0,
                "sub_intents": [],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="intent_detect",
            user_id="test-user",
            session_id="session-123",
            data={"query": ""},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is True


# =============================================================================
# Context Optimization Tests
# =============================================================================


@pytest.mark.xdist_group(name="conversation_intelligence_context")
class TestContextOptimize:
    """Test context_optimize task type."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_context_optimize_returns_suggestions(self) -> None:
        """Test that context_optimize returns optimization suggestions."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.optimize_context = AsyncMock(
            return_value={
                "current_tokens": 120000,
                "max_tokens": 128000,
                "usage_percent": 93.75,
                "suggestions": [
                    {
                        "type": "remove_old_messages",
                        "description": "Remove messages older than 1 hour",
                        "tokens_saved": 25000,
                    },
                    {
                        "type": "summarize_artifacts",
                        "description": "Summarize large code artifacts",
                        "tokens_saved": 15000,
                    },
                ],
                "recommended_action": "remove_old_messages",
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="context_optimize",
            user_id="test-user",
            session_id="session-123",
            data={"current_tokens": 120000, "max_tokens": 128000},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is True
        assert results[0].result is not None
        assert "suggestions" in results[0].result
        assert len(results[0].result["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_context_optimize_returns_token_counts(self) -> None:
        """Test that context_optimize includes token usage information."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.optimize_context = AsyncMock(
            return_value={
                "current_tokens": 50000,
                "max_tokens": 128000,
                "usage_percent": 39.06,
                "suggestions": [],
                "recommended_action": None,
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="context_optimize",
            user_id="test-user",
            session_id="session-123",
            data={"current_tokens": 50000, "max_tokens": 128000},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is True
        assert results[0].result is not None
        assert "current_tokens" in results[0].result
        assert "max_tokens" in results[0].result
        assert "usage_percent" in results[0].result


# =============================================================================
# Goal Tracking Tests
# =============================================================================


@pytest.mark.xdist_group(name="conversation_intelligence_goal")
class TestGoalTrack:
    """Test goal_track task type."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_goal_track_returns_session_goal(self) -> None:
        """Test that goal_track returns the detected session goal."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.track_goal = AsyncMock(
            return_value={
                "primary_goal": "Build a REST API for user authentication",
                "sub_goals": [
                    "Implement JWT token generation",
                    "Create login endpoint",
                    "Add password hashing",
                ],
                "progress_percent": 45,
                "current_focus": "Implement JWT token generation",
                "completed_sub_goals": ["Create login endpoint"],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="goal_track",
            user_id="test-user",
            session_id="session-123",
            data={},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is True
        assert results[0].result is not None
        assert "primary_goal" in results[0].result
        assert results[0].result["primary_goal"] is not None

    @pytest.mark.asyncio
    async def test_goal_track_includes_progress(self) -> None:
        """Test that goal_track includes progress tracking."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.track_goal = AsyncMock(
            return_value={
                "primary_goal": "Refactor database layer",
                "sub_goals": ["Add connection pooling", "Implement migrations"],
                "progress_percent": 75,
                "current_focus": "Implement migrations",
                "completed_sub_goals": ["Add connection pooling"],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="goal_track",
            user_id="test-user",
            session_id="session-123",
            data={},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is True
        assert results[0].result is not None
        assert "progress_percent" in results[0].result
        assert "sub_goals" in results[0].result

    @pytest.mark.asyncio
    async def test_goal_track_handles_no_goal(self) -> None:
        """Test that goal_track handles sessions with no clear goal."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.track_goal = AsyncMock(
            return_value={
                "primary_goal": None,
                "sub_goals": [],
                "progress_percent": 0,
                "current_focus": None,
                "completed_sub_goals": [],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="goal_track",
            user_id="test-user",
            session_id="session-123",
            data={},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is True


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.xdist_group(name="conversation_intelligence_errors")
class TestConversationIntelligenceErrors:
    """Test error handling for conversation intelligence tasks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_intent_detect_handles_service_error(self) -> None:
        """Test that intent_detect handles service errors gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.detect_intent = AsyncMock(side_effect=Exception("Service unavailable"))

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="intent_detect",
            user_id="test-user",
            session_id="session-123",
            data={"query": "Test query"},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is False
        assert results[0].error is not None

    @pytest.mark.asyncio
    async def test_context_optimize_handles_missing_service(self) -> None:
        """Test that context_optimize handles missing service gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        # Create orchestrator without AI UX service
        orchestrator = StudioOrchestrator(ai_ux_service=None)
        task = StudioTask(
            category=TaskCategory.CONVERSATION,
            task_type="context_optimize",
            user_id="test-user",
            session_id="session-123",
            data={"current_tokens": 100000},
        )

        results = await orchestrator.execute([task])

        assert results[0].success is False
        assert "not configured" in (results[0].error or "").lower()
