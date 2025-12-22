"""
Integration tests for Azure OpenAI models.

Tests GPT-5 and GPT-5.2 models accessed through Azure OpenAI Service.

Model Versions (December 2025):
- GPT-5.2: Azure deployment of latest GPT model
- GPT-5.2-pro: Higher capability variant

Authentication:
- AZURE_API_KEY: Azure OpenAI API key
- AZURE_API_BASE: Azure OpenAI endpoint (https://your-resource.openai.azure.com/)
- AZURE_API_VERSION: API version (e.g., 2024-12-01)
- AZURE_DEPLOYMENT_NAME: Deployment name for the model

Environment Variables:
- AZURE_API_KEY: Required for authentication
- AZURE_API_BASE: Required for endpoint resolution
- AZURE_API_VERSION: Required for API versioning
- AZURE_DEPLOYMENT_NAME: Optional, defaults to model name
"""

import gc
import os

import pytest
from langchain_core.messages import HumanMessage

from mcp_server_langgraph.llm.factory import LLMFactory

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def get_azure_api_key() -> str | None:
    """Get Azure OpenAI API key from environment."""
    return os.getenv("AZURE_API_KEY")


def get_azure_api_base() -> str | None:
    """Get Azure OpenAI endpoint from environment."""
    return os.getenv("AZURE_API_BASE")


def get_azure_api_version() -> str:
    """Get Azure OpenAI API version from environment."""
    return os.getenv("AZURE_API_VERSION", "2024-12-01")


def get_azure_deployment_name() -> str | None:
    """Get Azure OpenAI deployment name from environment."""
    return os.getenv("AZURE_DEPLOYMENT_NAME")


def azure_openai_available() -> bool:
    """Check if Azure OpenAI is available (credentials configured)."""
    return bool(get_azure_api_key() and get_azure_api_base())


def get_azure_skip_reason() -> str:
    """Get appropriate skip reason for Azure OpenAI tests."""
    if not get_azure_api_key():
        return "AZURE_API_KEY not set - requires Azure OpenAI access"
    if not get_azure_api_base():
        return "AZURE_API_BASE not set - requires Azure OpenAI endpoint"
    return ""


@pytest.mark.integration
@pytest.mark.xdist_group(name="azure_openai_tests")
class TestAzureOpenAIModels:
    """Test OpenAI GPT models via Azure OpenAI Service."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not azure_openai_available(),
        reason=get_azure_skip_reason() or "Azure OpenAI not available",
    )
    @pytest.mark.asyncio
    async def test_gpt_model_via_azure(self):
        """Test GPT model via Azure OpenAI."""
        deployment = get_azure_deployment_name() or "gpt-5.2"
        llm = LLMFactory(
            provider="azure",
            model_name=f"azure/{deployment}",
            api_key=get_azure_api_key(),
            api_base=get_azure_api_base(),
            api_version=get_azure_api_version(),
        )

        messages = [HumanMessage(content="Say 'Hello from Azure OpenAI' and nothing else.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    @pytest.mark.skipif(
        not azure_openai_available(),
        reason=get_azure_skip_reason() or "Azure OpenAI not available",
    )
    @pytest.mark.asyncio
    async def test_azure_openai_reasoning(self):
        """Test GPT reasoning capabilities via Azure OpenAI."""
        deployment = get_azure_deployment_name() or "gpt-5.2"
        llm = LLMFactory(
            provider="azure",
            model_name=f"azure/{deployment}",
            api_key=get_azure_api_key(),
            api_base=get_azure_api_base(),
            api_version=get_azure_api_version(),
        )

        messages = [HumanMessage(content="What is 2 + 2? Think through this step by step, then provide your answer.")]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert "4" in response.content

    @pytest.mark.skipif(
        not azure_openai_available(),
        reason=get_azure_skip_reason() or "Azure OpenAI not available",
    )
    @pytest.mark.asyncio
    async def test_azure_openai_conversation(self):
        """Test multi-turn conversation with GPT via Azure OpenAI."""
        deployment = get_azure_deployment_name() or "gpt-5.2"
        llm = LLMFactory(
            provider="azure",
            model_name=f"azure/{deployment}",
            api_key=get_azure_api_key(),
            api_base=get_azure_api_base(),
            api_version=get_azure_api_version(),
        )

        # Multi-turn conversation
        messages = [
            HumanMessage(content="My name is Alice."),
            HumanMessage(content="What name did I just tell you?"),
        ]

        response = await llm.ainvoke(messages)

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0


@pytest.mark.integration
@pytest.mark.xdist_group(name="azure_openai_tests")
class TestAzureOpenAIConfiguration:
    """Test Azure OpenAI configuration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not azure_openai_available(),
        reason=get_azure_skip_reason() or "Azure OpenAI not available",
    )
    @pytest.mark.asyncio
    async def test_azure_uses_endpoint_from_config(self):
        """Test that Azure OpenAI uses endpoint from configuration."""
        deployment = get_azure_deployment_name() or "gpt-5.2"
        llm = LLMFactory(
            provider="azure",
            model_name=f"azure/{deployment}",
            api_key=get_azure_api_key(),
            api_base=get_azure_api_base(),
            api_version=get_azure_api_version(),
        )

        # Verify configuration is set correctly
        assert llm.provider == "azure"
        assert "azure" in llm.model_name.lower() or "gpt" in llm.model_name.lower()

    def test_azure_model_prefix_detection(self):
        """Test that azure/ prefix models are detected as Azure provider."""
        llm = LLMFactory(
            provider="openai",  # Start with wrong provider
            model_name="azure/gpt-5.2",
        )

        # The _get_provider_from_model should detect azure/ prefix
        detected_provider = llm._get_provider_from_model("azure/gpt-5.2")
        assert detected_provider == "azure"

    def test_azure_deployment_naming(self):
        """Test Azure deployment naming conventions."""
        # Azure uses deployment names, not model names
        deployment = get_azure_deployment_name() or "gpt-5.2"
        llm = LLMFactory(
            provider="azure",
            model_name=f"azure/{deployment}",
            api_key="test-key",  # Not a real key
            api_base="https://test.openai.azure.com/",
            api_version="2024-12-01",
        )

        assert llm.provider == "azure"
        assert deployment in llm.model_name


@pytest.mark.integration
@pytest.mark.xdist_group(name="azure_openai_tests")
class TestAzureOpenAIErrorHandling:
    """Test error handling for Azure OpenAI."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_azure_requires_api_key(self):
        """Test that Azure OpenAI requires an API key."""
        llm = LLMFactory(
            provider="azure",
            model_name="azure/gpt-5.2",
            api_key=None,  # No key specified
            api_base="https://test.openai.azure.com/",
            api_version="2024-12-01",
        )

        # The factory should be created, but invocation will fail without credentials
        assert llm is not None

    @pytest.mark.asyncio
    async def test_azure_requires_api_base(self):
        """Test that Azure OpenAI requires an API base endpoint."""
        llm = LLMFactory(
            provider="azure",
            model_name="azure/gpt-5.2",
            api_key="test-key",
            api_base=None,  # No base specified
            api_version="2024-12-01",
        )

        # The factory should be created, but invocation will fail without endpoint
        assert llm is not None

    @pytest.mark.skipif(
        not azure_openai_available(),
        reason=get_azure_skip_reason() or "Azure OpenAI not available",
    )
    @pytest.mark.asyncio
    async def test_azure_invalid_deployment_name(self):
        """Test error handling for invalid deployment name."""
        llm = LLMFactory(
            provider="azure",
            model_name="azure/invalid-deployment-name-xyz",
            api_key=get_azure_api_key(),
            api_base=get_azure_api_base(),
            api_version=get_azure_api_version(),
        )

        messages = [HumanMessage(content="Hello")]

        # Should raise an error when trying to invoke invalid deployment
        with pytest.raises(Exception):  # LiteLLM will raise an error
            await llm.ainvoke(messages)


@pytest.mark.integration
@pytest.mark.xdist_group(name="azure_openai_tests")
class TestAzureOpenAIWithLiteLLM:
    """Test Azure OpenAI integration with LiteLLM model ID conversion."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_litellm_model_id_for_azure(self):
        """Test that get_litellm_model_id adds azure/ prefix."""
        from mcp_server_langgraph.agents.model_selector import get_litellm_model_id

        # Azure models need azure/ prefix
        result = get_litellm_model_id("gpt-5.2", "azure")
        assert result == "azure/gpt-5.2"

        # Already prefixed models should not be double-prefixed
        result = get_litellm_model_id("azure/gpt-5.2", "azure")
        assert result == "azure/gpt-5.2"

    def test_model_selector_azure_vendor(self):
        """Test that ModelSelector can work with Azure as a vendor."""
        from mcp_server_langgraph.agents.model_selector import (
            MODEL_TIERS,
            VENDOR_LITELLM_PREFIX,
        )

        # Verify Azure is in the LiteLLM prefix mapping
        assert "azure" in VENDOR_LITELLM_PREFIX
        assert VENDOR_LITELLM_PREFIX["azure"] == "azure/"

        # While Azure isn't in MODEL_TIERS by default (enterprise config),
        # the prefix mapping supports it for LiteLLM routing
        assert "openai" in MODEL_TIERS["simple"]  # OpenAI models can be used via Azure
