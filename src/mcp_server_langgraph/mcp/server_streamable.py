"""
MCP Server with StreamableHTTP transport
Implements the MCP StreamableHTTP specification (replaces deprecated SSE)
"""

import asyncio
import json
from typing import Any, AsyncIterator

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
    """Input schema for chat tool"""

    message: str = Field(description="The user message to send to the agent")
    username: str = Field(description="Username for authentication")
    thread_id: str | None = Field(default=None, description="Optional thread ID for conversation continuity")


class MCPAgentStreamableServer:
    """MCP Server with StreamableHTTP transport"""

    def __init__(self, openfga_client: OpenFGAClient | None = None):
        self.server = Server("langgraph-agent")

        # Initialize OpenFGA client
        self.openfga = openfga_client or self._create_openfga_client()

        # Initialize auth with OpenFGA
        self.auth = AuthMiddleware(
            secret_key=settings.jwt_secret_key or "change-this-in-production", openfga_client=self.openfga
        )

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
            """List available tools"""
            with tracer.start_as_current_span("mcp.list_tools"):
                logger.info("Listing available tools")
                return [
                    Tool(
                        name="chat",
                        description=(
                            "Chat with the AI agent. The agent can help with questions, research, and problem-solving."
                        ),
                        inputSchema=ChatInput.model_json_schema(),
                    ),
                    Tool(
                        name="get_conversation",
                        description="Retrieve a conversation thread by ID",
                        inputSchema={
                            "type": "object",
                            "properties": {"thread_id": {"type": "string"}, "username": {"type": "string"}},
                            "required": ["thread_id", "username"],
                        },
                    ),
                    Tool(
                        name="list_conversations",
                        description="List all conversations the user has access to",
                        inputSchema={
                            "type": "object",
                            "properties": {"username": {"type": "string"}},
                            "required": ["username"],
                        },
                    ),
                ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls with OpenFGA authorization and tracing"""

            with tracer.start_as_current_span("mcp.call_tool", attributes={"tool.name": name}) as span:
                logger.info(f"Tool called: {name}", extra={"tool": name, "args": arguments})
                metrics.tool_calls.add(1, {"tool": name})

                # Extract username or user_id
                username = arguments.get("username")
                user_id = arguments.get("user_id")

                # Require authentication
                if not username and not user_id:
                    logger.warning("No authentication provided")
                    metrics.auth_failures.add(1)
                    raise PermissionError("Authentication required")

                # Authenticate user
                if username:
                    span.set_attribute("user.name", username)
                    auth_result = await self.auth.authenticate(username)

                    if not auth_result["authorized"]:
                        logger.warning(
                            "Authentication failed", extra={"username": username, "reason": auth_result.get("reason")}
                        )
                        metrics.auth_failures.add(1)
                        raise PermissionError(f"Authentication failed: {auth_result.get('reason', 'unknown')}")

                    user_id = auth_result["user_id"]
                    span.set_attribute("user.id", user_id)

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

                # Route to appropriate handler
                if name == "chat":
                    return await self._handle_chat(arguments, span, user_id)
                elif name == "get_conversation":
                    return await self._handle_get_conversation(arguments, span, user_id)
                elif name == "list_conversations":
                    return await self._handle_list_conversations(arguments, span, user_id)
                else:
                    raise ValueError(f"Unknown tool: {name}")

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources"""
            with tracer.start_as_current_span("mcp.list_resources"):
                return [Resource(uri="agent://config", name="Agent Configuration", mimeType="application/json")]

    async def _handle_chat(self, arguments: dict[str, Any], span, user_id: str) -> list[TextContent]:
        """Handle chat tool invocation"""
        with tracer.start_as_current_span("agent.chat"):
            message = arguments["message"]
            thread_id = arguments.get("thread_id", "default")

            span.set_attribute("message.length", len(message))
            span.set_attribute("thread.id", thread_id)
            span.set_attribute("user.id", user_id)

            # Check if user can access this conversation
            conversation_resource = f"conversation:{thread_id}"

            can_edit = await self.auth.authorize(user_id=user_id, relation="editor", resource=conversation_resource)

            if not can_edit:
                logger.warning("User cannot edit conversation", extra={"user_id": user_id, "thread_id": thread_id})
                raise PermissionError(f"Not authorized to edit conversation {thread_id}")

            logger.info(
                "Processing chat message", extra={"thread_id": thread_id, "user_id": user_id, "message_preview": message[:100]}
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
                result = await asyncio.to_thread(agent_graph.invoke, initial_state, config)

                # Extract response
                response_message = result["messages"][-1]
                response_text = response_message.content

                span.set_attribute("response.length", len(response_text))
                metrics.successful_calls.add(1, {"tool": "chat"})

                logger.info("Chat response generated", extra={"thread_id": thread_id, "response_length": len(response_text)})

                return [TextContent(type="text", text=response_text)]

            except Exception as e:
                logger.error(f"Error processing chat: {e}", extra={"error": str(e), "thread_id": thread_id}, exc_info=True)
                metrics.failed_calls.add(1, {"tool": "chat", "error": type(e).__name__})
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

    async def _handle_list_conversations(self, arguments: dict[str, Any], span, user_id: str) -> list[TextContent]:
        """List all conversations user has access to"""
        with tracer.start_as_current_span("agent.list_conversations"):
            # Get all conversations user can view
            conversations = await self.auth.list_accessible_resources(
                user_id=user_id, relation="viewer", resource_type="conversation"
            )

            logger.info("Listed conversations", extra={"user_id": user_id, "count": len(conversations)})

            return [TextContent(type="text", text=f"Accessible conversations: {', '.join(conversations)}")]


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
