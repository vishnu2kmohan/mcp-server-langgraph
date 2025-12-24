"""
LLM Provider Registry

Provides metadata about all supported LLM providers in the system.

Sprint 1 of Enhanced Agents Page Implementation Plan:
- SUPPORTED_PROVIDERS: Dictionary of all supported LLM providers
- ProviderInfo: Pydantic model for provider metadata
- get_provider_info: Get info for a specific provider
- get_all_providers: Get list of all provider infos

Usage:
    from mcp_server_langgraph.llm.providers import (
        SUPPORTED_PROVIDERS,
        get_provider_info,
        get_all_providers,
    )

    # Get specific provider info
    info = get_provider_info("anthropic")
    if info:
        print(f"API key env: {info.api_key_env_var}")

    # Get all providers
    all_providers = get_all_providers()
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderInfo(BaseModel):
    """Metadata about an LLM provider.

    Used for displaying provider information in the agents page
    and for understanding provider capabilities.
    """

    name: str = Field(..., description="Provider identifier (e.g., 'anthropic')")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Description of the provider")
    supported_model_types: list[str] = Field(
        default_factory=list,
        description="Model types this provider supports (primary, summarization, verification)",
    )
    requires_api_key: bool = Field(
        default=True,
        description="Whether this provider requires an API key",
    )
    api_key_env_var: str | None = Field(
        default=None,
        description="Environment variable name for API key",
    )


# =============================================================================
# SUPPORTED_PROVIDERS
# =============================================================================
# Registry of all LLM providers supported by the system.
# Matches the providers in core/config/_settings.py:llm_provider
# =============================================================================

SUPPORTED_PROVIDERS: dict[str, ProviderInfo] = {
    "google": ProviderInfo(
        name="google",
        display_name="Google Gemini",
        description="Google's Gemini AI models including Gemini 2.5 Flash and Pro",
        supported_model_types=["primary", "summarization", "verification"],
        requires_api_key=True,
        api_key_env_var="GOOGLE_API_KEY",
    ),
    "anthropic": ProviderInfo(
        name="anthropic",
        display_name="Anthropic Claude",
        description="Anthropic's Claude AI models including Claude 3.5 Sonnet and Opus 4.5",
        supported_model_types=["primary", "summarization", "verification"],
        requires_api_key=True,
        api_key_env_var="ANTHROPIC_API_KEY",
    ),
    "openai": ProviderInfo(
        name="openai",
        display_name="OpenAI GPT",
        description="OpenAI's GPT models including GPT-4o and GPT-5",
        supported_model_types=["primary", "summarization", "verification"],
        requires_api_key=True,
        api_key_env_var="OPENAI_API_KEY",
    ),
    "azure": ProviderInfo(
        name="azure",
        display_name="Azure OpenAI",
        description="Microsoft Azure-hosted OpenAI models",
        supported_model_types=["primary", "summarization", "verification"],
        requires_api_key=True,
        api_key_env_var="AZURE_API_KEY",
    ),
    "bedrock": ProviderInfo(
        name="bedrock",
        display_name="AWS Bedrock",
        description="AWS Bedrock for Anthropic Claude and other models",
        supported_model_types=["primary", "summarization", "verification"],
        requires_api_key=True,
        api_key_env_var="AWS_ACCESS_KEY_ID",
    ),
    "vertex_ai": ProviderInfo(
        name="vertex_ai",
        display_name="Google Vertex AI",
        description="Google Cloud Vertex AI for enterprise deployments",
        supported_model_types=["primary", "summarization", "verification"],
        requires_api_key=True,
        api_key_env_var="GOOGLE_APPLICATION_CREDENTIALS",
    ),
    "ollama": ProviderInfo(
        name="ollama",
        display_name="Ollama (Local)",
        description="Local LLM inference via Ollama for offline/private deployments",
        supported_model_types=["primary"],
        requires_api_key=False,
        api_key_env_var=None,
    ),
}


def get_provider_info(name: str) -> ProviderInfo | None:
    """Get provider info by name.

    Args:
        name: Provider identifier (e.g., "anthropic")

    Returns:
        ProviderInfo if found, None otherwise
    """
    return SUPPORTED_PROVIDERS.get(name)


def get_all_providers() -> list[ProviderInfo]:
    """Get list of all supported providers.

    Returns:
        List of ProviderInfo for all supported providers
    """
    return list(SUPPORTED_PROVIDERS.values())
