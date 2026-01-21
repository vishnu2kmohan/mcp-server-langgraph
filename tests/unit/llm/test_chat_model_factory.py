"""
Tests for llm/chat_model_factory.py module.

TDD: These tests define the expected behavior for the LangChain ChatModel factory.
These tests use mocking to avoid requiring actual LangChain provider packages.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestChatModelFactoryProviderSelection:
    """Tests for provider selection logic in chat_model_factory."""

    def test_anthropic_provider_selection(self) -> None:
        """Anthropic provider should call _create_anthropic_model."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.model_name = "claude-3-5-sonnet"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_anthropic_model"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            mock_create.assert_called_once()
            args = mock_create.call_args
            assert args[0][0] == mock_settings  # settings
            assert args[0][1] == "claude-3-5-sonnet"  # model_name

    def test_openai_provider_selection(self) -> None:
        """OpenAI provider should call _create_openai_model."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "openai"
        mock_settings.model_name = "gpt-4o"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_openai_model"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            mock_create.assert_called_once()

    def test_google_provider_selection(self) -> None:
        """Google provider should call _create_google_model."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "google"
        mock_settings.model_name = "gemini-2.5-flash"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_google_model"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            mock_create.assert_called_once()

    def test_azure_provider_selection(self) -> None:
        """Azure provider should call _create_azure_model."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "azure"
        mock_settings.model_name = "gpt-4o"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_azure_model"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            mock_create.assert_called_once()

    def test_vertex_ai_provider_selection(self) -> None:
        """Vertex AI provider should call _create_vertex_ai_model."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "vertex_ai"
        mock_settings.model_name = "gemini-3-flash"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_vertex_ai_model"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            mock_create.assert_called_once()


@pytest.mark.unit
class TestChatModelFactoryVertexAI:
    """Tests for Vertex AI model name handling."""

    def test_vertex_ai_strips_prefix(self) -> None:
        """Vertex AI should strip vertex_ai/ prefix from model name."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "vertex_ai"
        mock_settings.model_name = "vertex_ai/gemini-3-flash"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_vertex_ai_model"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            # Second argument should be the stripped model name
            args = mock_create.call_args
            assert args[0][1] == "gemini-3-flash"

    def test_vertex_ai_claude_uses_litellm(self) -> None:
        """Vertex AI with Claude model should use LiteLLM adapter."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "vertex_ai"
        mock_settings.model_name = "claude-3-5-sonnet"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_litellm_adapter"
        ) as mock_adapter:
            mock_adapter.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            mock_adapter.assert_called_once()


@pytest.mark.unit
class TestChatModelFactoryFallback:
    """Tests for LiteLLM adapter fallback."""

    def test_unsupported_provider_uses_litellm(self) -> None:
        """Unsupported providers should fall back to LiteLLM adapter."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "bedrock"
        mock_settings.model_name = "claude-3"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_litellm_adapter"
        ) as mock_adapter:
            mock_adapter.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            mock_adapter.assert_called_once()

    def test_ollama_provider_uses_litellm(self) -> None:
        """Ollama provider should use LiteLLM adapter."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "ollama"
        mock_settings.model_name = "llama3"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_litellm_adapter"
        ) as mock_adapter:
            mock_adapter.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            mock_adapter.assert_called_once()


@pytest.mark.unit
class TestChatModelFactoryStreaming:
    """Tests for streaming parameter handling."""

    def test_streaming_enabled_by_default(self) -> None:
        """Streaming should be enabled by default."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.model_name = "claude-3-5-sonnet"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_anthropic_model"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings)

            # Check enable_streaming argument
            args = mock_create.call_args
            assert args[0][2] is True  # enable_streaming

    def test_streaming_can_be_disabled(self) -> None:
        """Streaming can be disabled via parameter."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.model_name = "claude-3-5-sonnet"

        with patch(
            "mcp_server_langgraph.llm.chat_model_factory._create_anthropic_model"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            from mcp_server_langgraph.llm.chat_model_factory import (
                create_chat_model_from_config,
            )

            create_chat_model_from_config(mock_settings, enable_streaming=False)

            # Check enable_streaming argument
            args = mock_create.call_args
            assert args[0][2] is False  # enable_streaming
