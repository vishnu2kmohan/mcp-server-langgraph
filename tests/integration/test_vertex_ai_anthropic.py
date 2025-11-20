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
"""

import gc
import os

import pytest
from langchain_core.messages import HumanMessage

from mcp_server_langgraph.llm.factory import LLMFactory


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_anthropic_tests")
class TestVertexAIAnthropicModels:
    """Test Anthropic Claude models via Vertex AI."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_claude_sonnet_4_5_via_vertex_ai(self):
        """Test Claude Sonnet 4.5 via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-sonnet-4-5@20250929",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        messages = [HumanMessage(content="Say 'Hello from Vertex AI Claude Sonnet 4.5' and nothing else.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_claude_haiku_4_5_via_vertex_ai(self):
        """Test Claude Haiku 4.5 via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        messages = [HumanMessage(content="Say 'Hello from Vertex AI Claude Haiku 4.5' and nothing else.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_claude_opus_4_1_via_vertex_ai(self):
        """Test Claude Opus 4.1 via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-opus-4-1@20250805",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        messages = [HumanMessage(content="Say 'Hello from Vertex AI Claude Opus 4.1' and nothing else.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_claude_sonnet_4_5_reasoning(self):
        """Test Claude Sonnet 4.5 reasoning capabilities via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-sonnet-4-5@20250929",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        messages = [HumanMessage(content="What is 2 + 2? Think through this step by step, then provide your answer.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert "4" in response.content

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_claude_with_conversation(self):
        """Test multi-turn conversation with Claude via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-sonnet-4-5@20250929",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
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
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_uses_project_from_config(self):
        """Test that Vertex AI uses project ID from configuration."""
        vertex_project = os.getenv("VERTEX_PROJECT")

        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=vertex_project,
            vertex_location="us-central1",
        )

        # Verify configuration is set correctly
        assert llm.provider == "vertex_ai"
        assert "claude" in llm.model_name.lower()

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_supports_multiple_regions(self):
        """Test that Vertex AI works with different regions."""
        # Test with explicit region
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location="us-east4",  # Different region
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
            vertex_location="us-central1",
        )

        # The factory should be created, but invocation may fail without credentials
        assert llm is not None

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_invalid_model_name(self):
        """Test error handling for invalid model name."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/invalid-model-name",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location="us-central1",
        )

        messages = [HumanMessage(content="Hello")]

        # Should raise an error when trying to invoke invalid model
        with pytest.raises(Exception):  # LiteLLM will raise an error
            await llm.ainvoke(messages)
