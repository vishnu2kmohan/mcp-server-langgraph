"""
LangChain Chat Model Factory.

Creates provider-specific ChatModel instances with correct settings mapping.
NOTE: Does NOT include hooks - use HookedChatModel wrapper for that.

This factory provides a unified interface for creating LangChain chat models
across different providers while respecting the Settings configuration.

Supported Providers:
- anthropic: ChatAnthropic (langchain-anthropic)
- openai: ChatOpenAI (langchain-openai)
- google: ChatGoogleGenerativeAI (langchain-google-genai)
- vertex_ai: ChatVertexAI (langchain-google-vertexai)
- azure: AzureChatOpenAI (langchain-openai)
- Others: LiteLLM adapter fallback
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from mcp_server_langgraph.core.config import Settings

from mcp_server_langgraph.observability.telemetry import logger


def create_chat_model_from_config(
    settings: "Settings",
    *,
    enable_streaming: bool = True,
) -> "BaseChatModel":
    """Create LangChain chat model with correct settings mapping.

    This function creates a provider-specific LangChain ChatModel instance
    based on the configured LLM provider and settings.

    Args:
        settings: Application settings containing LLM configuration
        enable_streaming: Whether to enable streaming responses (default: True)

    Returns:
        Configured BaseChatModel instance for the specified provider

    Example:
        ```python
        from mcp_server_langgraph.core.config import get_settings
        from mcp_server_langgraph.llm.chat_model_factory import create_chat_model_from_config

        settings = get_settings()
        model = create_chat_model_from_config(settings)
        response = await model.ainvoke([HumanMessage(content="Hello")])
        ```
    """
    provider = settings.llm_provider.lower()
    model_name = settings.model_name

    # Normalize Vertex AI model names (strip prefix)
    if provider == "vertex_ai" and model_name.startswith("vertex_ai/"):
        model_name = model_name[len("vertex_ai/") :]

    # Route Anthropic-on-Vertex to LiteLLM (ChatVertexAI doesn't support Claude)
    if provider == "vertex_ai" and "claude" in model_name.lower():
        logger.info(f"Routing {model_name} to LiteLLM for Anthropic-on-Vertex")
        return _create_litellm_adapter(settings)

    if provider == "anthropic":
        return _create_anthropic_model(settings, model_name, enable_streaming)

    elif provider == "google":
        return _create_google_model(settings, model_name)

    elif provider == "vertex_ai":
        return _create_vertex_ai_model(settings, model_name, enable_streaming)

    elif provider == "openai":
        return _create_openai_model(settings, model_name, enable_streaming)

    elif provider == "azure":
        return _create_azure_model(settings, enable_streaming)

    else:
        # Fallback for unsupported providers: bedrock, ollama, etc.
        logger.info(f"Using LiteLLM adapter for provider: {provider}")
        return _create_litellm_adapter(settings)


def _create_anthropic_model(
    settings: "Settings", model_name: str, enable_streaming: bool
) -> "BaseChatModel":
    """Create Anthropic ChatModel."""
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=model_name,
        temperature=settings.model_temperature,
        max_tokens=settings.model_max_tokens,
        streaming=enable_streaming,
        anthropic_api_key=settings.anthropic_api_key,
        timeout=settings.model_timeout,
    )


def _create_google_model(settings: "Settings", model_name: str) -> "BaseChatModel":
    """Create Google Generative AI ChatModel."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=settings.model_temperature,
        max_output_tokens=settings.model_max_tokens,
        google_api_key=settings.google_api_key,
    )


def _create_vertex_ai_model(
    settings: "Settings", model_name: str, enable_streaming: bool
) -> "BaseChatModel":
    """Create Vertex AI ChatModel."""
    from langchain_google_vertexai import ChatVertexAI

    return ChatVertexAI(
        model=model_name,
        temperature=settings.model_temperature,
        max_output_tokens=settings.model_max_tokens,
        project=settings.vertex_project,
        location=settings.vertex_location,
        streaming=enable_streaming,
    )


def _create_openai_model(
    settings: "Settings", model_name: str, enable_streaming: bool
) -> "BaseChatModel":
    """Create OpenAI ChatModel."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model_name,
        temperature=settings.model_temperature,
        max_tokens=settings.model_max_tokens,
        streaming=enable_streaming,
        openai_api_key=settings.openai_api_key,
    )


def _create_azure_model(settings: "Settings", enable_streaming: bool) -> "BaseChatModel":
    """Create Azure OpenAI ChatModel."""
    from langchain_openai import AzureChatOpenAI

    return AzureChatOpenAI(
        azure_deployment=settings.azure_deployment_name,
        temperature=settings.model_temperature,
        max_tokens=settings.model_max_tokens,
        streaming=enable_streaming,
        azure_endpoint=settings.azure_api_base,
        api_key=settings.azure_api_key,
        api_version=settings.azure_api_version,
    )


def _create_litellm_adapter(settings: "Settings") -> "BaseChatModel":
    """Create LiteLLM-backed ChatModel for unsupported providers.

    Uses ChatLiteLLM from langchain-community as a fallback for providers
    that don't have native LangChain integrations.
    """
    try:
        from langchain_community.chat_models import ChatLiteLLM

        return ChatLiteLLM(
            model=settings.model_name,
            temperature=settings.model_temperature,
            max_tokens=settings.model_max_tokens,
        )
    except ImportError:
        # If langchain-community not available, use a minimal adapter
        from mcp_server_langgraph.llm.litellm_chat_model import LiteLLMChatModel

        return LiteLLMChatModel(settings)
