"""
TDD: Unit tests for Session Intelligence LLM Integration.

Tests that AIUXService session intelligence methods use real LLM calls
when llm_factory is configured, with fallback to heuristics.

Sprint 2: Session Intelligence
- summarize_session() uses LLM to generate summaries
- group_sessions() uses LLM to cluster by topic
- find_similar_sessions() uses LLM to find related sessions

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents, pytest.mark.session_intelligence]


# =============================================================================
# LLM Integration Tests for summarize_session
# =============================================================================


class TestSessionSummarizeLLM:
    """Test summarize_session LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_summarize_session_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN summarize_session called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Mock LLM factory with a proper response
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "summary": "User discussed React component optimization",
            "key_topics": ["React", "performance", "memoization"],
            "highlight_messages": ["How to use useMemo", "React.memo explained"],
            "message_count": 12,
            "confidence": 0.92
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_session_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.summarize_session(session_id="session-123")

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "summary" in result
        assert result["summary"] != "Session session-123 summary placeholder"  # Not placeholder
        assert "key_topics" in result
        assert isinstance(result["key_topics"], list)

    @pytest.mark.asyncio
    async def test_summarize_session_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN summarize_session THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Mock settings without LLM
        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.summarize_session(session_id="session-123")

        # Verify fallback response (placeholder)
        assert "summary" in result
        # When LLM is disabled, should still return valid structure

    @pytest.mark.asyncio
    async def test_summarize_session_fallback_on_llm_error(self) -> None:
        """GIVEN LLM call fails WHEN summarize_session THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        # Mock LLM that raises exception
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_session_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.summarize_session(session_id="session-123")

        # Should not raise, should return fallback
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_summarize_session_parses_llm_response(self) -> None:
        """GIVEN valid LLM JSON response WHEN summarize_session THEN parses correctly."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "summary": "Debugging TypeScript type errors",
            "key_topics": ["TypeScript", "types", "debugging"],
            "highlight_messages": ["The error is in line 42"],
            "message_count": 8,
            "confidence": 0.88
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_session_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.summarize_session(session_id="session-456")

        assert result["summary"] == "Debugging TypeScript type errors"
        assert "TypeScript" in result["key_topics"]
        assert result["message_count"] == 8
        assert result["confidence"] == 0.88


# =============================================================================
# LLM Integration Tests for group_sessions
# =============================================================================


class TestSessionGroupLLM:
    """Test group_sessions LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_group_sessions_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN group_sessions called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "groups": [
                {
                    "topic": "React Development",
                    "session_ids": ["s1", "s2"],
                    "confidence": 0.85
                },
                {
                    "topic": "Database Work",
                    "session_ids": ["s3"],
                    "confidence": 0.78
                }
            ],
            "ungrouped": ["s4"]
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_session_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.group_sessions(
            session_ids=["s1", "s2", "s3", "s4"],
            user_id="user-123",
        )

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "groups" in result
        assert len(result["groups"]) == 2
        assert result["groups"][0]["topic"] == "React Development"

    @pytest.mark.asyncio
    async def test_group_sessions_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN group_sessions THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.group_sessions(
            session_ids=["s1", "s2"],
            user_id="user-123",
        )

        # Verify fallback response
        assert "groups" in result
        # Fallback groups all sessions under "General"

    @pytest.mark.asyncio
    async def test_group_sessions_handles_malformed_response(self) -> None:
        """GIVEN LLM returns malformed JSON WHEN group_sessions THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Not valid JSON"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_session_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.group_sessions(
            session_ids=["s1", "s2"],
            user_id="user-123",
        )

        # Should not raise, should return fallback
        assert "groups" in result


# =============================================================================
# LLM Integration Tests for find_similar_sessions
# =============================================================================


class TestSessionSimilarityLLM:
    """Test find_similar_sessions LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_find_similar_sessions_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN find_similar_sessions THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "similar_sessions": [
                {
                    "session_id": "s2",
                    "similarity_score": 0.92,
                    "common_topics": ["React", "hooks"]
                },
                {
                    "session_id": "s3",
                    "similarity_score": 0.78,
                    "common_topics": ["React"]
                }
            ],
            "search_query": "React component patterns"
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_session_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.find_similar_sessions(
            session_id="s1",
            user_id="user-123",
        )

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "similar_sessions" in result
        assert len(result["similar_sessions"]) == 2
        assert result["similar_sessions"][0]["similarity_score"] == 0.92

    @pytest.mark.asyncio
    async def test_find_similar_sessions_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN find_similar_sessions THEN returns fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.find_similar_sessions(
            session_id="s1",
            user_id="user-123",
        )

        # Verify fallback response
        assert "similar_sessions" in result
        assert result["similar_sessions"] == []  # Empty when no LLM

    @pytest.mark.asyncio
    async def test_find_similar_sessions_respects_limit(self) -> None:
        """GIVEN limit parameter WHEN find_similar_sessions THEN respects limit."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        # LLM returns 5 results
        mock_response.content = """
        {
            "similar_sessions": [
                {"session_id": "s2", "similarity_score": 0.95, "common_topics": ["A"]},
                {"session_id": "s3", "similarity_score": 0.90, "common_topics": ["A"]},
                {"session_id": "s4", "similarity_score": 0.85, "common_topics": ["B"]}
            ],
            "search_query": "test"
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_session_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.find_similar_sessions(
            session_id="s1",
            user_id="user-123",
            limit=2,
        )

        # Should respect limit parameter
        assert len(result["similar_sessions"]) <= 2


# =============================================================================
# Feature Flag Tests
# =============================================================================


class TestSessionIntelligenceFeatureFlags:
    """Test feature flag gating for session intelligence LLM calls."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_intelligence_requires_feature_flag(self) -> None:
        """GIVEN feature flag disabled WHEN session method called THEN uses fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        # Configure return_value even though we don't expect it to be called
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_session_intelligence = False  # Disabled

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.summarize_session(session_id="s1")

        # LLM should NOT be called when feature flag is disabled
        mock_llm.ainvoke.assert_not_called()

        # Should still return valid structure (fallback)
        assert "summary" in result
