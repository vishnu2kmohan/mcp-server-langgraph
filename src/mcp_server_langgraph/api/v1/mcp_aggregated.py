"""
REST API endpoints for aggregated MCP capabilities.

Provides unified access to tools, resources, and prompts from all
registered external MCP servers.

Reference: MCP Protocol Specification 2025-11-25
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mcp_server_langgraph.mcp.client.unified_registry import (
    get_unified_registry,
)

# Router for aggregated MCP capabilities
aggregated_router = APIRouter(prefix="/mcp", tags=["MCP Aggregated"])


# =============================================================================
# Response Models
# =============================================================================


class ToolResponse(BaseModel):
    """Response model for a tool definition."""

    qualified_name: str = Field(..., description="Fully qualified name (server:tool)")
    server_name: str = Field(..., description="Name of the MCP server")
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="JSON Schema for parameters")


class ResourceResponse(BaseModel):
    """Response model for a resource definition."""

    qualified_name: str = Field(..., description="Fully qualified name (server:uri)")
    server_name: str = Field(..., description="Name of the MCP server")
    uri: str = Field(..., description="Resource URI")
    name: str = Field(..., description="Resource name")
    description: str | None = Field(None, description="Optional description")
    mime_type: str | None = Field(None, description="MIME type")


class PromptResponse(BaseModel):
    """Response model for a prompt definition."""

    qualified_name: str = Field(..., description="Fully qualified name (server:name)")
    server_name: str = Field(..., description="Name of the MCP server")
    name: str = Field(..., description="Prompt name")
    description: str | None = Field(None, description="Optional description")
    arguments: list[dict[str, Any]] = Field(default_factory=list, description="Prompt arguments")


class ToolsListResponse(BaseModel):
    """Response for listing aggregated tools."""

    tools: list[ToolResponse]
    total_count: int


class ResourcesListResponse(BaseModel):
    """Response for listing aggregated resources."""

    resources: list[ResourceResponse]
    total_count: int


class PromptsListResponse(BaseModel):
    """Response for listing aggregated prompts."""

    prompts: list[PromptResponse]
    total_count: int


class ServerCapabilitiesResponse(BaseModel):
    """Response for server capability summary."""

    server_name: str
    tool_count: int
    resource_count: int
    prompt_count: int


class AllServersResponse(BaseModel):
    """Response for all servers summary."""

    servers: list[ServerCapabilitiesResponse]
    total_servers: int
    total_tools: int
    total_resources: int
    total_prompts: int


# =============================================================================
# Tools Endpoints
# =============================================================================


@aggregated_router.get(
    "/aggregated/tools",
    summary="List aggregated tools",
    description="Get all tools from all registered MCP servers",
)
async def list_aggregated_tools(
    server_name: str | None = None,
) -> ToolsListResponse:
    """List all tools from registered MCP servers.

    Args:
        server_name: Optional filter by server name

    Returns:
        List of tool definitions with total count
    """
    registry = get_unified_registry()
    tools = registry.get_tools(server_name)

    tool_responses = [
        ToolResponse(
            qualified_name=t.qualified_name,
            server_name=t.server_name,
            name=t.name,
            description=t.description,
            input_schema=t.input_schema,
        )
        for t in tools
    ]

    return ToolsListResponse(tools=tool_responses, total_count=len(tool_responses))


@aggregated_router.get(
    "/aggregated/tools/{qualified_name:path}",
    summary="Get tool by qualified name",
    description="Get a specific tool by its qualified name (server:tool)",
)
async def get_aggregated_tool(qualified_name: str) -> ToolResponse:
    """Get a specific tool by qualified name.

    Args:
        qualified_name: Fully qualified name (server:tool)

    Returns:
        Tool definition

    Raises:
        HTTPException: If tool not found
    """
    registry = get_unified_registry()
    tool = registry.get_tool(qualified_name)

    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{qualified_name}' not found")

    return ToolResponse(
        qualified_name=tool.qualified_name,
        server_name=tool.server_name,
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema,
    )


# =============================================================================
# Resources Endpoints
# =============================================================================


@aggregated_router.get(
    "/aggregated/resources",
    summary="List aggregated resources",
    description="Get all resources from all registered MCP servers",
)
async def list_aggregated_resources(
    server_name: str | None = None,
) -> ResourcesListResponse:
    """List all resources from registered MCP servers.

    Args:
        server_name: Optional filter by server name

    Returns:
        List of resource definitions with total count
    """
    registry = get_unified_registry()
    resources = registry.get_resources(server_name)

    resource_responses = [
        ResourceResponse(
            qualified_name=r.qualified_name,
            server_name=r.server_name,
            uri=r.uri,
            name=r.name,
            description=r.description,
            mime_type=r.mime_type,
        )
        for r in resources
    ]

    return ResourcesListResponse(resources=resource_responses, total_count=len(resource_responses))


@aggregated_router.get(
    "/aggregated/resources/{qualified_name:path}",
    summary="Get resource by qualified name",
    description="Get a specific resource by its qualified name (server:uri)",
)
async def get_aggregated_resource(qualified_name: str) -> ResourceResponse:
    """Get a specific resource by qualified name.

    Args:
        qualified_name: Fully qualified name (server:uri)

    Returns:
        Resource definition

    Raises:
        HTTPException: If resource not found
    """
    registry = get_unified_registry()
    resource = registry.get_resource(qualified_name)

    if resource is None:
        raise HTTPException(status_code=404, detail=f"Resource '{qualified_name}' not found")

    return ResourceResponse(
        qualified_name=resource.qualified_name,
        server_name=resource.server_name,
        uri=resource.uri,
        name=resource.name,
        description=resource.description,
        mime_type=resource.mime_type,
    )


# =============================================================================
# Prompts Endpoints
# =============================================================================


@aggregated_router.get(
    "/aggregated/prompts",
    summary="List aggregated prompts",
    description="Get all prompts from all registered MCP servers",
)
async def list_aggregated_prompts(
    server_name: str | None = None,
) -> PromptsListResponse:
    """List all prompts from registered MCP servers.

    Args:
        server_name: Optional filter by server name

    Returns:
        List of prompt definitions with total count
    """
    registry = get_unified_registry()
    prompts = registry.get_prompts(server_name)

    prompt_responses = [
        PromptResponse(
            qualified_name=p.qualified_name,
            server_name=p.server_name,
            name=p.name,
            description=p.description,
            arguments=p.arguments,
        )
        for p in prompts
    ]

    return PromptsListResponse(prompts=prompt_responses, total_count=len(prompt_responses))


@aggregated_router.get(
    "/aggregated/prompts/{qualified_name:path}",
    summary="Get prompt by qualified name",
    description="Get a specific prompt by its qualified name (server:name)",
)
async def get_aggregated_prompt(qualified_name: str) -> PromptResponse:
    """Get a specific prompt by qualified name.

    Args:
        qualified_name: Fully qualified name (server:name)

    Returns:
        Prompt definition

    Raises:
        HTTPException: If prompt not found
    """
    registry = get_unified_registry()
    prompt = registry.get_prompt(qualified_name)

    if prompt is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{qualified_name}' not found")

    return PromptResponse(
        qualified_name=prompt.qualified_name,
        server_name=prompt.server_name,
        name=prompt.name,
        description=prompt.description,
        arguments=prompt.arguments,
    )


# =============================================================================
# Server Summary Endpoints
# =============================================================================


@aggregated_router.get(
    "/aggregated/servers",
    summary="List all registered servers",
    description="Get summary of all registered MCP servers and their capabilities",
)
async def list_aggregated_servers() -> AllServersResponse:
    """List all registered servers with capability counts.

    Returns:
        Summary of all servers with total counts
    """
    registry = get_unified_registry()
    server_names = registry.get_server_names()

    servers: list[ServerCapabilitiesResponse] = []
    total_tools = 0
    total_resources = 0
    total_prompts = 0

    for name in server_names:
        caps = registry.get_server_capabilities(name)
        servers.append(
            ServerCapabilitiesResponse(
                server_name=name,
                tool_count=caps["tool_count"],
                resource_count=caps["resource_count"],
                prompt_count=caps["prompt_count"],
            )
        )
        total_tools += caps["tool_count"]
        total_resources += caps["resource_count"]
        total_prompts += caps["prompt_count"]

    return AllServersResponse(
        servers=servers,
        total_servers=len(servers),
        total_tools=total_tools,
        total_resources=total_resources,
        total_prompts=total_prompts,
    )


@aggregated_router.get(
    "/aggregated/servers/{server_name}",
    summary="Get server capabilities",
    description="Get capability summary for a specific server",
)
async def get_server_capabilities(server_name: str) -> ServerCapabilitiesResponse:
    """Get capability summary for a specific server.

    Args:
        server_name: Name of the server

    Returns:
        Server capability summary

    Raises:
        HTTPException: If server not found
    """
    registry = get_unified_registry()

    if server_name not in registry.get_server_names():
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")

    caps = registry.get_server_capabilities(server_name)

    return ServerCapabilitiesResponse(
        server_name=server_name,
        tool_count=caps["tool_count"],
        resource_count=caps["resource_count"],
        prompt_count=caps["prompt_count"],
    )
