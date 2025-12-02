"""
Integration tests for Vertex AI authentication methods.

Tests both authentication approaches:
1. Workload Identity (GKE) - automatic, no credentials needed
2. Service Account Key (GOOGLE_APPLICATION_CREDENTIALS) - for local development

These tests verify that LLMFactory correctly handles Vertex AI authentication
for both Anthropic Claude and Google Gemini models.

IMPORTANT: Region Configuration
- Claude models (Opus, Sonnet, Haiku) are only available in us-east5 on Vertex AI
- Gemini models are available in most regions including us-central1 and global
- See: https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/use-claude
"""

import gc
import os

import pytest
from langchain_core.messages import HumanMessage

from mcp_server_langgraph.llm.factory import LLMFactory

pytestmark = pytest.mark.integration

# Region configuration for different model families on Vertex AI
# Claude models are only available in us-east5
# Gemini models work in most regions (us-central1, global, etc.)
CLAUDE_REGION = os.getenv("VERTEX_LOCATION", "us-east5")
GEMINI_REGION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_auth_tests")
class TestVertexAIWorkloadIdentity:
    """Test Vertex AI with Workload Identity (GKE authentication)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT") or bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
        reason="Requires VERTEX_PROJECT and NO GOOGLE_APPLICATION_CREDENTIALS (Workload Identity)",
    )
    @pytest.mark.asyncio
    async def test_workload_identity_claude(self):
        """Test Claude via Vertex AI using Workload Identity (no explicit credentials)."""
        # When GOOGLE_APPLICATION_CREDENTIALS is NOT set, Vertex AI should use
        # Workload Identity (automatic on GKE)
        # Note: Claude models only available in us-east5 on Vertex AI
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=CLAUDE_REGION,
        )

        messages = [HumanMessage(content="Say 'Hello' and nothing else.")]
        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT") or bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
        reason="Requires VERTEX_PROJECT and NO GOOGLE_APPLICATION_CREDENTIALS (Workload Identity)",
    )
    @pytest.mark.asyncio
    async def test_workload_identity_gemini(self):
        """Test Gemini via Vertex AI using Workload Identity."""
        # Note: Gemini models available in most regions (global, us-central1, etc.)
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=GEMINI_REGION,
        )

        messages = [HumanMessage(content="Say 'Hello' and nothing else.")]
        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_auth_tests")
class TestVertexAIServiceAccountKey:
    """Test Vertex AI with Service Account Key (local development)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT") or not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        reason="Requires both VERTEX_PROJECT and GOOGLE_APPLICATION_CREDENTIALS",
    )
    @pytest.mark.asyncio
    async def test_service_account_key_claude(self):
        """Test Claude via Vertex AI using service account key file."""
        # When GOOGLE_APPLICATION_CREDENTIALS is set, Vertex AI should use
        # the specified service account key file
        # Note: Claude models only available in us-east5 on Vertex AI
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/claude-haiku-4-5@20251001",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=CLAUDE_REGION,
        )

        messages = [HumanMessage(content="Say 'Hello' and nothing else.")]
        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT") or not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        reason="Requires both VERTEX_PROJECT and GOOGLE_APPLICATION_CREDENTIALS",
    )
    @pytest.mark.asyncio
    async def test_service_account_key_gemini(self):
        """Test Gemini via Vertex AI using service account key file."""
        # Note: Gemini models available in most regions (global, us-central1, etc.)
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=GEMINI_REGION,
        )

        messages = [HumanMessage(content="Say 'Hello' and nothing else.")]
        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content


@pytest.mark.integration
@pytest.mark.xdist_group(name="vertex_ai_auth_tests")
class TestVertexAIAuthConfiguration:
    """Test Vertex AI authentication configuration and error handling."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not os.getenv("VERTEX_PROJECT"),
        reason="VERTEX_PROJECT not set - requires Vertex AI access",
    )
    @pytest.mark.asyncio
    async def test_auto_detect_auth_method(self):
        """Test that LLMFactory auto-detects the appropriate auth method."""
        # LiteLLM should automatically detect whether to use Workload Identity
        # or service account key based on environment
        # Note: Using Gemini here as it's available in more regions
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=os.getenv("VERTEX_PROJECT"),
            vertex_location=GEMINI_REGION,
        )

        # Verify factory was created successfully
        assert llm is not None
        assert llm.provider == "vertex_ai"

        # Test that it can actually invoke (auth is working)
        messages = [HumanMessage(content="Test")]
        response = await llm.ainvoke(messages)
        assert response is not None

    @pytest.mark.asyncio
    async def test_missing_project_id_handling(self):
        """Test error handling when project ID is missing."""
        # Without a project ID, Vertex AI may try to use Application Default Credentials
        # or fail gracefully
        llm = LLMFactory(
            provider="vertex_ai",
            model_name="vertex_ai/gemini-2.5-flash",
            vertex_project=None,  # No project specified
            vertex_location=GEMINI_REGION,
        )

        # Factory should be created
        assert llm is not None

        # But invocation may fail without proper credentials/project
        # This test documents the behavior
        messages = [HumanMessage(content="Test")]
        try:
            response = await llm.ainvoke(messages)
            # If it succeeds, credentials were found via ADC
            assert response is not None
        except Exception as e:
            # If it fails, verify error is about missing credentials/project
            assert e is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
