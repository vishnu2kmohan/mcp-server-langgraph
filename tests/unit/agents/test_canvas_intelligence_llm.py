"""
TDD: Unit tests for Canvas Intelligence LLM Integration.

Tests that AIUXService canvas intelligence methods use real LLM calls
when llm_factory is configured, with fallback to heuristics.

Sprint 4: Canvas Intelligence
- suggest_artifact_type() uses LLM for smart type detection
- analyze_code() uses LLM for code quality analysis
- explain_diff() uses LLM for change explanations

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents, pytest.mark.canvas_intelligence]


# =============================================================================
# LLM Integration Tests for suggest_artifact_type
# =============================================================================


@pytest.mark.xdist_group(name="canvas_intelligence_llm_artifact")
class TestArtifactTypeLLM:
    """Test suggest_artifact_type LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_suggest_artifact_type_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN suggest_artifact_type called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "suggested_type": "mermaid",
            "confidence": 0.95,
            "alternatives": [
                {"type": "code", "confidence": 0.3}
            ],
            "reason": "Content contains Mermaid flowchart syntax with nodes and edges"
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_canvas_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.suggest_artifact_type(
            content="graph TD\n    A[Start] --> B[End]",
            user_id="user-1",
        )

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "suggested_type" in result
        assert "confidence" in result
        assert result["reason"] != "Content contains Mermaid diagram syntax"  # Not heuristic

    @pytest.mark.asyncio
    async def test_suggest_artifact_type_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN suggest_artifact_type THEN uses heuristics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.suggest_artifact_type(
            content="graph TD\n    A --> B",
            user_id="user-1",
        )

        # Verify heuristic fallback
        assert "suggested_type" in result
        assert "confidence" in result


# =============================================================================
# LLM Integration Tests for analyze_code
# =============================================================================


@pytest.mark.xdist_group(name="canvas_intelligence_llm_code")
class TestCodeAnalysisLLM:
    """Test analyze_code LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_analyze_code_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN analyze_code called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "complexity": 8,
            "quality_score": 0.75,
            "issues": [
                {"type": "security", "message": "SQL injection risk detected", "severity": "high"}
            ],
            "suggestions": [
                {"type": "refactor", "description": "Use parameterized queries", "priority": "high"}
            ],
            "language": "python",
            "lines_of_code": 25
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_canvas_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.analyze_code(
            code='query = f"SELECT * FROM users WHERE id = {user_id}"',
            language="python",
            user_id="user-1",
        )

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "complexity" in result
        assert "quality_score" in result
        assert "issues" in result
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_code_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN analyze_code THEN uses heuristics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.analyze_code(
            code="def hello():\n    print('Hello')",
            language="python",
            user_id="user-1",
        )

        # Verify heuristic fallback
        assert "complexity" in result
        assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_analyze_code_fallback_on_llm_error(self) -> None:
        """GIVEN LLM call fails WHEN analyze_code THEN returns heuristic fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_canvas_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.analyze_code(
            code="def hello(): pass",
            language="python",
            user_id="user-1",
        )

        # Should not raise, should return fallback
        assert "complexity" in result
        assert "quality_score" in result


# =============================================================================
# LLM Integration Tests for explain_diff
# =============================================================================


@pytest.mark.xdist_group(name="canvas_intelligence_llm_diff")
class TestDiffExplainLLM:
    """Test explain_diff LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_explain_diff_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN explain_diff called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "summary": "Changed authentication from basic auth to OAuth2 token-based authentication",
            "changes": [
                {"type": "modification", "description": "Replaced password check with token validation", "impact": "high"}
            ],
            "breaking_changes": true,
            "affected_areas": ["authentication", "API endpoints"]
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_canvas_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.explain_diff(
            old_content="def auth(password): return check_password(password)",
            new_content="def auth(token): return validate_oauth_token(token)",
            user_id="user-1",
        )

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "summary" in result
        assert "changes" in result
        assert result["breaking_changes"] is True

    @pytest.mark.asyncio
    async def test_explain_diff_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN explain_diff THEN uses heuristics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.explain_diff(
            old_content="line1\nline2",
            new_content="line1\nline3",
            user_id="user-1",
        )

        # Verify heuristic fallback
        assert "summary" in result
        assert "changes" in result


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.xdist_group(name="canvas_intelligence_llm_flags")
class TestCanvasIntelligenceFeatureFlags:
    """Test feature flag gating for canvas intelligence LLM calls."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_canvas_intelligence_requires_feature_flag(self) -> None:
        """GIVEN feature flag disabled WHEN canvas method called THEN uses heuristics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_canvas_intelligence = False  # Disabled

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.suggest_artifact_type(
            content="test content",
            user_id="u1",
        )

        # LLM should NOT be called when feature flag is disabled
        mock_llm.ainvoke.assert_not_called()

        # Should still return valid structure (heuristic fallback)
        assert "suggested_type" in result
        assert "confidence" in result
