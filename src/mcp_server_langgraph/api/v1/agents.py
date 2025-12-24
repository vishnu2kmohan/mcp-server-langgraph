"""
Agents Config Router

Provides agent configuration under /api/v1/agents/*.

This endpoint returns the current agent configuration including:
- Model name and provider (from core/config.py)
- Temperature settings
- Verification settings (human-in-loop)
- Registered tools from MCP server
- Thinking budget defaults (optional, Sprint 1 extension)
- Feature flags snapshot (optional, Sprint 1 extension)

Usage:
    GET /api/v1/agents/config - Get current agent configuration
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from mcp_server_langgraph.agents.registry import OrchestratorInfo, get_all_orchestrators
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.llm.providers import ProviderInfo, get_all_providers
from mcp_server_langgraph.observability.telemetry import logger

agents_router = APIRouter(prefix="/agents", tags=["agents"])


# Response Models


class ToolInfo(BaseModel):
    """Tool information for display."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")


class ThinkingLevelInfo(BaseModel):
    """Information about a specific thinking level.

    Provides model-specific behavior for each thinking level:
    - Claude Opus 4.5: Uses native `effort` parameter
    - Other models: Uses `thinking_budget` token count
    """

    level: str = Field(..., description="Thinking level (low, medium, high, ultra)")
    claude_opus_effort: str = Field(
        ...,
        description="Effort parameter for Claude Opus 4.5 (low, medium, high)",
    )
    other_models_tokens: int = Field(
        ...,
        description="Token budget for non-Opus models",
    )
    description: str = Field(..., description="Description of this thinking level")


class ThinkingBudgetDefaults(BaseModel):
    """Thinking budget default configuration.

    Provides unified thinking levels across models:
    - Claude Opus 4.5: Uses native `effort` parameter
    - Other models: Uses `thinking_budget` token count
    """

    enabled: bool = Field(..., description="Whether thinking budget is enabled")
    default_level: str = Field(
        ...,
        description="Default thinking level (low, medium, high, ultra)",
    )
    levels: list[ThinkingLevelInfo] = Field(
        default_factory=list,
        description="Available thinking levels with model-specific behavior",
    )
    complexity_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Task complexity to thinking level mapping",
    )


class AgentConfigResponse(BaseModel):
    """Response model for agent configuration.

    Extended in Sprint 1 with optional fields:
    - thinking_budget_defaults: Thinking level configuration
    - feature_flags_snapshot: Agent-related feature flags
    """

    model: str = Field(..., description="Current model name")
    provider: str = Field(..., description="LLM provider (google, anthropic, openai, etc.)")
    temperature: float = Field(..., ge=0.0, le=2.0, description="Model temperature (0.0-2.0)")
    verification_enabled: bool = Field(..., description="Whether verification/human-in-loop is enabled")
    tools: list[ToolInfo] = Field(default_factory=list, description="List of available tools")

    # Sprint 1 Extensions (optional for backward compatibility)
    thinking_budget_defaults: ThinkingBudgetDefaults | None = Field(
        default=None,
        description="Thinking budget default configuration (optional)",
    )
    feature_flags_snapshot: dict[str, bool] | None = Field(
        default=None,
        description="Snapshot of agent-related feature flags (optional)",
    )
    orchestrators: list[OrchestratorInfo] | None = Field(
        default=None,
        description="List of registered orchestrators with their metadata (optional)",
    )
    providers: list[ProviderInfo] | None = Field(
        default=None,
        description="List of supported LLM providers with their metadata (optional)",
    )


# Valid thinking levels for validation
VALID_THINKING_LEVELS = frozenset({"low", "medium", "high", "ultra"})


class ThinkingBudgetUpdateRequest(BaseModel):
    """Request model for updating thinking budget configuration.

    All fields are optional - only specified fields will be updated.
    """

    default_level: str | None = Field(
        default=None,
        description="Default thinking level (low, medium, high, ultra)",
    )
    enabled: bool | None = Field(
        default=None,
        description="Whether thinking budget is enabled",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate thinking level if provided."""
        if self.default_level is not None and self.default_level not in VALID_THINKING_LEVELS:
            raise ValueError(
                f"Invalid thinking level: {self.default_level}. Must be one of: {', '.join(sorted(VALID_THINKING_LEVELS))}"
            )


class ThinkingBudgetUpdateResponse(BaseModel):
    """Response model for thinking budget update."""

    success: bool = Field(..., description="Whether the update was successful")
    updated_fields: list[str] = Field(
        default_factory=list,
        description="List of fields that were updated",
    )
    current_config: ThinkingBudgetDefaults | None = Field(
        default=None,
        description="Current thinking budget configuration after update",
    )
    message: str | None = Field(
        default=None,
        description="Optional message about the update",
    )


def get_registered_tools() -> list[dict[str, Any]]:
    """
    Get list of registered tools from the MCP server.

    Returns:
        List of tool info dicts with name and description.
    """
    # Import here to avoid circular imports
    # This function may not exist in all deployments - it's dynamically added
    try:
        import mcp_server_langgraph.mcp.server_streamable as mcp_module

        get_registered_tool_definitions = getattr(mcp_module, "get_registered_tool_definitions", None)
        if get_registered_tool_definitions is None:
            return []

        tools = get_registered_tool_definitions()
        return [{"name": t.name, "description": t.description or ""} for t in tools]
    except ImportError:
        logger.warning("Could not import tool definitions from MCP server")
        return []
    except Exception as e:
        logger.warning(f"Error getting registered tools: {e}")
        return []


def get_thinking_budget_defaults() -> ThinkingBudgetDefaults:
    """
    Get thinking budget default configuration from feature flags.

    Returns:
        ThinkingBudgetDefaults with current configuration.
    """
    # Define thinking level info (matching ThinkingBudgetManager constants)
    levels = [
        ThinkingLevelInfo(
            level="low",
            claude_opus_effort="low",
            other_models_tokens=1024,
            description="Quick thinking for simple tasks",
        ),
        ThinkingLevelInfo(
            level="medium",
            claude_opus_effort="medium",
            other_models_tokens=8192,
            description="Standard thinking for most tasks",
        ),
        ThinkingLevelInfo(
            level="high",
            claude_opus_effort="high",
            other_models_tokens=32768,
            description="Deep thinking for complex tasks",
        ),
        ThinkingLevelInfo(
            level="ultra",
            claude_opus_effort="high",  # ULTRA maps to high for Opus
            other_models_tokens=65536,
            description="Maximum thinking for highly complex tasks",
        ),
    ]

    # Complexity to thinking level mapping
    complexity_mapping = {
        "simple": "low",
        "complicated": "medium",
        "complex": "high",
    }

    return ThinkingBudgetDefaults(
        enabled=feature_flags.enable_thinking_budget,
        default_level=feature_flags.default_thinking_level,
        levels=levels,
        complexity_mapping=complexity_mapping,
    )


# Agent-related feature flags to include in snapshot
# These are flags relevant to agent configuration and orchestration
AGENT_FEATURE_FLAGS = [
    "enable_thinking_budget",
    "enable_multi_agent_orchestration",
    "enable_loop_agent",
    "enable_orchestrator_resilience",
    "enable_cost_tracking",
    "enable_sdk_hooks",
    "enable_sdk_interrupt",
    "enable_sdk_structured_output",
    "enable_sdk_agent_definition",
    "enable_handoff_pattern",
    "enable_llm_hooks",
    "enable_session_hooks",
    "enable_tool_examples",
    "enable_think_tool",
    "max_subagents",
    "enable_llm_fallback",
    "enable_agent_memory",
    "max_agent_iterations",
]


def get_agent_feature_flags_snapshot() -> dict[str, bool]:
    """
    Get snapshot of agent-related feature flags.

    Returns:
        Dictionary mapping feature flag names to their current values.
    """
    snapshot: dict[str, bool] = {}
    for flag_name in AGENT_FEATURE_FLAGS:
        value = getattr(feature_flags, flag_name, None)
        if value is not None:
            # Convert non-bool values to bool for consistency in snapshot
            if isinstance(value, bool):
                snapshot[flag_name] = value
            elif isinstance(value, int):
                # For int flags like max_subagents, include as-is but type as Any
                # For API simplicity, we'll just skip non-bool flags in the snapshot
                pass
            else:
                snapshot[flag_name] = bool(value)
    return snapshot


@agents_router.get("/config")
async def get_agent_config() -> AgentConfigResponse:
    """
    Get current agent configuration.

    Returns the current model settings, verification settings,
    list of available tools from the MCP server, and extended
    configuration (thinking budget, feature flags).

    Returns:
        AgentConfigResponse with current agent configuration.
    """
    # Get registered tools
    tools_data = get_registered_tools()
    tools = [ToolInfo(name=t["name"], description=t["description"]) for t in tools_data]

    # Get extended configuration
    thinking_budget_defaults = get_thinking_budget_defaults()
    feature_flags_snapshot = get_agent_feature_flags_snapshot()

    # Get registered orchestrators
    orchestrators = get_all_orchestrators()

    # Get supported providers
    providers = get_all_providers()

    return AgentConfigResponse(
        model=settings.model_name,
        provider=settings.llm_provider,
        temperature=settings.model_temperature,
        verification_enabled=settings.enable_verification,
        tools=tools,
        thinking_budget_defaults=thinking_budget_defaults,
        feature_flags_snapshot=feature_flags_snapshot,
        orchestrators=orchestrators,
        providers=providers,
    )


async def update_thinking_budget(
    request: ThinkingBudgetUpdateRequest,
) -> ThinkingBudgetUpdateResponse:
    """
    Update thinking budget configuration.

    Updates the thinking budget settings based on the provided request.
    Only fields that are explicitly set in the request will be updated.

    Args:
        request: ThinkingBudgetUpdateRequest with fields to update

    Returns:
        ThinkingBudgetUpdateResponse with update status and current config
    """
    updated_fields: list[str] = []

    # Update enabled flag if provided
    if request.enabled is not None:
        # Note: In a real implementation, this would persist to config/database
        # For now, we update the feature_flags singleton (in-memory only)
        feature_flags.enable_thinking_budget = request.enabled
        updated_fields.append("enabled")
        logger.info(f"Updated thinking budget enabled to: {request.enabled}")

    # Update default level if provided
    if request.default_level is not None:
        # Note: In a real implementation, this would persist to config/database
        feature_flags.default_thinking_level = request.default_level
        updated_fields.append("default_level")
        logger.info(f"Updated default thinking level to: {request.default_level}")

    # Get current config after updates
    current_config = get_thinking_budget_defaults()

    return ThinkingBudgetUpdateResponse(
        success=True,
        updated_fields=updated_fields,
        current_config=current_config,
        message=f"Updated {len(updated_fields)} field(s)" if updated_fields else "No changes made",
    )


@agents_router.patch("/config/thinking-budget")
async def patch_thinking_budget(
    request: ThinkingBudgetUpdateRequest,
) -> ThinkingBudgetUpdateResponse:
    """
    Update thinking budget configuration (PATCH).

    Allows updating thinking budget settings:
    - enabled: Enable/disable thinking budget feature
    - default_level: Set default thinking level (low, medium, high, ultra)

    Only provided fields will be updated.

    Returns:
        ThinkingBudgetUpdateResponse with update status and current config.
    """
    return await update_thinking_budget(request)
