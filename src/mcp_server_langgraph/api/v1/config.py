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

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.config import settings

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

    Example Response:
        {
            "model_name": "gemini-2.5-flash",
            "model_provider": "google",
            "max_tokens": 8192,
            "temperature": 0.7
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
    }
