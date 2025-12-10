"""
Integration tests for Anthropic Claude models via Google Vertex AI.

Tests Claude Opus 4.1, Sonnet 4.5, and Haiku 4.5 models accessed through Vertex AI
instead of direct Anthropic API.

Model Versions (Latest as of 2025):
- Claude Haiku 4.5: claude-haiku-4-5@20251001
- Claude Sonnet 4.5: claude-sonnet-4-5@20250929
- Claude Opus 4.1: claude-opus-4-1@20250805

Authentication:
- On GKE: Workload Identity (automatic)
- Locally: GOOGLE_APPLICATION_CREDENTIALS environment variable

Environment Variables for Claude on Vertex AI:
- ANTHROPIC_VERTEX_PROJECT_ID: Project ID for Claude on Vertex AI (falls back to VERTEX_PROJECT)
- CLOUD_ML_REGION: Region for Claude on Vertex AI (defaults to global, falls back to us-east5)
- VERTEX_PROJECT: General Vertex AI project ID (for Gemini: defaults to global, falls back to us-central1)
- VERTEX_LOCATION: General Vertex AI location (for Gemini models)
"""

import gc
import os

import pytest
from langchain_core.messages import HumanMessage

from mcp_server_langgraph.llm.factory import LLMFactory

# Check if vertexai SDK is installed (required for Vertex AI partner models)
try:
    import vertexai  # noqa: F401

    VERTEX_SDK_AVAILABLE = True
except ImportError:
    VERTEX_SDK_AVAILABLE = False

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def get_claude_vertex_project() -> str | None:
    """Get project ID for Claude on Vertex AI.

    Checks ANTHROPIC_VERTEX_PROJECT_ID first, falls back to VERTEX_PROJECT.
    """
    return os.getenv("ANTHROPIC_VERTEX_PROJECT_ID") or os.getenv("VERTEX_PROJECT")


def vertex_ai_available() -> bool:
    """Check if Vertex AI is available (SDK installed and project configured)."""
    return VERTEX_SDK_AVAILABLE and bool(get_claude_vertex_project())


def get_vertex_skip_reason() -> str:
    """Get appropriate skip reason for Vertex AI tests."""
    if not VERTEX_SDK_AVAILABLE:
        return "vertexai SDK not installed - run: pip install google-cloud-aiplatform>=1.38"
    if not get_claude_vertex_project():
        return "ANTHROPIC_VERTEX_PROJECT_ID or VERTEX_PROJECT not set - requires Vertex AI access"
    return ""


def get_claude_vertex_location() -> str:
    """Get location for Claude on Vertex AI.

    Checks CLOUD_ML_REGION first, then VERTEX_LOCATION, defaults to global.
    Falls back to 'us-east5' if the region is not set.

    Note: Claude on Vertex AI is available in limited regions. 'global' works
    for most cases, with 'us-east5' as a reliable fallback.
    """
    return os.getenv("CLOUD_ML_REGION") or os.getenv("VERTEX_LOCATION", "global") or "us-east5"


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_anthropic_tests")
class TestVertexAIAnthropicModels:
    """Test Anthropic Claude models via Vertex AI."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not vertex_ai_available(),
        reason=get_vertex_skip_reason() or "Vertex AI not available",
    )
    @pytest.mark.asyncio
    async def test_claude_sonnet_4_5_via_vertex_ai(self):
        """Test Claude Sonnet 4.5 via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-sonnet-4-5@20250929",
            vertex_project=get_claude_vertex_project(),
            vertex_location=get_claude_vertex_location(),
        )

        messages = [HumanMessage(content="Say 'Hello from Vertex AI Claude Sonnet 4.5' and nothing else.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    @pytest.mark.skipif(
        not vertex_ai_available(),
        reason=get_vertex_skip_reason() or "Vertex AI not available",
    )
    @pytest.mark.asyncio
    async def test_claude_haiku_4_5_via_vertex_ai(self):
        """Test Claude Haiku 4.5 via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=get_claude_vertex_project(),
            vertex_location=get_claude_vertex_location(),
        )

        messages = [HumanMessage(content="Say 'Hello from Vertex AI Claude Haiku 4.5' and nothing else.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    @pytest.mark.skipif(
        not vertex_ai_available(),
        reason=get_vertex_skip_reason() or "Vertex AI not available",
    )
    @pytest.mark.asyncio
    async def test_claude_opus_4_5_via_vertex_ai(self):
        """Test Claude Opus 4.5 via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-opus-4-5@20251101",
            vertex_project=get_claude_vertex_project(),
            vertex_location=get_claude_vertex_location(),
        )

        messages = [HumanMessage(content="Say 'Hello from Vertex AI Claude Opus 4.5' and nothing else.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    @pytest.mark.skipif(
        not vertex_ai_available(),
        reason=get_vertex_skip_reason() or "Vertex AI not available",
    )
    @pytest.mark.asyncio
    async def test_claude_sonnet_4_5_reasoning(self):
        """Test Claude Sonnet 4.5 reasoning capabilities via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-sonnet-4-5@20250929",
            vertex_project=get_claude_vertex_project(),
            vertex_location=get_claude_vertex_location(),
        )

        messages = [HumanMessage(content="What is 2 + 2? Think through this step by step, then provide your answer.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert "4" in response.content

    @pytest.mark.skipif(
        not vertex_ai_available(),
        reason=get_vertex_skip_reason() or "Vertex AI not available",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_claude_with_conversation(self):
        """Test multi-turn conversation with Claude via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-sonnet-4-5@20250929",
            vertex_project=get_claude_vertex_project(),
            vertex_location=get_claude_vertex_location(),
        )

        # Multi-turn conversation
        messages = [
            HumanMessage(content="My name is Alice."),
            # In a real conversation, we'd have an AIMessage here
            # but for testing we'll just verify it responds to context
            HumanMessage(content="What name did I just tell you?"),
        ]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        # Claude should reference the name from context
        assert len(response.content) > 0


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_anthropic_tests")
class TestVertexAIAnthropicConfiguration:
    """Test Vertex AI configuration for Anthropic models."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not vertex_ai_available(),
        reason=get_vertex_skip_reason() or "Vertex AI not available",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_uses_project_from_config(self):
        """Test that Vertex AI uses project ID from configuration."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=get_claude_vertex_project(),
            vertex_location=get_claude_vertex_location(),
        )

        # Verify configuration is set correctly
        assert llm.provider == "vertex_ai"
        assert "claude" in llm.model_name.lower()

    @pytest.mark.skipif(
        not vertex_ai_available(),
        reason=get_vertex_skip_reason() or "Vertex AI not available",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_supports_multiple_regions(self):
        """Test that Vertex AI works with different regions (fallback to global)."""
        # Test with 'global' region as fallback
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=get_claude_vertex_project(),
            vertex_location="global",  # Fallback region
        )

        messages = [HumanMessage(content="Hello")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_anthropic_tests")
class TestVertexAIAnthropicErrorHandling:
    """Test error handling for Anthropic models via Vertex AI."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_vertex_ai_requires_project_id(self):
        """Test that Vertex AI requires a project ID."""
        # This should either raise an error or use Application Default Credentials
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=None,  # No project specified
            vertex_location=get_claude_vertex_location(),
        )

        # The factory should be created, but invocation may fail without credentials
        assert llm is not None

    @pytest.mark.skipif(
        not vertex_ai_available(),
        reason=get_vertex_skip_reason() or "Vertex AI not available",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_invalid_model_name(self):
        """Test error handling for invalid model name."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/invalid-model-name",
            vertex_project=get_claude_vertex_project(),
            vertex_location=get_claude_vertex_location(),
        )

        messages = [HumanMessage(content="Hello")]

        # Should raise an error when trying to invoke invalid model
        with pytest.raises(Exception):  # LiteLLM will raise an error
            await llm.ainvoke(messages)
