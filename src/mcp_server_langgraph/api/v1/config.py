"""
Config Router

Exposes server configuration defaults to the frontend for hydration.

This endpoint follows 12-Factor App principles (III. Config):
- Configuration is stored in the environment, not in code
- Frontend fetches configuration from backend at startup
- Single source of truth for LLM model, max tokens, etc.

Usage:
    GET /api/v1/config/defaults - Get server default configuration
"""

import warnings
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from mcp_server_langgraph.agents.model_registry import get_default_registry
from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.core.feature_flags import feature_flags

# Type alias for current user
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

config_router = APIRouter(tags=["config"])


def _infer_model_provider(model_name: str) -> str:
    """
    Infer the model provider from the model name.

    Args:
        model_name: The model name to analyze

    Returns:
        Provider string: "openai", "anthropic", "google", "azure", or "unknown"
    """
    model_lower = model_name.lower()

    # Azure models (prefixed with azure/) - check first since azure/gpt-4 contains "gpt-"
    if model_lower.startswith("azure/"):
        return "azure"

    # OpenAI models
    if any(prefix in model_lower for prefix in ["gpt-", "o1-", "chatgpt-", "text-davinci", "text-embedding"]):
        return "openai"

    # Anthropic models
    if any(prefix in model_lower for prefix in ["claude-", "claude3"]):
        return "anthropic"

    # Google models
    if any(prefix in model_lower for prefix in ["gemini-", "palm-", "bison", "gecko"]):
        return "google"

    return "unknown"


# =============================================================================
# Available Models Configuration
# =============================================================================

# Models that support extended thinking (chain-of-thought reasoning)
THINKING_CAPABLE_MODELS = frozenset(
    {
        "claude-3-5-sonnet",
        "claude-3-opus",
        "claude-sonnet-4-5",
        "claude-sonnet-4-0",
        "o1-preview",
        "o1-mini",
    }
)

# =============================================================================
# DEPRECATED: AVAILABLE_MODELS will be removed in v3.0.0
# =============================================================================
#
# This hardcoded list is deprecated. The ModelRegistry is now the single source
# of truth for model options. This list is only used as a fallback when
# FF_USE_MODEL_REGISTRY_FOR_FRONTEND=false.
#
# Removal Plan:
#   - v2.9.0: Feature flag defaults to True (current state)
#   - v2.10.0: Feature flag removed, ModelRegistry always used
#   - v3.0.0: AVAILABLE_MODELS list and THINKING_CAPABLE_MODELS removed
#
# Migration: The ModelRegistry provides:
#   - All model capabilities (vision, tools, thinking, effort_param, json_mode)
#   - Model lifecycle status (current, preview, legacy, deprecated)
#   - Sunset dates for deprecated models
#   - Vendor deduplication (Vertex AI variants → single entry)
#   - Consistent frontend/backend model data
#
# See:
#   - src/mcp_server_langgraph/agents/model_registry.py
#   - ADR-0102: Enhanced Model Selector Architecture
#   - docs/guides/model-lifecycle.mdx
#
# To use ModelRegistry, ensure FF_USE_MODEL_REGISTRY_FOR_FRONTEND=true (default)
AVAILABLE_MODELS = [
    # Anthropic models
    {
        "id": "claude-3-5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "supports_thinking": True,
        "supports_vision": True,
        "supports_tools": True,
    },
    {
        "id": "claude-3-opus",
        "name": "Claude 3 Opus",
        "provider": "anthropic",
        "supports_thinking": True,
        "supports_vision": True,
        "supports_tools": True,
    },
    {
        "id": "claude-3-haiku",
        "name": "Claude 3 Haiku",
        "provider": "anthropic",
        "supports_thinking": False,
        "supports_vision": True,
        "supports_tools": True,
    },
    {
        "id": "claude-sonnet-4-5",
        "name": "Claude Sonnet 4.5",
        "provider": "anthropic",
        "supports_thinking": True,
        "supports_vision": True,
        "supports_tools": True,
    },
    # OpenAI models
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "supports_thinking": False,
        "supports_vision": True,
        "supports_tools": True,
    },
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "openai",
        "supports_thinking": False,
        "supports_vision": True,
        "supports_tools": True,
    },
    {
        "id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "supports_thinking": False,
        "supports_vision": True,
        "supports_tools": True,
    },
    {
        "id": "o1-preview",
        "name": "o1 Preview",
        "provider": "openai",
        "supports_thinking": True,
        "supports_vision": False,  # o1 models don't support vision
        "supports_tools": False,  # o1 models have limited tool support
    },
    {
        "id": "o1-mini",
        "name": "o1 Mini",
        "provider": "openai",
        "supports_thinking": True,
        "supports_vision": False,  # o1 models don't support vision
        "supports_tools": False,  # o1 models have limited tool support
    },
    # Google models
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "provider": "google",
        "supports_thinking": False,
        "supports_vision": True,
        "supports_tools": True,
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "provider": "google",
        "supports_thinking": False,
        "supports_vision": True,
        "supports_tools": True,
    },
    {
        "id": "gemini-pro",
        "name": "Gemini Pro",
        "provider": "google",
        "supports_thinking": False,
        "supports_vision": True,
        "supports_tools": True,
    },
]


@config_router.get("/config/models")
async def get_available_models(current_user: CurrentUser) -> list[dict]:
    """
    Get available LLM models for selection in the frontend.

    Returns a list of model options with their metadata, including:
    - id: Unique identifier for the model
    - name: Human-readable display name
    - provider: The LLM provider (anthropic, openai, google)
    - supports_thinking: Whether the model supports extended thinking
    - supports_vision: Whether the model supports image inputs
    - supports_tools: Whether the model supports tool/function calling
    - isDefault: Whether this is the default model (from settings.model_name)

    This endpoint provides the single source of truth for model options,
    ensuring frontend model selectors reflect actual backend capabilities.

    When FF_USE_MODEL_REGISTRY_FOR_FRONTEND is enabled, uses ModelRegistry
    as the single source of truth instead of hardcoded AVAILABLE_MODELS.

    12-Factor App Compliance:
    - Default model is determined by settings.model_name (env: MODEL_NAME)
    - Frontend should NOT hardcode default model - use isDefault from this API

    Returns:
        List of model dictionaries with id, name, provider, supports_thinking,
        supports_vision, supports_tools, isDefault

    Example Response:
        [
            {
                "id": "gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "provider": "google",
                "supports_thinking": true,
                "supports_vision": true,
                "supports_tools": true,
                "isDefault": true
            },
            ...
        ]
    """
    # Get the default model from settings (12-Factor: config from environment)
    # Use exact matching - no normalization to preserve explicit provider+model specification
    default_model_id = settings.model_name

    if feature_flags.use_model_registry_for_frontend:
        registry = get_default_registry()
        # Pass default_model_id to mark the correct model as default
        models = registry.get_frontend_models(default_model_id=default_model_id)
        return models

    # Emit deprecation warning when legacy AVAILABLE_MODELS is used
    warnings.warn(
        "AVAILABLE_MODELS is deprecated and will be removed in v3.0.0. "
        "Set FF_USE_MODEL_REGISTRY_FOR_FRONTEND=true (now default) to use "
        "ModelRegistry.get_frontend_models() instead. "
        "See: ADR-0102, src/mcp_server_langgraph/agents/model_registry.py",
        DeprecationWarning,
        stacklevel=2,
    )

    # Mark default for legacy AVAILABLE_MODELS - exact match
    models = [dict(m) for m in AVAILABLE_MODELS]  # Copy to avoid mutation
    for model in models:
        model["isDefault"] = model.get("id", "") == default_model_id

    return models


@config_router.get("/config/defaults")
async def get_defaults(current_user: CurrentUser) -> dict:
    """
    Get server default configuration for frontend hydration.

    Returns a dictionary containing the default configuration values
    sourced from the server's environment configuration (settings).

    This endpoint is critical for 12-Factor App compliance:
    - Frontend should fetch this at startup
    - Values come from environment/settings, not hardcoded
    - Ensures frontend reflects actual backend configuration

    Returns:
        Dictionary with:
        - model_name: Default LLM model name from settings
        - model_provider: Inferred provider (openai, anthropic, google, azure)
        - max_tokens: Default max tokens from settings
        - temperature: Default temperature (0.7)
        - executor_model_name: Optional override for executor model (critique loop)
        - critic_model_name: Optional override for critic model (critique loop)
        - critique_loop_enabled: Whether the critique loop feature is enabled

    Example Response:
        {
            "model_name": "gemini-2.5-flash",
            "model_provider": "google",
            "max_tokens": 8192,
            "temperature": 0.7,
            "executor_model_name": null,
            "critic_model_name": null,
            "critique_loop_enabled": false
        }
    """
    model_name = settings.model_name
    model_provider = _infer_model_provider(model_name)

    # Get temperature from settings if available, otherwise default
    temperature = getattr(settings, "temperature", 0.7)

    return {
        "model_name": model_name,
        "model_provider": model_provider,
        "max_tokens": settings.model_max_tokens,
        "temperature": temperature,
        # Executor/Critic model configuration (for critique loop)
        "executor_model_name": settings.executor_model_name,
        "critic_model_name": settings.critic_model_name,
        "critique_loop_enabled": feature_flags.enable_critique_loop,
    }
