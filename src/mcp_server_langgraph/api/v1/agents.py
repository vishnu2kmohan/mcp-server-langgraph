"""
Agents Config Router

Provides agent configuration under /api/v1/agents/*.

This endpoint returns the current agent configuration including:
- Model name and provider (from core/config.py)
- Temperature settings
- Verification settings (human-in-loop)
- Registered tools from MCP server

Usage:
    GET /api/v1/agents/config - Get current agent configuration
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger

agents_router = APIRouter(prefix="/agents", tags=["agents"])


# Response Models


class ToolInfo(BaseModel):
    """Tool information for display."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")


class AgentConfigResponse(BaseModel):
    """Response model for agent configuration."""

    model: str = Field(..., description="Current model name")
    provider: str = Field(..., description="LLM provider (google, anthropic, openai, etc.)")
    temperature: float = Field(..., ge=0.0, le=2.0, description="Model temperature (0.0-2.0)")
    verification_enabled: bool = Field(..., description="Whether verification/human-in-loop is enabled")
    tools: list[ToolInfo] = Field(default_factory=list, description="List of available tools")


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


@agents_router.get("/config")
async def get_agent_config() -> AgentConfigResponse:
    """
    Get current agent configuration.

    Returns the current model settings, verification settings,
    and list of available tools from the MCP server.

    Returns:
        AgentConfigResponse with current agent configuration.
    """
    # Get registered tools
    tools_data = get_registered_tools()
    tools = [ToolInfo(name=t["name"], description=t["description"]) for t in tools_data]

    return AgentConfigResponse(
        model=settings.model_name,
        provider=settings.llm_provider,
        temperature=settings.model_temperature,
        verification_enabled=settings.enable_verification,
        tools=tools,
    )
