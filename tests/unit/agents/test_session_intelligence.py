"""
Unit tests for Session Intelligence in StudioOrchestrator.

Tests session_summarize, session_group, and session_similarity task types.

Sprint 2: Session Intelligence
- Summarization generates one-line AI summaries per session
- Grouping clusters sessions by topic/project (not just date)
- Similarity search finds related sessions

TDD: Tests written FIRST before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents]


# =============================================================================
# Session Summarize Tests
# =============================================================================


@pytest.mark.xdist_group(name="session_intelligence_summarize")
class TestSessionSummarize:
    """Test session_summarize task type."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_summarize_returns_summary(self) -> None:
        """Test that session_summarize returns a summary string."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        # Mock AIUXService with summarize_session method
        mock_service = MagicMock()
        mock_service.summarize_session = AsyncMock(
            return_value={
                "summary": "User explored React component patterns and debugging techniques.",
                "key_topics": ["React", "debugging", "components"],
                "message_count": 15,
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="session-123",
            data={},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert result.result is not None
        assert "summary" in result.result

    @pytest.mark.asyncio
    async def test_session_summarize_includes_key_topics(self) -> None:
        """Test that session_summarize includes key topics."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.summarize_session = AsyncMock(
            return_value={
                "summary": "Database optimization discussion",
                "key_topics": ["PostgreSQL", "indexing", "query optimization"],
                "message_count": 8,
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="session-456",
            data={},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert "key_topics" in result.result
        assert isinstance(result.result["key_topics"], list)

    @pytest.mark.asyncio
    async def test_session_summarize_passes_session_id(self) -> None:
        """Test that session_summarize passes session_id to service."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.summarize_session = AsyncMock(return_value={"summary": "Test summary"})

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="specific-session-id",
            data={},
        )

        await orchestrator._execute_task(task)

        mock_service.summarize_session.assert_called_once()
        call_kwargs = mock_service.summarize_session.call_args.kwargs
        assert call_kwargs.get("session_id") == "specific-session-id"

    @pytest.mark.asyncio
    async def test_session_summarize_handles_empty_session(self) -> None:
        """Test that session_summarize handles empty session gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.summarize_session = AsyncMock(
            return_value={
                "summary": "Empty session - no messages yet.",
                "key_topics": [],
                "message_count": 0,
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="empty-session",
            data={},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert result.result["message_count"] == 0


# =============================================================================
# Session Group Tests
# =============================================================================


@pytest.mark.xdist_group(name="session_intelligence_group")
class TestSessionGroup:
    """Test session_group task type."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_group_returns_grouped_sessions(self) -> None:
        """Test that session_group returns sessions grouped by topic."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.group_sessions = AsyncMock(
            return_value={
                "groups": [
                    {
                        "topic": "API Development",
                        "session_ids": ["session-1", "session-2", "session-3"],
                        "confidence": 0.85,
                    },
                    {
                        "topic": "Frontend Work",
                        "session_ids": ["session-4", "session-5"],
                        "confidence": 0.78,
                    },
                ],
                "ungrouped": ["session-6"],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_group",
            user_id="test-user",
            data={"session_ids": ["session-1", "session-2", "session-3", "session-4", "session-5", "session-6"]},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert "groups" in result.result
        assert isinstance(result.result["groups"], list)

    @pytest.mark.asyncio
    async def test_session_group_includes_topic_names(self) -> None:
        """Test that session_group includes topic names for each group."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.group_sessions = AsyncMock(
            return_value={
                "groups": [
                    {
                        "topic": "Database Optimization",
                        "session_ids": ["s1", "s2"],
                        "confidence": 0.9,
                    }
                ],
                "ungrouped": [],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_group",
            user_id="test-user",
            data={"session_ids": ["s1", "s2"]},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert len(result.result["groups"]) > 0
        assert "topic" in result.result["groups"][0]

    @pytest.mark.asyncio
    async def test_session_group_handles_single_session(self) -> None:
        """Test that session_group handles single session."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.group_sessions = AsyncMock(
            return_value={
                "groups": [],
                "ungrouped": ["single-session"],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_group",
            user_id="test-user",
            data={"session_ids": ["single-session"]},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True


# =============================================================================
# Session Similarity Tests
# =============================================================================


@pytest.mark.xdist_group(name="session_intelligence_similarity")
class TestSessionSimilarity:
    """Test session_similarity task type."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_similarity_returns_similar_sessions(self) -> None:
        """Test that session_similarity returns similar sessions."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.find_similar_sessions = AsyncMock(
            return_value={
                "source_session_id": "session-123",
                "similar_sessions": [
                    {"session_id": "session-456", "similarity_score": 0.92, "common_topics": ["React", "hooks"]},
                    {"session_id": "session-789", "similarity_score": 0.78, "common_topics": ["React"]},
                ],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_similarity",
            user_id="test-user",
            session_id="session-123",
            data={"limit": 5},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert "similar_sessions" in result.result

    @pytest.mark.asyncio
    async def test_session_similarity_includes_scores(self) -> None:
        """Test that session_similarity includes similarity scores."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.find_similar_sessions = AsyncMock(
            return_value={
                "source_session_id": "session-123",
                "similar_sessions": [
                    {"session_id": "session-456", "similarity_score": 0.85, "common_topics": ["Python"]},
                ],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_similarity",
            user_id="test-user",
            session_id="session-123",
            data={},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        similar = result.result["similar_sessions"]
        assert len(similar) > 0
        assert "similarity_score" in similar[0]

    @pytest.mark.asyncio
    async def test_session_similarity_handles_no_matches(self) -> None:
        """Test that session_similarity handles no matches gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.find_similar_sessions = AsyncMock(
            return_value={
                "source_session_id": "unique-session",
                "similar_sessions": [],
            }
        )

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_similarity",
            user_id="test-user",
            session_id="unique-session",
            data={},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert result.result["similar_sessions"] == []


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.xdist_group(name="session_intelligence_errors")
class TestSessionIntelligenceErrors:
    """Test error handling for session intelligence tasks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_task_without_service_returns_error(self) -> None:
        """Test that session tasks without AIUXService return error."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        # No service configured
        orchestrator = StudioOrchestrator()

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="session-123",
        )

        result = await orchestrator._execute_task(task)

        assert result.success is False
        assert "not configured" in result.error.lower() or "service" in result.error.lower()

    @pytest.mark.asyncio
    async def test_session_task_service_exception_handled(self) -> None:
        """Test that exceptions from service are handled gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.summarize_session = AsyncMock(side_effect=Exception("LLM timeout"))

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="session-123",
        )

        result = await orchestrator._execute_task(task)

        assert result.success is False
        assert "timeout" in result.error.lower() or "error" in result.error.lower()


# =============================================================================
# Persona Access Tests
# =============================================================================


@pytest.mark.xdist_group(name="session_intelligence_persona")
class TestSessionIntelligencePersonaAccess:
    """Test persona-based access to session intelligence features."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_summarize_available_to_alice_builder(self) -> None:
        """Test that session_summarize is available to alice-builder persona."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.summarize_session = AsyncMock(return_value={"summary": "Test"})

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="session-123",
            persona="alice-builder",
        )

        result = await orchestrator._execute_task(task)

        # Should succeed for alice-builder
        assert result.success is True

    @pytest.mark.asyncio
    async def test_session_summarize_available_to_bob(self) -> None:
        """Test that session_summarize is available to bob persona."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.summarize_session = AsyncMock(return_value={"summary": "Test"})

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="session-123",
            persona="bob",
        )

        result = await orchestrator._execute_task(task)

        # Should succeed for bob
        assert result.success is True
