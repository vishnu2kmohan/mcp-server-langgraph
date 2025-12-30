"""
TDD: Unit tests for Diagram Intelligence LLM Integration.

Tests that AIUXService diagram intelligence methods use real LLM calls
when llm_factory is configured, with fallback to heuristics.

Sprint 4: Diagram Intelligence
- analyze_diagram() uses LLM for Mermaid diagram analysis
- diagram_to_code() uses LLM to generate code from diagrams

RED phase: These tests define expected behavior before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents, pytest.mark.diagram_intelligence]


# =============================================================================
# LLM Integration Tests for analyze_diagram
# =============================================================================


@pytest.mark.xdist_group(name="diagram_intelligence_llm_analyze")
class TestDiagramAnalyzeLLM:
    """Test analyze_diagram LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_analyze_diagram_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN analyze_diagram called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "diagram_type": "flowchart",
            "is_valid": true,
            "node_count": 5,
            "edge_count": 4,
            "complexity_score": 0.6,
            "issues": [],
            "suggestions": [
                {"type": "improvement", "description": "Consider adding error handling nodes"}
            ],
            "description": "A user authentication flow with login and password validation"
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_diagram_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.analyze_diagram(
            diagram_code="graph TD\n    A[Login] --> B[Validate]\n    B --> C[Success]",
            user_id="user-1",
        )

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "diagram_type" in result
        assert "node_count" in result
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_analyze_diagram_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN analyze_diagram THEN uses heuristics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.analyze_diagram(
            diagram_code="graph TD\n    A --> B",
            user_id="user-1",
        )

        # Verify heuristic fallback
        assert "diagram_type" in result
        assert "node_count" in result
        assert "is_valid" in result

    @pytest.mark.asyncio
    async def test_analyze_diagram_fallback_on_llm_error(self) -> None:
        """GIVEN LLM call fails WHEN analyze_diagram THEN returns heuristic fallback."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_diagram_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.analyze_diagram(
            diagram_code="graph TD\n    A --> B",
            user_id="user-1",
        )

        # Should not raise, should return fallback
        assert "diagram_type" in result
        assert "is_valid" in result


# =============================================================================
# LLM Integration Tests for diagram_to_code
# =============================================================================


@pytest.mark.xdist_group(name="diagram_intelligence_llm_code")
class TestDiagramToCodeLLM:
    """Test diagram_to_code LLM integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_diagram_to_code_calls_llm_when_enabled(self) -> None:
        """GIVEN LLM factory configured WHEN diagram_to_code called THEN uses LLM."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "code": "async function authenticate(credentials: Credentials): Promise<AuthResult> {\\n  const validated = await validate(credentials);\\n  if (!validated) throw new AuthError();\\n  return { success: true };\\n}",
            "language": "typescript",
            "confidence": 0.85,
            "explanation": "Generated TypeScript function implementing the authentication flow from the diagram"
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_diagram_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.diagram_to_code(
            diagram_code="graph TD\n    A[Login] --> B[Validate]\n    B --> C[Success]",
            target_language="typescript",
            user_id="user-1",
        )

        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()

        # Verify result structure
        assert "code" in result
        assert "language" in result
        assert result["language"] == "typescript"

    @pytest.mark.asyncio
    async def test_diagram_to_code_fallback_when_llm_disabled(self) -> None:
        """GIVEN LLM factory not configured WHEN diagram_to_code THEN uses placeholder."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = False

        service = AIUXService(llm_factory=None, settings=mock_settings)

        result = await service.diagram_to_code(
            diagram_code="graph TD\n    A --> B",
            target_language="python",
            user_id="user-1",
        )

        # Verify fallback
        assert "code" in result
        assert "language" in result
        assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_diagram_to_code_parses_llm_response(self) -> None:
        """GIVEN valid LLM JSON response WHEN diagram_to_code THEN parses correctly."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """
        {
            "code": "def process(data):\\n    return transform(data)",
            "language": "python",
            "confidence": 0.9,
            "explanation": "Simple data processing function"
        }
        """
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_diagram_intelligence = True

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.diagram_to_code(
            diagram_code="graph TD\n    Input --> Process --> Output",
            target_language="python",
            user_id="user-1",
        )

        assert result["confidence"] == 0.9
        assert "explanation" in result


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.xdist_group(name="diagram_intelligence_llm_flags")
class TestDiagramIntelligenceFeatureFlags:
    """Test feature flag gating for diagram intelligence LLM calls."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_diagram_intelligence_requires_feature_flag(self) -> None:
        """GIVEN feature flag disabled WHEN diagram method called THEN uses heuristics."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_settings = MagicMock()
        mock_settings.ff_enable_ai_suggestions = True
        mock_settings.ff_enable_diagram_intelligence = False  # Disabled

        service = AIUXService(llm_factory=mock_llm, settings=mock_settings)

        result = await service.analyze_diagram(
            diagram_code="graph TD\n    A --> B",
            user_id="u1",
        )

        # LLM should NOT be called when feature flag is disabled
        mock_llm.ainvoke.assert_not_called()

        # Should still return valid structure (heuristic fallback)
        assert "diagram_type" in result
        assert "is_valid" in result
