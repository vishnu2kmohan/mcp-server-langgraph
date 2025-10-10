"""
MCP Server with HTTP/SSE (Server-Sent Events) transport
Implements the MCP Streaming HTTP specification
"""
import asyncio
from typing import Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn

from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
from pydantic import BaseModel, Field

from agent import agent_graph, AgentState
from observability import tracer, logger, metrics
from auth import AuthMiddleware
from openfga_client import OpenFGAClient
from config import settings


app = FastAPI(
    title="LangGraph MCP Agent",
    description="AI Agent with fine-grained authorization and observability",
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatInput(BaseModel):
    """Input schema for chat tool"""
    message: str = Field(description="The user message to send to the agent")
    username: str = Field(description="Username for authentication")
    thread_id: str | None = Field(default=None, description="Optional thread ID for conversation continuity")


class MCPAgentHTTPServer:
    """MCP Server with HTTP/SSE transport"""

    def __init__(self, openfga_client: OpenFGAClient | None = None):
        self.server = Server("langgraph-agent")

        # Initialize OpenFGA client
        self.openfga = openfga_client or self._create_openfga_client()

        # Initialize auth with OpenFGA
        self.auth = AuthMiddleware(
            secret_key=settings.jwt_secret_key or "change-this-in-production",
            openfga_client=self.openfga
        )

        self._setup_handlers()

    def _create_openfga_client(self) -> OpenFGAClient | None:
        """Create OpenFGA client from settings"""
        if settings.openfga_store_id and settings.openfga_model_id:
            logger.info(
                "Initializing OpenFGA client",
                extra={
                    "store_id": settings.openfga_store_id,
                    "model_id": settings.openfga_model_id
                }
            )
            return OpenFGAClient(
                api_url=settings.openfga_api_url,
                store_id=settings.openfga_store_id,
                model_id=settings.openfga_model_id
            )
        else:
            logger.warning(
                "OpenFGA not configured, authorization will use fallback mode"
            )
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
                        description="Chat with the AI agent. The agent can help with questions, research, and problem-solving.",
                        inputSchema=ChatInput.model_json_schema()
                    ),
                    Tool(
                        name="get_conversation",
                        description="Retrieve a conversation thread by ID",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "thread_id": {"type": "string"},
                                "username": {"type": "string"}
                            },
                            "required": ["thread_id", "username"]
                        }
                    ),
                    Tool(
                        name="list_conversations",
                        description="List all conversations the user has access to",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"}
                            },
                            "required": ["username"]
                        }
                    )
                ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls with OpenFGA authorization and tracing"""

            with tracer.start_as_current_span(
                "mcp.call_tool",
                attributes={"tool.name": name}
            ) as span:
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
                            "Authentication failed",
                            extra={"username": username, "reason": auth_result.get("reason")}
                        )
                        metrics.auth_failures.add(1)
                        raise PermissionError(f"Authentication failed: {auth_result.get('reason', 'unknown')}")

                    user_id = auth_result["user_id"]
                    span.set_attribute("user.id", user_id)

                # Check OpenFGA authorization
                resource = f"tool:{name}"

                authorized = await self.auth.authorize(
                    user_id=user_id,
                    relation="executor",
                    resource=resource
                )

                if not authorized:
                    logger.warning(
                        "Authorization failed (OpenFGA)",
                        extra={
                            "user_id": user_id,
                            "resource": resource,
                            "relation": "executor"
                        }
                    )
                    metrics.authz_failures.add(1, {"resource": resource})
                    raise PermissionError(f"Not authorized to execute {resource}")

                logger.info(
                    "Authorization granted",
                    extra={
                        "user_id": user_id,
                        "resource": resource
                    }
                )

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
                return [
                    Resource(
                        uri="agent://config",
                        name="Agent Configuration",
                        mimeType="application/json"
                    )
                ]

    async def _handle_chat(
        self,
        arguments: dict[str, Any],
        span,
        user_id: str
    ) -> list[TextContent]:
        """Handle chat tool invocation"""
        with tracer.start_as_current_span("agent.chat"):
            message = arguments["message"]
            thread_id = arguments.get("thread_id", "default")

            span.set_attribute("message.length", len(message))
            span.set_attribute("thread.id", thread_id)
            span.set_attribute("user.id", user_id)

            # Check if user can access this conversation
            conversation_resource = f"conversation:{thread_id}"

            can_edit = await self.auth.authorize(
                user_id=user_id,
                relation="editor",
                resource=conversation_resource
            )

            if not can_edit:
                logger.warning(
                    "User cannot edit conversation",
                    extra={
                        "user_id": user_id,
                        "thread_id": thread_id
                    }
                )
                raise PermissionError(f"Not authorized to edit conversation {thread_id}")

            logger.info(
                "Processing chat message",
                extra={
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "message_preview": message[:100]
                }
            )

            # Create initial state
            initial_state: AgentState = {
                "messages": [{"role": "user", "content": message}],
                "next_action": "",
                "user_id": user_id,
                "request_id": span.get_span_context().trace_id
            }

            # Run the agent graph
            config = {"configurable": {"thread_id": thread_id}}

            try:
                result = await asyncio.to_thread(
                    agent_graph.invoke,
                    initial_state,
                    config
                )

                # Extract response
                response_message = result["messages"][-1]
                response_text = response_message.content

                span.set_attribute("response.length", len(response_text))
                metrics.successful_calls.add(1, {"tool": "chat"})

                logger.info(
                    "Chat response generated",
                    extra={
                        "thread_id": thread_id,
                        "response_length": len(response_text)
                    }
                )

                return [TextContent(
                    type="text",
                    text=response_text
                )]

            except Exception as e:
                logger.error(
                    f"Error processing chat: {e}",
                    extra={"error": str(e), "thread_id": thread_id},
                    exc_info=True
                )
                metrics.failed_calls.add(1, {"tool": "chat", "error": type(e).__name__})
                span.record_exception(e)
                raise

    async def _handle_get_conversation(
        self,
        arguments: dict[str, Any],
        span,
        user_id: str
    ) -> list[TextContent]:
        """Retrieve conversation history"""
        with tracer.start_as_current_span("agent.get_conversation"):
            thread_id = arguments["thread_id"]

            # Check if user can view this conversation
            conversation_resource = f"conversation:{thread_id}"

            can_view = await self.auth.authorize(
                user_id=user_id,
                relation="viewer",
                resource=conversation_resource
            )

            if not can_view:
                logger.warning(
                    "User cannot view conversation",
                    extra={
                        "user_id": user_id,
                        "thread_id": thread_id
                    }
                )
                raise PermissionError(f"Not authorized to view conversation {thread_id}")

            # In production, retrieve from checkpoint storage
            # For now, return placeholder
            return [TextContent(
                type="text",
                text=f"Conversation history for thread {thread_id}"
            )]

    async def _handle_list_conversations(
        self,
        arguments: dict[str, Any],
        span,
        user_id: str
    ) -> list[TextContent]:
        """List all conversations user has access to"""
        with tracer.start_as_current_span("agent.list_conversations"):
            # Get all conversations user can view
            conversations = await self.auth.list_accessible_resources(
                user_id=user_id,
                relation="viewer",
                resource_type="conversation"
            )

            logger.info(
                "Listed conversations",
                extra={
                    "user_id": user_id,
                    "count": len(conversations)
                }
            )

            return [TextContent(
                type="text",
                text=f"Accessible conversations: {', '.join(conversations)}"
            )]


# Initialize the MCP server
mcp_server = MCPAgentHTTPServer()


# FastAPI endpoints for MCP HTTP/SSE transport
@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "LangGraph MCP Agent",
        "version": settings.service_version,
        "transport": "http-sse",
        "protocol": "mcp",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages",
            "tools": "/tools",
            "resources": "/resources",
            "health": "/health"
        }
    }


@app.get("/sse")
async def sse_endpoint(request: Request):
    """
    SSE endpoint for MCP streaming transport

    Client connects to this endpoint to receive server-sent events
    """
    async def event_generator():
        """Generate SSE events"""
        try:
            # Send initial connection event
            yield {
                "event": "connected",
                "data": {
                    "server": "langgraph-agent",
                    "version": settings.service_version,
                    "transport": "http-sse"
                }
            }

            # Keep connection alive with periodic pings
            while True:
                if await request.is_disconnected():
                    logger.info("SSE client disconnected")
                    break

                # Send ping every 30 seconds
                yield {
                    "event": "ping",
                    "data": {"timestamp": asyncio.get_event_loop().time()}
                }

                await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info("SSE connection cancelled")
        except Exception as e:
            logger.error(f"SSE error: {e}", exc_info=True)

    return EventSourceResponse(event_generator())


@app.post("/messages")
async def handle_message(request: Request):
    """
    Handle MCP messages via HTTP POST

    This is the main endpoint for MCP protocol messages
    """
    try:
        message = await request.json()

        with tracer.start_as_current_span("mcp.http.message") as span:
            span.set_attribute("mcp.method", message.get("method", "unknown"))

            logger.info(
                "Received MCP message",
                extra={"method": message.get("method")}
            )

            # Handle different MCP methods
            method = message.get("method")

            if method == "tools/list":
                tools = await mcp_server.server._tool_manager.list_tools()
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "tools": [tool.model_dump() for tool in tools]
                    }
                })

            elif method == "tools/call":
                params = message.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                result = await mcp_server.server._tool_manager.call_tool(
                    tool_name,
                    arguments
                )

                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "content": [item.model_dump() for item in result]
                    }
                })

            elif method == "resources/list":
                resources = await mcp_server.server._resource_manager.list_resources()
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "resources": [res.model_dump() for res in resources]
                    }
                })

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown method: {method}"
                )

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if "message" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
        )


@app.get("/tools")
async def list_tools():
    """List available tools (convenience endpoint)"""
    tools = await mcp_server.server._tool_manager.list_tools()
    return {
        "tools": [tool.model_dump() for tool in tools]
    }


@app.get("/resources")
async def list_resources():
    """List available resources (convenience endpoint)"""
    resources = await mcp_server.server._resource_manager.list_resources()
    return {
        "resources": [res.model_dump() for res in resources]
    }


# Include health check routes
from health_check import app as health_app
app.mount("/health", health_app)


if __name__ == "__main__":
    logger.info(f"Starting MCP HTTP/SSE server on port {settings.get_secret('PORT', fallback='8000')}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(settings.get_secret("PORT", fallback="8000")),
        log_level=settings.log_level.lower(),
        access_log=True
    )
