"""
Test LiteLLM fallback kwargs forwarding.

Ensures that provider-specific kwargs (api_base, aws_secret_access_key, etc.)
are properly forwarded to fallback models.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from mcp_server_langgraph.llm.factory import LLMFactory


@pytest.fixture
def mock_litellm_responses():
    """Mock LiteLLM responses."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Test response"
    response.usage = MagicMock()
    response.usage.total_tokens = 10
    return response


@pytest.mark.unit
def test_fallback_forwards_kwargs_sync(mock_litellm_responses):
    """Test that sync fallback forwards provider-specific kwargs."""
    # Test Azure-specific kwargs
    azure_kwargs = {
        "api_base": "https://my-azure-endpoint.openai.azure.com",
        "api_version": "2024-02-15-preview",
    }

    factory = LLMFactory(
        provider="azure",
        model_name="gpt-4",
        api_key="test-key",
        enable_fallback=True,
        fallback_models=["gpt-3.5-turbo"],
        **azure_kwargs,
    )

    messages = [HumanMessage(content="test message")]

    # Mock completion to fail on primary, succeed on fallback
    with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
        # First call (primary) fails
        # Second call (fallback) succeeds
        mock_completion.side_effect = [Exception("Primary failed"), mock_litellm_responses]

        result = factory.invoke(messages)

        # Should have tried twice (primary + fallback)
        assert mock_completion.call_count == 2

        # Check that fallback call received the provider-specific kwargs
        fallback_call = mock_completion.call_args_list[1]
        assert fallback_call[1]["api_base"] == azure_kwargs["api_base"]
        assert fallback_call[1]["api_version"] == azure_kwargs["api_version"]
        assert fallback_call[1]["model"] == "gpt-3.5-turbo"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_forwards_kwargs_async(mock_litellm_responses):
    """Test that async fallback forwards provider-specific kwargs."""
    # Test Bedrock-specific kwargs
    bedrock_kwargs = {
        "aws_secret_access_key": "test-secret-key",
        "aws_region_name": "us-west-2",
    }

    factory = LLMFactory(
        provider="bedrock",
        model_name="anthropic.claude-v2",
        api_key="test-access-key",
        enable_fallback=True,
        fallback_models=["anthropic.claude-instant-v1"],
        **bedrock_kwargs,
    )

    messages = [HumanMessage(content="test message")]

    # Mock acompletion to fail on primary, succeed on fallback
    with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
        # First call (primary) fails
        # Second call (fallback) succeeds
        mock_acompletion.side_effect = [Exception("Primary failed"), mock_litellm_responses]

        result = await factory.ainvoke(messages)

        # Should have tried twice (primary + fallback)
        assert mock_acompletion.call_count == 2

        # Check that fallback call received the provider-specific kwargs
        fallback_call = mock_acompletion.call_args_list[1]
        assert fallback_call[1]["aws_secret_access_key"] == bedrock_kwargs["aws_secret_access_key"]
        assert fallback_call[1]["aws_region_name"] == bedrock_kwargs["aws_region_name"]
        assert fallback_call[1]["model"] == "anthropic.claude-instant-v1"


@pytest.mark.unit
def test_fallback_forwards_ollama_kwargs_sync(mock_litellm_responses):
    """Test that sync fallback forwards Ollama-specific kwargs."""
    ollama_kwargs = {
        "api_base": "http://localhost:11434",
    }

    factory = LLMFactory(
        provider="ollama",
        model_name="llama3.1:8b",
        enable_fallback=True,
        fallback_models=["qwen2.5:7b"],
        **ollama_kwargs,
    )

    messages = [HumanMessage(content="test message")]

    with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
        mock_completion.side_effect = [Exception("Primary failed"), mock_litellm_responses]

        result = factory.invoke(messages)

        assert mock_completion.call_count == 2

        # Check that fallback call received the api_base
        fallback_call = mock_completion.call_args_list[1]
        assert fallback_call[1]["api_base"] == ollama_kwargs["api_base"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_forwards_ollama_kwargs_async(mock_litellm_responses):
    """Test that async fallback forwards Ollama-specific kwargs."""
    ollama_kwargs = {
        "api_base": "http://localhost:11434",
    }

    factory = LLMFactory(
        provider="ollama",
        model_name="llama3.1:8b",
        enable_fallback=True,
        fallback_models=["qwen2.5:7b"],
        **ollama_kwargs,
    )

    messages = [HumanMessage(content="test message")]

    with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = [Exception("Primary failed"), mock_litellm_responses]

        result = await factory.ainvoke(messages)

        assert mock_acompletion.call_count == 2

        # Check that fallback call received the api_base
        fallback_call = mock_acompletion.call_args_list[1]
        assert fallback_call[1]["api_base"] == ollama_kwargs["api_base"]
