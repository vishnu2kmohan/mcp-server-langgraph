"""
MCP REST Router.

Exposes MCP Protocol 2025-11-25 features via REST endpoints.

Endpoints:
- GET  /tools                  - List available tools (REST fallback for WebSocket)
- POST /tools/call             - Call a tool (REST fallback for WebSocket)
- GET  /resources              - List available resources
- GET  /resources/content      - Read a resource by URI
- GET  /prompts                - List available prompts
- POST /prompts/{name}         - Get a prompt with arguments
- POST /sampling               - Request LLM completion (server-initiated)
- POST /elicitation            - Request user input (form mode)
- POST /elicitation/url        - Request user URL action
- GET  /tasks                  - List active tasks
- GET  /tasks/{id}             - Get task status
- POST /tasks/{id}/cancel      - Cancel a task
- GET  /tasks/{id}/result      - Get task result (blocks until complete)

Example:
    from mcp_server_langgraph.api.v1.mcp import mcp_router
    app.include_router(mcp_router, prefix="/api/v1/mcp")
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.v1.mcp_bridge import (
    ChatError,
    MCPBridge,
    MCPConnectionError,
    MCPElicitationRequiredError,
    MCPPermissionError,
    MCPResource,
    MCPResourceContent,
    MCPResourceNotFoundError,
    MCPTask,
    MCPTaskNotFoundError,
    MCPTool,
    MCPToolResult,
    SamplingResponse,
    get_mcp_bridge,
)


mcp_router = APIRouter(tags=["mcp"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ResourceResponse(BaseModel):
    """Response model for a single resource."""

    uri: str = Field(description="Resource URI")
    name: str = Field(description="Resource name")
    title: str | None = Field(default=None, description="Human-readable title")
    description: str | None = Field(default=None, description="Resource description")
    mime_type: str | None = Field(default=None, description="MIME type")


class ResourceListResponse(BaseModel):
    """Response model for listing resources."""

    resources: list[ResourceResponse] = Field(description="List of resources")


class ResourceContentItem(BaseModel):
    """A single resource content item."""

    uri: str = Field(description="Resource URI")
    mime_type: str | None = Field(default=None, description="MIME type")
    text: str | None = Field(default=None, description="Text content")
    blob: str | None = Field(default=None, description="Base64 encoded binary content")


class ResourceContentResponse(BaseModel):
    """Response model for reading resource content."""

    contents: list[ResourceContentItem] = Field(description="Resource contents")


# =============================================================================
# Tool Request/Response Models
# =============================================================================


class ToolResponse(BaseModel):
    """Response model for a single tool."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    inputSchema: dict[str, Any] | None = Field(default=None, description="JSON Schema for tool input")


class ToolListResponse(BaseModel):
    """Response model for listing tools."""

    tools: list[ToolResponse] = Field(description="List of available tools")


class ToolCallRequest(BaseModel):
    """Request model for calling a tool."""

    name: str = Field(description="Tool name to call")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolCallContentItem(BaseModel):
    """A single content item in a tool result."""

    type: str = Field(description="Content type (text, image, resource)")
    text: str | None = Field(default=None, description="Text content")
    data: str | None = Field(default=None, description="Base64 encoded data")
    mimeType: str | None = Field(default=None, description="MIME type for binary content")


class ToolCallResponse(BaseModel):
    """Response model for tool call result."""

    content: list[ToolCallContentItem] = Field(description="Result content items")
    isError: bool = Field(default=False, description="Whether the call resulted in an error")


class SamplingRequest(BaseModel):
    """Request model for sampling."""

    messages: list[dict[str, Any]] = Field(description="Conversation messages")
    max_tokens: int = Field(default=1000, ge=1, le=100000, description="Max tokens")
    system_prompt: str | None = Field(default=None, description="System prompt")
    model_hints: list[str] | None = Field(default=None, description="Model name hints")
    intelligence_priority: float = Field(default=0.5, ge=0.0, le=1.0, description="Intelligence priority")
    speed_priority: float = Field(default=0.5, ge=0.0, le=1.0, description="Speed priority")
    cost_priority: float = Field(default=0.5, ge=0.0, le=1.0, description="Cost priority")


class SamplingResponseModel(BaseModel):
    """Response model for sampling."""

    role: str = Field(description="Message role")
    content: dict[str, Any] = Field(description="Message content")
    model: str | None = Field(default=None, description="Model used")
    stop_reason: str | None = Field(default=None, description="Stop reason")


class ElicitationFormRequest(BaseModel):
    """Request model for form elicitation."""

    model_config = {"populate_by_name": True}

    message: str = Field(description="Human-readable explanation")
    requested_schema: dict[str, Any] | None = Field(default=None, alias="schema", description="JSON Schema for the form")


class ElicitationUrlRequest(BaseModel):
    """Request model for URL elicitation."""

    message: str = Field(description="Human-readable explanation")
    url: str = Field(description="URL to navigate to")


class ElicitationResponseModel(BaseModel):
    """Response model for elicitation."""

    action: str = Field(description="User action (accept, decline, cancel)")
    content: dict[str, Any] | None = Field(default=None, description="User input")


class TaskResponse(BaseModel):
    """Response model for a task."""

    task_id: str = Field(description="Task ID")
    status: str = Field(description="Task status")
    created_at: datetime = Field(description="Creation timestamp")
    last_updated_at: datetime = Field(description="Last update timestamp")
    ttl: int | None = Field(default=None, description="TTL in milliseconds")
    poll_interval: int | None = Field(default=None, description="Recommended poll interval in ms")
    status_message: str | None = Field(default=None, description="Status message")


class TaskListResponse(BaseModel):
    """Response model for listing tasks."""

    tasks: list[TaskResponse] = Field(description="List of tasks")


class PromptArgumentResponse(BaseModel):
    """Response model for a prompt argument."""

    name: str = Field(description="Argument name")
    description: str = Field(description="Argument description")
    required: bool = Field(default=False, description="Whether argument is required")


class PromptResponse(BaseModel):
    """Response model for a prompt."""

    name: str = Field(description="Prompt name")
    description: str = Field(description="Prompt description")
    arguments: list[PromptArgumentResponse] = Field(default_factory=list, description="Prompt arguments")


class PromptListResponse(BaseModel):
    """Response model for listing prompts."""

    prompts: list[PromptResponse] = Field(description="List of prompts")


class PromptGetRequest(BaseModel):
    """Request model for getting a prompt with arguments."""

    arguments: dict[str, Any] = Field(default_factory=dict, description="Prompt arguments")


class PromptMessageResponse(BaseModel):
    """Response model for a prompt message."""

    role: str = Field(description="Message role (user, assistant, system)")
    content: dict[str, Any] = Field(description="Message content")


class PromptGetResponse(BaseModel):
    """Response model for getting a prompt."""

    description: str | None = Field(default=None, description="Prompt description")
    messages: list[PromptMessageResponse] = Field(description="Prompt messages")


class ElicitationRequiredResponse(BaseModel):
    """Response model for elicitation required error."""

    detail: str = Field(description="Error message")
    elicitations: list[dict[str, Any]] = Field(description="Required elicitations")


# =============================================================================
# Service Layer
# =============================================================================


class MCPService:
    """
    Service layer for MCP operations.

    Wraps MCPBridge and provides high-level operations for the router.
    """

    def __init__(self, bridge: MCPBridge | None = None) -> None:
        """Initialize with optional bridge."""
        self._bridge = bridge

    @property
    def bridge(self) -> MCPBridge | None:
        """Get the MCP bridge, lazily initializing if needed."""
        if self._bridge is None:
            self._bridge = get_mcp_bridge()
        return self._bridge

    @property
    def is_configured(self) -> bool:
        """Check if the service is configured."""
        return self.bridge is not None and self.bridge.is_configured

    async def list_tools(self) -> list[MCPTool]:
        """
        List available tools.

        Returns tools from the MCP bridge if configured, otherwise falls back
        to built-in tools from the local MCP server.
        """
        bridge = self.bridge
        if bridge is not None and bridge.is_configured:
            return await bridge.refresh_tools()

        # Fall back to built-in MCP server tools
        try:
            from mcp_server_langgraph.mcp.server_streamable import get_mcp_server
            import logging

            logger = logging.getLogger(__name__)
            logger.info("Listing available tools from built-in MCP server")

            mcp_server = get_mcp_server()
            builtin_tools = await mcp_server.list_tools_public()
            logger.info(f"Found {len(builtin_tools)} built-in tools")

            return [
                MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                )
                for tool in builtin_tools
            ]
        except Exception as e:
            # If MCP server not initialized, return empty list
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to get built-in tools: {e}")
            return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPToolResult:
        """
        Call a tool with the given arguments.

        Uses MCP bridge if configured, otherwise falls back to built-in MCP server.
        """
        bridge = self.bridge
        if bridge is not None and bridge.is_configured:
            return await bridge.call_tool(tool_name=tool_name, arguments=arguments or {})

        # Fall back to built-in MCP server
        try:
            from mcp_server_langgraph.mcp.server_streamable import get_mcp_server

            mcp_server = get_mcp_server()
            result = await mcp_server.call_tool_public(tool_name, arguments or {})
            # Convert TextContent objects to dicts
            content = [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else {"type": "text", "text": str(item)}
                for item in result
            ]
            return MCPToolResult(content=content, is_error=False)
        except Exception as e:
            return MCPToolResult(
                content=[{"type": "text", "text": f"Error calling tool: {e}"}],
                is_error=True,
            )

    async def list_resources(self) -> list[MCPResource]:
        """List available resources."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            return []
        return await bridge.refresh_resources()

    async def read_resource(self, uri: str) -> list[MCPResourceContent]:
        """Read a resource by URI."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            raise ChatError("MCP not configured")
        return await bridge.read_resource(uri)

    async def request_sampling(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1000,
        system_prompt: str | None = None,
        model_hints: list[str] | None = None,
        intelligence_priority: float = 0.5,
        speed_priority: float = 0.5,
        cost_priority: float = 0.5,
    ) -> SamplingResponse:
        """Request LLM completion via sampling."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            raise ChatError("MCP not configured")
        return await bridge.request_sampling(
            messages=messages,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            model_hints=model_hints,
            intelligence_priority=intelligence_priority,
            speed_priority=speed_priority,
            cost_priority=cost_priority,
        )

    async def request_user_input(
        self,
        message: str,
        schema: dict[str, Any] | None = None,
    ) -> Any:
        """Request user input via form elicitation."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            raise ChatError("MCP not configured")
        return await bridge.request_user_input(message=message, schema=schema)

    async def request_user_url_action(
        self,
        message: str,
        url: str,
    ) -> Any:
        """Request user to navigate to a URL."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            raise ChatError("MCP not configured")
        return await bridge.request_user_url_action(message=message, url=url)

    async def list_tasks(self) -> list[MCPTask]:
        """List active tasks."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            return []
        return await bridge.list_tasks()

    async def get_task(self, task_id: str) -> MCPTask:
        """Get task status."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            raise ChatError("MCP not configured")
        return await bridge.get_task(task_id)

    async def cancel_task(self, task_id: str) -> MCPTask:
        """Cancel a task."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            raise ChatError("MCP not configured")
        return await bridge.cancel_task(task_id)

    async def get_task_result(self, task_id: str) -> MCPToolResult:
        """Get task result (blocks until task completes)."""
        bridge = self.bridge
        if bridge is None or not bridge.is_configured:
            raise ChatError("MCP not configured")
        return await bridge.get_task_result(task_id)

    async def list_prompts(self) -> list[dict[str, Any]]:
        """List available prompts."""
        # Import here to avoid circular imports
        from mcp_server_langgraph.mcp.server_streamable import get_mcp_server

        mcp_server = get_mcp_server()
        return mcp_server.list_prompts_public()

    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get a prompt with arguments filled in.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Dict with 'description' and 'messages' keys
        """
        arguments = arguments or {}

        # Generate prompt messages based on name
        if name == "code_review":
            code = arguments.get("code", "")
            language = arguments.get("language", "unknown")
            return {
                "description": "Review code for issues and improvements",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Please review the following {language} code:\n\n```{language}\n{code}\n```",
                        },
                    }
                ],
            }
        elif name == "summarize_conversation":
            return {
                "description": "Summarize the current conversation",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Please summarize the key points from our conversation so far.",
                        },
                    }
                ],
            }
        elif name == "debug_error":
            error = arguments.get("error", "")
            context = arguments.get("context", "")
            context_text = f"\n\nContext:\n{context}" if context else ""
            return {
                "description": "Debug an error message",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Please help me debug this error:\n\n```\n{error}\n```{context_text}",
                        },
                    }
                ],
            }
        else:
            # Unknown prompt
            raise ValueError(f"Unknown prompt: {name}")


# Service singleton
_mcp_service: MCPService | None = None


def get_mcp_service() -> MCPService:
    """Get the MCP service instance."""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = MCPService()
    return _mcp_service


def reset_mcp_service() -> None:
    """Reset the MCP service singleton (for testing)."""
    global _mcp_service
    _mcp_service = None


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_resource(resource: MCPResource) -> ResourceResponse:
    """Convert MCPResource to response model."""
    return ResourceResponse(
        uri=resource.uri,
        name=resource.name,
        title=resource.title,
        description=resource.description,
        mime_type=resource.mime_type,
    )


def _convert_content(content: MCPResourceContent) -> ResourceContentItem:
    """Convert MCPResourceContent to response model."""
    return ResourceContentItem(
        uri=content.uri,
        mime_type=content.mime_type,
        text=content.text,
        blob=content.blob,
    )


def _convert_task(task: MCPTask) -> TaskResponse:
    """Convert MCPTask to response model."""
    return TaskResponse(
        task_id=task.task_id,
        status=task.status.value,
        created_at=task.created_at,
        last_updated_at=task.last_updated_at,
        ttl=task.ttl,
        poll_interval=task.poll_interval,
        status_message=task.status_message,
    )


def _convert_tool(tool: MCPTool) -> ToolResponse:
    """Convert MCPTool to response model."""
    return ToolResponse(
        name=tool.name,
        description=tool.description,
        inputSchema=tool.input_schema,
    )


def _convert_tool_result(result: MCPToolResult) -> ToolCallResponse:
    """Convert MCPToolResult to response model."""
    content_items = []
    for item in result.content:
        content_items.append(
            ToolCallContentItem(
                type=item.get("type", "text"),
                text=item.get("text"),
                data=item.get("data"),
                mimeType=item.get("mimeType"),
            )
        )
    return ToolCallResponse(
        content=content_items,
        isError=result.is_error,
    )


# =============================================================================
# Endpoints
# =============================================================================


@mcp_router.get("/tools")
async def list_tools() -> ToolListResponse:
    """
    List available MCP tools.

    Returns all tools exposed by the MCP server.
    Used as REST fallback when WebSocket is unavailable.
    """
    service = get_mcp_service()

    try:
        tools = await service.list_tools()
        return ToolListResponse(tools=[_convert_tool(t) for t in tools])
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )


@mcp_router.post("/tools/call")
async def call_tool(request: ToolCallRequest) -> ToolCallResponse:
    """
    Call an MCP tool.

    Executes the specified tool with the given arguments.
    Used as REST fallback when WebSocket is unavailable.
    """
    service = get_mcp_service()

    try:
        result = await service.call_tool(tool_name=request.name, arguments=request.arguments)
        return _convert_tool_result(result)
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP not configured: {e}",
        )


@mcp_router.get("/resources")
async def list_resources() -> ResourceListResponse:
    """
    List available MCP resources.

    Returns all resources exposed by the MCP server.
    """
    service = get_mcp_service()

    try:
        resources = await service.list_resources()
        return ResourceListResponse(resources=[_convert_resource(r) for r in resources])
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )


@mcp_router.get("/resources/content")
async def read_resource(
    uri: str = Query(..., description="Resource URI to read"),
) -> ResourceContentResponse:
    """
    Read a resource by URI.

    Returns the content of the specified resource.
    """
    service = get_mcp_service()

    try:
        contents = await service.read_resource(uri)
        return ResourceContentResponse(contents=[_convert_content(c) for c in contents])
    except MCPResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource not found: {e}",
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP not configured: {e}",
        )


@mcp_router.get("/prompts")
async def list_prompts() -> PromptListResponse:
    """
    List available MCP prompts.

    Returns all prompts (workflow templates) exposed by the MCP server.
    """
    service = get_mcp_service()

    try:
        prompts = await service.list_prompts()
        return PromptListResponse(
            prompts=[
                PromptResponse(
                    name=p["name"],
                    description=p["description"],
                    arguments=[
                        PromptArgumentResponse(
                            name=arg["name"],
                            description=arg["description"],
                            required=arg.get("required", False),
                        )
                        for arg in p.get("arguments", [])
                    ],
                )
                for p in prompts
            ]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to list prompts: {e}",
        )


@mcp_router.post("/prompts/{prompt_name}")
async def get_prompt(
    prompt_name: str,
    request: PromptGetRequest | None = None,
) -> PromptGetResponse:
    """
    Get a prompt with arguments filled in.

    Returns the prompt messages with the provided arguments substituted.
    """
    service = get_mcp_service()

    try:
        arguments = request.arguments if request else {}
        result = await service.get_prompt(prompt_name, arguments)
        return PromptGetResponse(
            description=result.get("description"),
            messages=[
                PromptMessageResponse(
                    role=msg["role"],
                    content=msg["content"],
                )
                for msg in result.get("messages", [])
            ],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to get prompt: {e}",
        )


@mcp_router.post("/sampling")
async def create_sampling(request: SamplingRequest) -> SamplingResponseModel:
    """
    Request LLM completion via MCP sampling.

    This is a server-initiated request for the client to sample from an LLM.
    Useful for agent patterns where the server needs LLM assistance.
    """
    service = get_mcp_service()

    try:
        response = await service.request_sampling(
            messages=request.messages,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
            model_hints=request.model_hints,
            intelligence_priority=request.intelligence_priority,
            speed_priority=request.speed_priority,
            cost_priority=request.cost_priority,
        )
        return SamplingResponseModel(
            role=response.role,
            content=response.content,
            model=response.model,
            stop_reason=response.stop_reason,
        )
    except MCPElicitationRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={"detail": str(e), "elicitations": e.elicitations},
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP not configured: {e}",
        )


@mcp_router.post("/elicitation")
async def create_elicitation(request: ElicitationFormRequest) -> ElicitationResponseModel:
    """
    Request user input via form elicitation.

    Allows the server to request structured input from the user.
    """
    service = get_mcp_service()

    try:
        response = await service.request_user_input(
            message=request.message,
            schema=request.requested_schema,
        )
        return ElicitationResponseModel(
            action=response.action.value,
            content=response.content,
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP not configured: {e}",
        )


@mcp_router.post("/elicitation/url")
async def create_url_elicitation(
    request: ElicitationUrlRequest,
) -> ElicitationResponseModel:
    """
    Request user to navigate to a URL.

    Useful for OAuth flows or handling sensitive data.
    """
    service = get_mcp_service()

    try:
        response = await service.request_user_url_action(
            message=request.message,
            url=request.url,
        )
        return ElicitationResponseModel(
            action=response.action.value,
            content=response.content,
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP not configured: {e}",
        )


@mcp_router.get("/tasks")
async def list_tasks() -> TaskListResponse:
    """
    List active MCP tasks.

    Returns all currently active tasks (experimental feature).
    """
    service = get_mcp_service()

    try:
        tasks = await service.list_tasks()
        return TaskListResponse(tasks=[_convert_task(t) for t in tasks])
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )


@mcp_router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> TaskResponse:
    """
    Get task status.

    Returns the current status of a task.
    """
    service = get_mcp_service()

    try:
        task = await service.get_task(task_id)
        return _convert_task(task)
    except MCPTaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP not configured: {e}",
        )


@mcp_router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str) -> TaskResponse:
    """
    Cancel a running task.

    Attempts to cancel the specified task.
    """
    service = get_mcp_service()

    try:
        task = await service.cancel_task(task_id)
        return _convert_task(task)
    except MCPTaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP not configured: {e}",
        )


@mcp_router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str) -> ToolCallResponse:
    """
    Get task result (blocks until complete).

    Waits for the task to reach a terminal status, then returns the result.
    Per MCP 2025-11-25 spec: tasks/result.
    """
    service = get_mcp_service()

    try:
        result = await service.get_task_result(task_id)
        return _convert_tool_result(result)
    except MCPTaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )
    except ChatError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP not configured: {e}",
        )
