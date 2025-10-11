"""
MCP Server implementation for LangGraph agent with OpenFGA and Infisical
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from pydantic import BaseModel, Field

from agent import AgentState, agent_graph
from auth import AuthMiddleware
from config import settings
from observability import logger, metrics, tracer
from openfga_client import OpenFGAClient


class ChatInput(BaseModel):
    """Input schema for chat tool"""

    message: str = Field(description="The user message to send to the agent")
    username: str = Field(description="Username for authentication")
    thread_id: str | None = Field(default=None, description="Optional thread ID for conversation continuity")


class MCPAgentServer:
    """MCP Server exposing LangGraph agent with OpenFGA authorization"""

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
                "request_id": span.get_span_context().trace_id,
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

    async def run(self):
        """Run the MCP server"""
        logger.info("Starting MCP Agent Server")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())


async def main():
    """Main entry point"""
    server = MCPAgentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
