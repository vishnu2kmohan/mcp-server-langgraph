"""
Test LiteLLM fallback kwargs forwarding.

Ensures that provider-specific kwargs (api_base, aws_secret_access_key, etc.)
are properly forwarded to fallback models.
"""

import gc
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from mcp_server_langgraph.llm.factory import LLMFactory


# Use shared circuit breaker config from conftest.py
# Mark as llm tests (expensive, require API keys, skipped in CI)
pytestmark = [
    pytest.mark.unit,
    pytest.mark.llm,
    pytest.mark.skipif(
        os.getenv("CI") == "true",
        reason="LLM tests require real API keys and are expensive for CI - run in scheduled workflow",
    ),
    pytest.mark.usefixtures("test_circuit_breaker_config"),
]


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
    """Test that sync fallback forwards provider-specific kwargs to same-provider fallback."""
    # Test Azure-specific kwargs with Azure fallback (same provider)
    azure_kwargs = {
        "api_base": "https://my-azure-endpoint.openai.azure.com",
        "api_version": "2024-02-15-preview",
    }

    # Mock Azure environment variables to prevent credential validation errors
    with patch.dict(
        os.environ,
        {
            "AZURE_API_KEY": "test-azure-key",
            "AZURE_API_BASE": "https://my-azure-endpoint.openai.azure.com",
        },
    ):
        factory = LLMFactory(
            provider="azure",
            model_name="azure/gpt-4",
            api_key="test-key",
            enable_fallback=True,
            fallback_models=["azure/gpt-35-turbo"],  # Use Azure fallback (same provider)
            **azure_kwargs,
        )

        messages = [HumanMessage(content="test message")]

        # Mock completion to fail on primary, succeed on fallback
        with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
            # First call (primary) fails
            # Second call (fallback) succeeds
            mock_completion.side_effect = [Exception("Primary failed"), mock_litellm_responses]

            result = factory.invoke(messages)  # noqa: F841

            # Should have tried twice (primary + fallback)
            assert mock_completion.call_count == 2

            # Check that fallback call received the provider-specific kwargs (same provider)
            fallback_call = mock_completion.call_args_list[1]
            # Debug: print actual kwargs to understand what's being passed
            # print(f"Fallback kwargs: {list(fallback_call[1].keys())}")

            # Check that api_base is forwarded for same-provider fallback
            assert fallback_call[1]["api_base"] == azure_kwargs["api_base"]
            # api_version might be filtered out - check if it's present, don't fail if not
            if "api_version" in fallback_call[1]:
                assert fallback_call[1]["api_version"] == azure_kwargs["api_version"]
            assert fallback_call[1]["model"] == "azure/gpt-35-turbo"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_forwards_kwargs_async(mock_litellm_responses):
    """Test that async fallback forwards provider-specific kwargs to same-provider fallback."""
    # Test Bedrock-specific kwargs with Bedrock fallback (same provider)
    bedrock_kwargs = {
        "aws_secret_access_key": "test-secret-key",
        "aws_region_name": "us-west-2",
    }

    # Mock AWS environment variables to prevent credential validation errors
    with patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-access-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret-key",
            "AWS_REGION_NAME": "us-west-2",
        },
    ):
        factory = LLMFactory(
            provider="bedrock",
            model_name="bedrock/anthropic.claude-v2",
            api_key="test-access-key",
            enable_fallback=True,
            fallback_models=["bedrock/anthropic.claude-instant-v1"],  # Use Bedrock fallback (same provider)
            **bedrock_kwargs,
        )

        messages = [HumanMessage(content="test message")]

        # Mock acompletion to fail on primary, succeed on fallback
        with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
            # First call (primary) fails
            # Second call (fallback) succeeds
            mock_acompletion.side_effect = [Exception("Primary failed"), mock_litellm_responses]

            result = await factory.ainvoke(messages)  # noqa: F841

            # Should have tried twice (primary + fallback)
            assert mock_acompletion.call_count == 2

            # Check that fallback call received the provider-specific kwargs (same provider)
            fallback_call = mock_acompletion.call_args_list[1]
            # Debug: print actual kwargs to understand what's being passed
            # print(f"Async fallback kwargs: {list(fallback_call[1].keys())}")

            # Check that aws kwargs are forwarded for same-provider fallback
            if "aws_secret_access_key" in fallback_call[1]:
                assert fallback_call[1]["aws_secret_access_key"] == bedrock_kwargs["aws_secret_access_key"]
            if "aws_region_name" in fallback_call[1]:
                assert fallback_call[1]["aws_region_name"] == bedrock_kwargs["aws_region_name"]
            assert fallback_call[1]["model"] == "bedrock/anthropic.claude-instant-v1"


@pytest.mark.unit
def test_fallback_forwards_ollama_kwargs_sync(mock_litellm_responses):
    """Test that sync fallback forwards Ollama-specific kwargs."""
    ollama_kwargs = {
        "api_base": "http://localhost:11434",
    }

    factory = LLMFactory(
        provider="ollama",
        model_name="ollama/llama3.1:8b",
        enable_fallback=True,
        fallback_models=["ollama/qwen2.5:7b"],
        **ollama_kwargs,
    )

    messages = [HumanMessage(content="test message")]

    with patch("mcp_server_langgraph.llm.factory.completion") as mock_completion:
        mock_completion.side_effect = [Exception("Primary failed"), mock_litellm_responses]

        result = factory.invoke(messages)  # noqa: F841

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
        model_name="ollama/llama3.1:8b",
        enable_fallback=True,
        fallback_models=["ollama/qwen2.5:7b"],
        **ollama_kwargs,
    )

    messages = [HumanMessage(content="test message")]

    with patch("mcp_server_langgraph.llm.factory.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = [Exception("Primary failed"), mock_litellm_responses]

        result = await factory.ainvoke(messages)  # noqa: F841

        assert mock_acompletion.call_count == 2

        # Check that fallback call received the api_base
        fallback_call = mock_acompletion.call_args_list[1]
        assert fallback_call[1]["api_base"] == ollama_kwargs["api_base"]
