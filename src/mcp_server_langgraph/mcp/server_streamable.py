"""
MCP Server with StreamableHTTP transport
Implements the MCP StreamableHTTP specification (replaces deprecated SSE)

Implements Anthropic's best practices for writing tools for agents:
- Token-efficient responses with truncation
- Search-focused tools instead of list-all
- Response format control (concise vs detailed)
- Namespaced tools for clarity
- High-signal information in responses
"""

import asyncio
import json
from typing import Any, AsyncIterator, Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from mcp.server import Server
from mcp.types import Resource, TextContent, Tool
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.core.agent import AgentState, agent_graph
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.utils.response_optimizer import format_response

app = FastAPI(
    title="MCP Server with LangGraph",
    description="AI Agent with fine-grained authorization and observability - StreamableHTTP transport",
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "mcp",
            "description": "Model Context Protocol (MCP) endpoints for agent interaction",
        },
        {
            "name": "health",
            "description": "Health check and system status endpoints",
        },
        {
            "name": "auth",
            "description": "Authentication and authorization endpoints",
        },
    ],
    responses={
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        429: {"description": "Too Many Requests - Rate limit exceeded"},
        500: {"description": "Internal Server Error"},
    },
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)


class ChatInput(BaseModel):
    """
    Input schema for agent_chat tool.

    Follows Anthropic best practices:
    - Unambiguous parameter names (user_id not username, message not query)
    - Response format control for token efficiency
    - Clear field descriptions
    """

    message: str = Field(description="The user message to send to the agent", min_length=1, max_length=10000)
    user_id: str = Field(description="User identifier for authentication and authorization")
    thread_id: str | None = Field(
        default=None, description="Optional thread ID for conversation continuity (e.g., 'conv_123')"
    )
    response_format: Literal["concise", "detailed"] = Field(
        default="concise",
        description=(
            "Response verbosity level. "
            "'concise' returns ~500 tokens (faster, less context). "
            "'detailed' returns ~2000 tokens (comprehensive, more context)."
        ),
    )

    # Backward compatibility - DEPRECATED
    username: str | None = Field(
        default=None, deprecated=True, description="DEPRECATED: Use 'user_id' instead. Maintained for backward compatibility."
    )

    @property
    def effective_user_id(self) -> str:
        """Get effective user ID, prioritizing user_id over deprecated username."""
        return self.user_id if hasattr(self, "user_id") and self.user_id else (self.username or "")


class SearchConversationsInput(BaseModel):
    """Input schema for conversation_search tool."""

    query: str = Field(description="Search query to filter conversations", min_length=1, max_length=500)
    user_id: str = Field(description="User identifier for authentication and authorization")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of conversations to return (1-50)")

    # Backward compatibility - DEPRECATED
    username: str | None = Field(
        default=None, deprecated=True, description="DEPRECATED: Use 'user_id' instead. Maintained for backward compatibility."
    )

    @property
    def effective_user_id(self) -> str:
        """Get effective user ID, prioritizing user_id over deprecated username."""
        return self.user_id if hasattr(self, "user_id") and self.user_id else (self.username or "")


class MCPAgentStreamableServer:
    """MCP Server with StreamableHTTP transport"""

    def __init__(self, openfga_client: OpenFGAClient | None = None):
        self.server = Server("langgraph-agent")

        # Initialize OpenFGA client
        self.openfga = openfga_client or self._create_openfga_client()

        # Validate JWT secret is configured (fail-closed security pattern)
        if not settings.jwt_secret_key:
            raise ValueError(
                "CRITICAL: JWT secret key not configured. "
                "Set JWT_SECRET_KEY environment variable or configure via Infisical. "
                "The service cannot start without a secure secret key."
            )

        # Initialize auth with OpenFGA
        self.auth = AuthMiddleware(secret_key=settings.jwt_secret_key, openfga_client=self.openfga)

        self._setup_handlers()

    def _create_openfga_client(self) -> OpenFGAClient | None:
        """Create OpenFGA client from settings"""
        if settings.openfga_store_id and settings.openfga_model_id:
            logger.info(
                "Initializing OpenFGA client",
                extra={"store_id": settings.openfga_store_id, "model_id": settings.openfga_model_id},
            )
            return OpenFGAClient(
                api_url=settings.openfga_api_url, store_id=settings.openfga_store_id, model_id=settings.openfga_model_id
            )
        else:
            logger.warning("OpenFGA not configured, authorization will use fallback mode")
            return None

    def _setup_handlers(self):
        """Setup MCP protocol handlers"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """
            List available tools.

            Tools follow Anthropic best practices:
            - Namespaced for clarity (agent_*, conversation_*)
            - Search-focused instead of list-all
            - Clear usage guidance in descriptions
            - Token limits and expected response times documented
            """
            with tracer.start_as_current_span("mcp.list_tools"):
                logger.info("Listing available tools")
                return [
                    Tool(
                        name="agent_chat",
                        description=(
                            "Chat with the AI agent for questions, research, and problem-solving. "
                            "Returns responses optimized for agent consumption. "
                            "Response format: 'concise' (~500 tokens, 2-5 sec) or 'detailed' (~2000 tokens, 5-10 sec). "
                            "For specialized tasks like code execution or web search, use dedicated tools instead. "
                            "Rate limit: 60 requests/minute per user."
                        ),
                        inputSchema=ChatInput.model_json_schema(),
                    ),
                    Tool(
                        name="conversation_get",
                        description=(
                            "Retrieve a specific conversation thread by ID. "
                            "Returns conversation history with messages, participants, and metadata. "
                            "Response time: <1 second. "
                            "Use conversation_search to find conversation IDs first."
                        ),
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "thread_id": {
                                    "type": "string",
                                    "description": "Conversation thread identifier (e.g., 'conv_abc123')",
                                },
                                "user_id": {
                                    "type": "string",
                                    "description": "User identifier for authentication and authorization",
                                },
                                "username": {"type": "string", "description": "DEPRECATED: Use 'user_id' instead"},
                            },
                            "required": ["thread_id", "user_id"],
                        },
                    ),
                    Tool(
                        name="conversation_search",
                        description=(
                            "Search conversations using keywords or filters. "
                            "Returns matching conversations sorted by relevance. "
                            "Much more efficient than listing all conversations. "
                            "Response time: <2 seconds. "
                            "Examples: 'project updates', 'conversations with alice', 'last week'. "
                            "Results limited to 50 conversations max to prevent context overflow."
                        ),
                        inputSchema=SearchConversationsInput.model_json_schema(),
                    ),
                ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls with OpenFGA authorization and tracing"""

            with tracer.start_as_current_span("mcp.call_tool", attributes={"tool.name": name}) as span:
                logger.info(f"Tool called: {name}", extra={"tool": name, "args": arguments})
                metrics.tool_calls.add(1, {"tool": name})

                # Extract user_id (with backward compatibility for username)
                user_id = arguments.get("user_id") or arguments.get("username")

                # Require authentication
                if not user_id:
                    logger.warning("No user identification provided")
                    metrics.auth_failures.add(1)
                    raise PermissionError(
                        "User identification required. Provide 'user_id' parameter. "
                        "(Legacy 'username' also supported but deprecated)"
                    )

                # Log deprecation warning if username was used
                if "username" in arguments and "user_id" not in arguments:
                    logger.warning(
                        "DEPRECATED: 'username' parameter used. Please update to 'user_id'.",
                        extra={"user": user_id, "tool": name},
                    )

                # Authenticate user
                span.set_attribute("user.id", user_id)
                auth_result = await self.auth.authenticate(user_id)

                if not auth_result["authorized"]:
                    logger.warning("Authentication failed", extra={"user_id": user_id, "reason": auth_result.get("reason")})
                    metrics.auth_failures.add(1)
                    raise PermissionError(f"Authentication failed: {auth_result.get('reason', 'unknown')}")

                user_id = auth_result["user_id"]

                # Check OpenFGA authorization
                resource = f"tool:{name}"

                authorized = await self.auth.authorize(user_id=user_id, relation="executor", resource=resource)

                if not authorized:
                    logger.warning(
                        "Authorization failed (OpenFGA)",
                        extra={"user_id": user_id, "resource": resource, "relation": "executor"},
                    )
                    metrics.authz_failures.add(1, {"resource": resource})
                    raise PermissionError(f"Not authorized to execute {resource}")

                logger.info("Authorization granted", extra={"user_id": user_id, "resource": resource})

                # Route to appropriate handler (with backward compatibility)
                if name == "agent_chat" or name == "chat":  # Support old name for compatibility
                    return await self._handle_chat(arguments, span, user_id)
                elif name == "conversation_get" or name == "get_conversation":
                    return await self._handle_get_conversation(arguments, span, user_id)
                elif name == "conversation_search" or name == "list_conversations":
                    return await self._handle_search_conversations(arguments, span, user_id)
                else:
                    raise ValueError(f"Unknown tool: {name}")

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources"""
            with tracer.start_as_current_span("mcp.list_resources"):
                return [Resource(uri="agent://config", name="Agent Configuration", mimeType="application/json")]

    async def _handle_chat(self, arguments: dict[str, Any], span, user_id: str) -> list[TextContent]:
        """
        Handle agent_chat tool invocation.

        Implements Anthropic best practices:
        - Response format control (concise vs detailed)
        - Token-efficient responses with truncation
        - Clear error messages
        - Performance tracking
        """
        with tracer.start_as_current_span("agent.chat"):
            message = arguments["message"]
            thread_id = arguments.get("thread_id", "default")
            response_format_type = arguments.get("response_format", "concise")

            span.set_attribute("message.length", len(message))
            span.set_attribute("thread.id", thread_id)
            span.set_attribute("user.id", user_id)
            span.set_attribute("response.format", response_format_type)

            # Check if user can access this conversation
            conversation_resource = f"conversation:{thread_id}"

            can_edit = await self.auth.authorize(user_id=user_id, relation="editor", resource=conversation_resource)

            if not can_edit:
                logger.warning("User cannot edit conversation", extra={"user_id": user_id, "thread_id": thread_id})
                raise PermissionError(
                    f"Not authorized to edit conversation '{thread_id}'. "
                    f"Request access from conversation owner or use a different thread_id."
                )

            logger.info(
                "Processing chat message",
                extra={
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "message_preview": message[:100],
                    "response_format": response_format_type,
                },
            )

            # Create initial state
            initial_state: AgentState = {
                "messages": [{"role": "user", "content": message}],
                "next_action": "",
                "user_id": user_id,
                "request_id": str(span.get_span_context().trace_id) if span.get_span_context() else None,
            }

            # Run the agent graph
            config = {"configurable": {"thread_id": thread_id}}

            try:
                result = await agent_graph.ainvoke(initial_state, config)

                # Extract response
                response_message = result["messages"][-1]
                response_text = response_message.content

                # Apply response formatting based on format type
                # Follows Anthropic guidance: offer response_format enum parameter
                formatted_response = format_response(response_text, format_type=response_format_type)

                span.set_attribute("response.length.original", len(response_text))
                span.set_attribute("response.length.formatted", len(formatted_response))
                metrics.successful_calls.add(1, {"tool": "agent_chat", "format": response_format_type})

                logger.info(
                    "Chat response generated",
                    extra={
                        "thread_id": thread_id,
                        "original_length": len(response_text),
                        "formatted_length": len(formatted_response),
                        "format": response_format_type,
                    },
                )

                return [TextContent(type="text", text=formatted_response)]

            except Exception as e:
                logger.error(f"Error processing chat: {e}", extra={"error": str(e), "thread_id": thread_id}, exc_info=True)
                metrics.failed_calls.add(1, {"tool": "agent_chat", "error": type(e).__name__})
                span.record_exception(e)
                raise

    async def _handle_get_conversation(self, arguments: dict[str, Any], span, user_id: str) -> list[TextContent]:
        """Retrieve conversation history"""
        with tracer.start_as_current_span("agent.get_conversation"):
            thread_id = arguments["thread_id"]

            # Check if user can view this conversation
            conversation_resource = f"conversation:{thread_id}"

            can_view = await self.auth.authorize(user_id=user_id, relation="viewer", resource=conversation_resource)

            if not can_view:
                logger.warning("User cannot view conversation", extra={"user_id": user_id, "thread_id": thread_id})
                raise PermissionError(f"Not authorized to view conversation {thread_id}")

            # In production, retrieve from checkpoint storage
            # For now, return placeholder
            return [TextContent(type="text", text=f"Conversation history for thread {thread_id}")]

    async def _handle_search_conversations(self, arguments: dict[str, Any], span, user_id: str) -> list[TextContent]:
        """
        Search conversations (replacing list-all approach).

        Implements Anthropic best practice:
        "Implement search-focused tools (like search_contacts) rather than
        list-all tools (list_contacts)"

        Benefits:
        - Prevents context overflow with large conversation lists
        - Forces agents to be specific in their requests
        - More token-efficient
        - Better for users with many conversations
        """
        with tracer.start_as_current_span("agent.search_conversations"):
            query = arguments.get("query", "")
            limit = arguments.get("limit", 10)

            span.set_attribute("search.query", query)
            span.set_attribute("search.limit", limit)

            # Get all conversations user can view
            all_conversations = await self.auth.list_accessible_resources(
                user_id=user_id, relation="viewer", resource_type="conversation"
            )

            # Filter conversations based on query (simple implementation)
            # In production, this would use a proper search index
            if query:
                filtered_conversations = [conv for conv in all_conversations if query.lower() in conv.lower()]
            else:
                # No query: return most recent (up to limit)
                filtered_conversations = all_conversations

            # Apply limit to prevent context overflow
            # Follows Anthropic guidance: "Restrict responses to ~25,000 tokens"
            limited_conversations = filtered_conversations[:limit]

            # Build response with high-signal information
            # Avoid technical IDs where possible
            if not limited_conversations:
                response_text = (
                    f"No conversations found matching '{query}'. "
                    f"Try a different search query or request access to more conversations."
                )
            else:
                response_lines = [
                    (
                        f"Found {len(limited_conversations)} conversation(s) matching '{query}':"
                        if query
                        else f"Showing {len(limited_conversations)} recent conversation(s):"
                    )
                ]

                for i, conv_id in enumerate(limited_conversations, 1):
                    # Extract human-readable info from conversation ID
                    # In production, fetch metadata like title, date, participants
                    response_lines.append(f"{i}. {conv_id}")

                # Add guidance if results were truncated
                if len(filtered_conversations) > limit:
                    response_lines.append(
                        f"\n[Showing {limit} of {len(filtered_conversations)} results. "
                        f"Use a more specific query to narrow results.]"
                    )

                response_text = "\n".join(response_lines)

            logger.info(
                "Searched conversations",
                extra={
                    "user_id": user_id,
                    "query": query,
                    "total_accessible": len(all_conversations),
                    "filtered_count": len(filtered_conversations),
                    "returned_count": len(limited_conversations),
                },
            )

            return [TextContent(type="text", text=response_text)]


# Initialize the MCP server
mcp_server = MCPAgentStreamableServer()


# FastAPI endpoints for MCP StreamableHTTP transport
@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "MCP Server with LangGraph",
        "version": settings.service_version,
        "transport": "streamable-http",
        "protocol": "mcp",
        "endpoints": {"message": "/message", "tools": "/tools", "resources": "/resources", "health": "/health"},
        "capabilities": {
            "tools": {"listSupported": True, "callSupported": True},
            "resources": {"listSupported": True, "readSupported": True},
            "streaming": True,
        },
    }


async def stream_jsonrpc_response(data: dict) -> AsyncIterator[str]:
    """
    Stream a JSON-RPC response in chunks

    Yields newline-delimited JSON for streaming responses
    """
    # For now, send the complete response
    # In the future, this could stream token-by-token for LLM responses
    yield json.dumps(data) + "\n"


@app.post("/message")
async def handle_message(request: Request):
    """
    Handle MCP messages via StreamableHTTP POST

    This is the main endpoint for MCP protocol messages.
    Supports both regular and streaming responses.
    """
    try:
        # Parse JSON-RPC request
        message = await request.json()

        with tracer.start_as_current_span("mcp.streamable.message") as span:
            span.set_attribute("mcp.method", message.get("method", "unknown"))
            span.set_attribute("mcp.id", str(message.get("id", "")))

            logger.info("Received MCP message", extra={"method": message.get("method"), "id": message.get("id")})

            method = message.get("method")
            message_id = message.get("id")

            # Handle different MCP methods
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "protocolVersion": "0.1.0",
                        "serverInfo": {"name": "langgraph-agent", "version": settings.service_version},
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "resources": {"listChanged": False},
                            "prompts": {},
                            "logging": {},
                        },
                    },
                }
                return JSONResponse(response)

            elif method == "tools/list":
                tools = await mcp_server.server._tool_manager.list_tools()
                response = {"jsonrpc": "2.0", "id": message_id, "result": {"tools": [tool.model_dump() for tool in tools]}}
                return JSONResponse(response)

            elif method == "tools/call":
                params = message.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                # Check if client supports streaming
                accept_header = request.headers.get("accept", "")
                supports_streaming = "text/event-stream" in accept_header or "application/x-ndjson" in accept_header

                result = await mcp_server.server._tool_manager.call_tool(tool_name, arguments)

                response_data = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"content": [item.model_dump() for item in result]},
                }

                # If streaming is supported, stream the response
                if supports_streaming:
                    return StreamingResponse(
                        stream_jsonrpc_response(response_data),
                        media_type="application/x-ndjson",
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-cache"},
                    )
                else:
                    return JSONResponse(response_data)

            elif method == "resources/list":
                resources = await mcp_server.server._resource_manager.list_resources()
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"resources": [res.model_dump() for res in resources]},
                }
                return JSONResponse(response)

            elif method == "resources/read":
                params = message.get("params", {})
                resource_uri = params.get("uri")

                # Handle resource read (implement based on your needs)
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "contents": [
                            {
                                "uri": resource_uri,
                                "mimeType": "application/json",
                                "text": json.dumps({"config": "placeholder"}),
                            }
                        ]
                    },
                }
                return JSONResponse(response)

            else:
                raise HTTPException(status_code=400, detail=f"Unknown method: {method}")

    except PermissionError as e:
        logger.warning(f"Permission denied: {e}")
        return JSONResponse(
            status_code=403,
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if "message" in locals() else None,
                "error": {"code": -32001, "message": str(e)},
            },
        )
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if "message" in locals() else None,
                "error": {"code": -32603, "message": str(e)},
            },
        )


@app.get("/tools")
async def list_tools():
    """List available tools (convenience endpoint)"""
    tools = await mcp_server.server._tool_manager.list_tools()
    return {"tools": [tool.model_dump() for tool in tools]}


@app.get("/resources")
async def list_resources():
    """List available resources (convenience endpoint)"""
    resources = await mcp_server.server._resource_manager.list_resources()
    return {"resources": [res.model_dump() for res in resources]}


# Include health check routes
from mcp_server_langgraph.health.checks import app as health_app  # noqa: E402

app.mount("/health", health_app)


def main() -> None:
    """Entry point for console script"""
    logger.info(f"Starting MCP StreamableHTTP server on port {settings.get_secret('PORT', fallback='8000')}")

    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 - Required for containerized deployment
        port=int(settings.get_secret("PORT", fallback="8000")),
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
