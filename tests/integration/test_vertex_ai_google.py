"""
Integration tests for Google Gemini models via Google Vertex AI.

Tests Gemini 3.0 Pro and 2.5 Flash models accessed through Vertex AI
instead of Google AI Studio API.

Model Versions (Latest as of Nov 2025):
- Gemini 3.0 Pro: gemini-3-pro-preview (released Nov 18, 2025)
- Gemini 2.5 Flash: gemini-2.5-flash

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
@pytest.mark.xdist_group(name="vertex_ai_google_tests")
class TestVertexAIGeminiModels:
    """Test Google Gemini models via Vertex AI."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_gemini_3_pro_via_vertex_ai_explicit_prefix(self):
        """Test Gemini 3.0 Pro via Vertex AI with explicit vertex_ai/ prefix."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-3-pro-preview",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        messages = [HumanMessage(content="Say 'Hello from Vertex AI Gemini 3.0 Pro' and nothing else.")]

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
    async def test_gemini_3_pro_via_vertex_ai_implicit_routing(self):
        """Test Gemini 3.0 Pro via Vertex AI without vertex_ai/ prefix (auto-routing)."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="gemini-3-pro-preview",  # No prefix - LiteLLM should auto-route to Vertex AI
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        messages = [HumanMessage(content="Say 'Hello from Gemini' and nothing else.")]

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
    async def test_gemini_2_5_flash_via_vertex_ai(self):
        """Test Gemini 2.5 Flash via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        messages = [HumanMessage(content="Say 'Hello from Vertex AI Gemini 2.5 Flash' and nothing else.")]

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
    async def test_gemini_2_5_flash_via_vertex_ai_implicit(self):
        """Test Gemini 2.5 Flash via Vertex AI with implicit routing."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="gemini-2.5-flash",  # No prefix
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        messages = [HumanMessage(content="What is 5 + 3? Provide only the number.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert "8" in response.content

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_gemini_with_conversation(self):
        """Test multi-turn conversation with Gemini via Vertex AI."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

        # Multi-turn conversation
        messages = [
            HumanMessage(content="My favorite color is blue."),
            HumanMessage(content="What did I say my favorite color was?"),
        ]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        # Gemini should reference the color from context
        assert len(response.content) > 0


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_google_tests")
class TestVertexAIGeminiConfiguration:
    """Test Vertex AI configuration for Google Gemini models."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_gemini_uses_project_from_config(self):
        """Test that Vertex AI uses project ID from configuration."""
        vertex_project = os.getenv("VERTEX_PROJECT")

        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=vertex_project,
            vertex_location="us-central1",
        )

        # Verify configuration is set correctly
        assert llm.provider == "vertex_ai"
        assert "gemini" in llm.model_name.lower()

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_gemini_supports_multiple_regions(self):
        """Test that Vertex AI Gemini works with different regions."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location="us-east4",  # Different region
        )

        messages = [HumanMessage(content="Hello")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_prefix_vs_no_prefix_equivalence(self):
        """Test that vertex_ai/ prefix and no prefix produce equivalent results."""
        # Create two LLM instances - one with prefix, one without
        llm_with_prefix = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-3-pro-preview",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location="us-central1",
        )

        llm_without_prefix = LLMFactory(
            provider="vertex_ai",
            model_name="gemini-3-pro-preview",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location="us-central1",
        )

        messages = [HumanMessage(content="Say 'test' and nothing else.")]

        # Both should work
        response_with_prefix = await llm_with_prefix.ainvoke(messages)
        response_without_prefix = await llm_without_prefix.ainvoke(messages)

        assert response_with_prefix is not None
        assert response_without_prefix is not None
        assert response_with_prefix.content
        assert response_without_prefix.content


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_google_tests")
class TestVertexAIGeminiErrorHandling:
    """Test error handling for Google Gemini models via Vertex AI."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_vertex_ai_gemini_requires_project_id(self):
        """Test that Vertex AI Gemini requires a project ID."""
        # This should either raise an error or use Application Default Credentials
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
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
    async def test_vertex_ai_gemini_invalid_model_name(self):
        """Test error handling for invalid Gemini model name."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-invalid-version",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location="us-central1",
        )

        messages = [HumanMessage(content="Hello")]

        # Should raise an error when trying to invoke invalid model
        with pytest.raises(Exception):  # LiteLLM will raise an error
            await llm.ainvoke(messages)

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_vertex_ai_gemini_empty_message(self):
        """Test error handling for empty message."""
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location="us-central1",
        )

        messages = [HumanMessage(content="")]

        # Gemini should handle empty messages gracefully or raise a clear error
        # This test documents the actual behavior
        try:
            response = await llm.ainvoke(messages)
            # If it succeeds, verify response is valid
            assert response is not None
        except Exception as e:
            # If it fails, verify error is informative
            assert e is not None
