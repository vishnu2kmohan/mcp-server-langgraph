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

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage
from mcp.server import Server
from mcp.types import Resource, TextContent, Tool
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.factory import create_auth_middleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.user_provider import KeycloakUserProvider
from mcp_server_langgraph.core.agent import AgentState, get_agent_graph
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.utils.response_optimizer import format_response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for application startup and shutdown.

    CRITICAL: This ensures observability is initialized before handling requests,
    preventing crashes when launching with: uvicorn mcp_server_langgraph.mcp.server_streamable:app

    Without this handler, logger/tracer/metrics usage in get_mcp_server() and downstream
    code would fail when observability hasn't been initialized yet.
    """
    # Startup
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    if not is_initialized():
        logger_temp = logging.getLogger(__name__)
        logger_temp.info("Initializing observability from startup event")

        # Initialize with file logging if configured
        enable_file_logging = getattr(settings, "enable_file_logging", False)
        init_observability(settings=settings, enable_file_logging=enable_file_logging)

        logger_temp.info("Observability initialized successfully")

    # Initialize global auth middleware for FastAPI dependencies
    # This must happen AFTER observability is initialized (for logging)
    try:
        from mcp_server_langgraph.auth.middleware import FASTAPI_AVAILABLE, set_global_auth_middleware

        if FASTAPI_AVAILABLE:
            # Get MCP server instance (creates it if needed)
            mcp_server = get_mcp_server()

            # Set the auth middleware globally for FastAPI dependencies
            set_global_auth_middleware(mcp_server.auth)

            logger.info("Global auth middleware initialized for FastAPI dependencies")
    except Exception as e:
        logger.warning(f"Failed to initialize global auth middleware: {e}")

    yield

    # Shutdown (if needed in the future)
    pass


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
    lifespan=lifespan,
)

# CORS middleware
# SECURITY: Use config-based origins instead of wildcard
# Empty list = no CORS (production default), specific origins in development
cors_origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True if cors_origins else False,  # Only allow credentials if origins specified
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
    token: str = Field(
        description=(
            "JWT authentication token. Obtain via /auth/login endpoint (HTTP) "
            "or external authentication service. Required for all tool calls."
        )
    )
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
    token: str = Field(
        description=(
            "JWT authentication token. Obtain via /auth/login endpoint (HTTP) "
            "or external authentication service. Required for all tool calls."
        )
    )
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

    def __init__(self, openfga_client: OpenFGAClient | None = None) -> None:
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

        # SECURITY: Fail-closed pattern - require OpenFGA in production
        if settings.environment == "production" and self.openfga is None:
            raise ValueError(
                "CRITICAL: OpenFGA authorization is required in production mode. "
                "Configure OPENFGA_STORE_ID and OPENFGA_MODEL_ID environment variables, "
                "or set ENVIRONMENT=development for local testing. "
                "Fallback authorization is not secure enough for production use."
            )

        # Initialize auth using factory (respects settings.auth_provider)
        self.auth = create_auth_middleware(settings, openfga_client=self.openfga)

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

    async def list_tools_public(self) -> list[Tool]:
        """
        Public API to list available tools.

        This wraps the internal MCP handler to avoid accessing private SDK attributes.
        """
        # Call the registered handler
        # The handler is registered below in _setup_handlers()
        return await self._list_tools_handler()  # type: ignore[no-any-return]

    async def call_tool_public(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Public API to call a tool.

        This wraps the internal MCP handler to avoid accessing private SDK attributes.
        """
        return await self._call_tool_handler(name, arguments)  # type: ignore[no-any-return]

    async def list_resources_public(self) -> list[Resource]:
        """
        Public API to list available resources.

        This wraps the internal MCP handler to avoid accessing private SDK attributes.
        """
        return await self._list_resources_handler()  # type: ignore[no-any-return]

    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers and store references for public API"""

        @self.server.list_tools()  # type: ignore[misc,no-untyped-call]
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
                                "token": {
                                    "type": "string",
                                    "description": "JWT authentication token. Required for all tool calls.",
                                },
                                "user_id": {
                                    "type": "string",
                                    "description": "User identifier for authentication and authorization",
                                },
                                "username": {"type": "string", "description": "DEPRECATED: Use 'user_id' instead"},
                            },
                            "required": ["thread_id", "token", "user_id"],
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

        # Store reference to handler for public API
        self._list_tools_handler = list_tools

        @self.server.call_tool()  # type: ignore[misc]
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls with OpenFGA authorization and tracing"""

            with tracer.start_as_current_span("mcp.call_tool", attributes={"tool.name": name}) as span:
                logger.info(f"Tool called: {name}", extra={"tool": name, "tool_args": arguments})
                metrics.tool_calls.add(1, {"tool": name})

                # SECURITY: Require JWT token for all tool calls
                token = arguments.get("token")

                if not token:
                    logger.warning("No authentication token provided")
                    metrics.auth_failures.add(1)
                    raise PermissionError(
                        "Authentication token required. Provide 'token' parameter with a valid JWT. "
                        "Obtain token via /auth/login endpoint or external authentication service."
                    )

                # Verify JWT token
                token_verification = await self.auth.verify_token(token)

                if not token_verification.valid:
                    logger.warning("Token verification failed", extra={"error": token_verification.error})
                    metrics.auth_failures.add(1)
                    raise PermissionError(
                        f"Invalid authentication token: {token_verification.error or 'token verification failed'}"
                    )

                # Extract user_id from validated token payload
                if not token_verification.payload or "sub" not in token_verification.payload:
                    logger.error("Token payload missing 'sub' claim")
                    metrics.auth_failures.add(1)
                    raise PermissionError("Invalid token: missing user identifier")

                user_id = token_verification.payload["sub"]
                span.set_attribute("user.id", user_id)

                logger.info("User authenticated via token", extra={"user_id": user_id, "tool": name})

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

        # Store reference to handler for public API
        self._call_tool_handler = call_tool

        @self.server.list_resources()  # type: ignore[misc,no-untyped-call]
        async def list_resources() -> list[Resource]:
            """List available resources"""
            with tracer.start_as_current_span("mcp.list_resources"):
                # type: ignore[arg-type]
                return [Resource(uri="agent://config", name="Agent Configuration", mimeType="application/json")]

        # Store reference to handler for public API
        self._list_resources_handler = list_resources

    async def _handle_chat(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
        """
        Handle agent_chat tool invocation.

        Implements Anthropic best practices:
        - Response format control (concise vs detailed)
        - Token-efficient responses with truncation
        - Clear error messages
        - Performance tracking
        """
        with tracer.start_as_current_span("agent.chat"):
            # BUGFIX: Validate input with Pydantic schema to enforce length limits and required fields
            try:
                chat_input = ChatInput.model_validate(arguments)
            except Exception as e:
                logger.error(f"Invalid chat input: {e}", extra={"arguments": arguments})
                raise ValueError(f"Invalid chat input: {e}")

            message = chat_input.message
            thread_id = chat_input.thread_id or "default"
            response_format_type = chat_input.response_format

            span.set_attribute("message.length", len(message))
            span.set_attribute("thread.id", thread_id)
            span.set_attribute("user.id", user_id)
            span.set_attribute("response.format", response_format_type)

            # Check if user can access this conversation
            # BUGFIX: Allow first-time conversation creation without pre-existing OpenFGA tuples
            # For new conversations, we short-circuit authorization and will seed ownership after creation
            conversation_resource = f"conversation:{thread_id}"

            # Check if conversation exists by trying to get state from checkpointer
            graph = get_agent_graph()  # type: ignore[func-returns-value]
            conversation_exists = False
            if hasattr(graph, "checkpointer") and graph.checkpointer is not None:
                try:
                    config = {"configurable": {"thread_id": thread_id}}
                    state_snapshot = await graph.aget_state(config)
                    conversation_exists = state_snapshot is not None and state_snapshot.values is not None
                except Exception:
                    # If we can't check, assume it doesn't exist (fail-open for creation)
                    conversation_exists = False

            # Only check authorization for existing conversations
            if conversation_exists:
                can_edit = await self.auth.authorize(user_id=user_id, relation="editor", resource=conversation_resource)
                if not can_edit:
                    logger.warning("User cannot edit conversation", extra={"user_id": user_id, "thread_id": thread_id})
                    raise PermissionError(
                        f"Not authorized to edit conversation '{thread_id}'. "
                        f"Request access from conversation owner or use a different thread_id."
                    )
            else:
                # New conversation - user becomes implicit owner (OpenFGA tuples should be seeded after creation)
                logger.info(
                    "Creating new conversation, user granted implicit ownership",
                    extra={"user_id": user_id, "thread_id": thread_id},
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

            # Create initial state with proper LangChain message objects
            # BUGFIX: Use HumanMessage instead of dict to avoid type errors in graph nodes
            initial_state: AgentState = {
                "messages": [HumanMessage(content=message)],
                "next_action": "",
                "user_id": user_id,
                "request_id": str(span.get_span_context().trace_id) if span.get_span_context() else None,
                "routing_confidence": None,
                "reasoning": None,
                "compaction_applied": None,
                "original_message_count": None,
                "verification_passed": None,
                "verification_score": None,
                "verification_feedback": None,
                "refinement_attempts": None,
                "user_request": message,
            }

            # Run the agent graph
            config = {"configurable": {"thread_id": thread_id}}

            try:
                result = await get_agent_graph().ainvoke(initial_state, config)  # type: ignore[func-returns-value]

                # Seed OpenFGA tuples for new conversations
                if not conversation_exists and self.openfga is not None:
                    try:
                        # Create ownership, viewer, and editor tuples in batch
                        await self.openfga.write_tuples(
                            [
                                {"user": user_id, "relation": "owner", "object": conversation_resource},
                                {"user": user_id, "relation": "viewer", "object": conversation_resource},
                                {"user": user_id, "relation": "editor", "object": conversation_resource},
                            ]
                        )

                        logger.info(
                            "OpenFGA tuples seeded for new conversation",
                            extra={"user_id": user_id, "thread_id": thread_id},
                        )

                    except Exception as e:
                        # Log warning but don't fail the request
                        # The conversation was created successfully, ACL seeding is best-effort
                        logger.warning(
                            f"Failed to seed OpenFGA tuples for new conversation: {e}",
                            extra={"user_id": user_id, "thread_id": thread_id},
                            exc_info=True,
                        )

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

    async def _handle_get_conversation(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
        """
        Retrieve conversation history from LangGraph checkpointer.

        Returns formatted conversation with messages, metadata, and participants.
        """
        with tracer.start_as_current_span("agent.get_conversation"):
            thread_id = arguments["thread_id"]

            # Check if user can view this conversation
            conversation_resource = f"conversation:{thread_id}"

            can_view = await self.auth.authorize(user_id=user_id, relation="viewer", resource=conversation_resource)

            if not can_view:
                logger.warning("User cannot view conversation", extra={"user_id": user_id, "thread_id": thread_id})
                raise PermissionError(f"Not authorized to view conversation {thread_id}")

            # Retrieve conversation from checkpointer
            graph = get_agent_graph()  # type: ignore[func-returns-value]

            if not hasattr(graph, "checkpointer") or graph.checkpointer is None:
                logger.warning("No checkpointer available, cannot retrieve conversation history")
                return [
                    TextContent(
                        type="text",
                        text="Conversation history unavailable: checkpointing is disabled. "
                        "Enable checkpointing to persist conversation history.",
                    )
                ]

            try:
                config = {"configurable": {"thread_id": thread_id}}
                state_snapshot = await graph.aget_state(config)

                if state_snapshot is None or state_snapshot.values is None:
                    logger.info("Conversation not found", extra={"thread_id": thread_id})
                    return [TextContent(type="text", text=f"Conversation '{thread_id}' not found or has no history.")]

                # Extract messages from state
                messages = state_snapshot.values.get("messages", [])

                if not messages:
                    return [TextContent(type="text", text=f"Conversation '{thread_id}' has no messages yet.")]

                # Format conversation history
                formatted_lines = [f"Conversation: {thread_id}", f"Messages: {len(messages)}", ""]

                for i, msg in enumerate(messages, 1):
                    msg_type = type(msg).__name__
                    content = getattr(msg, "content", str(msg))

                    # Truncate long messages for readability
                    if len(content) > 200:
                        content = content[:200] + "..."

                    formatted_lines.append(f"{i}. [{msg_type}] {content}")

                # Add metadata if available
                metadata = state_snapshot.values.get("metadata", {})
                if metadata:
                    formatted_lines.append("")
                    formatted_lines.append("Metadata:")
                    for key, value in metadata.items():
                        formatted_lines.append(f"  {key}: {value}")

                response_text = "\n".join(formatted_lines)

                logger.info(
                    "Conversation history retrieved",
                    extra={"thread_id": thread_id, "message_count": len(messages), "user_id": user_id},
                )

                return [TextContent(type="text", text=response_text)]

            except Exception as e:
                logger.error(f"Failed to retrieve conversation history: {e}", extra={"thread_id": thread_id}, exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"Error retrieving conversation history: {str(e)}",
                    )
                ]

    async def _handle_search_conversations(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
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
            # BUGFIX: Validate input with Pydantic schema to enforce query length and limit constraints
            try:
                search_input = SearchConversationsInput.model_validate(arguments)
            except Exception as e:
                logger.error(f"Invalid search input: {e}", extra={"arguments": arguments})
                raise ValueError(f"Invalid search input: {e}")

            query = search_input.query
            limit = search_input.limit

            span.set_attribute("search.query", query)
            span.set_attribute("search.limit", limit)

            # Get all conversations user can view
            all_conversations = await self.auth.list_accessible_resources(
                user_id=user_id, relation="viewer", resource_type="conversation"
            )

            # Filter conversations based on query (simple implementation)
            # In production, this would use a proper search index
            # Normalize query and conversation names to handle spaces/underscores/hyphens
            if query:
                normalized_query = query.lower().replace(" ", "_").replace("-", "_")
                filtered_conversations = [
                    conv
                    for conv in all_conversations
                    if (query.lower() in conv.lower() or normalized_query in conv.lower().replace(" ", "_").replace("-", "_"))
                ]
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


# ============================================================================
# Lazy Singleton Pattern for MCP Server
# ============================================================================
# Prevents import-time initialization which causes issues with:
# - Missing environment variables
# - Observability not yet initialized
# - Test dependency injection

_mcp_server_instance: Optional[MCPAgentStreamableServer] = None


def get_mcp_server() -> MCPAgentStreamableServer:
    """
    Get or create the MCP server instance (lazy singleton)

    This ensures the server is only created after observability is initialized,
    avoiding import-time side effects and logging errors.

    Returns:
        MCPAgentStreamableServer singleton instance

    Raises:
        RuntimeError: If observability is not initialized
    """
    from mcp_server_langgraph.observability.telemetry import is_initialized

    # Guard: Ensure observability is initialized before creating server
    if not is_initialized():
        raise RuntimeError(
            "Observability must be initialized before creating MCP server. "
            "This should be done automatically via the startup event handler. "
            "If you see this error, observability initialization failed or was skipped."
        )

    global _mcp_server_instance
    if _mcp_server_instance is None:
        _mcp_server_instance = MCPAgentStreamableServer()
    return _mcp_server_instance


# ============================================================================
# Authentication Models
# ============================================================================


class LoginRequest(BaseModel):
    """Login request with username and password"""

    username: str = Field(description="Username", min_length=1, max_length=100)
    password: str = Field(description="Password", min_length=1, max_length=500)


class LoginResponse(BaseModel):
    """Login response with JWT token"""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(description="Token expiration in seconds")
    user_id: str = Field(description="User identifier")
    username: str = Field(description="Username")
    roles: list[str] = Field(description="User roles")


class RefreshTokenRequest(BaseModel):
    """Token refresh request"""

    refresh_token: str | None = Field(description="Refresh token (Keycloak only)", default=None)
    current_token: str | None = Field(description="Current access token (for InMemory provider)", default=None)


class RefreshTokenResponse(BaseModel):
    """Token refresh response"""

    access_token: str = Field(description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    refresh_token: str | None = Field(default=None, description="New refresh token (Keycloak only)")


# FastAPI endpoints for MCP StreamableHTTP transport
@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with server info"""
    return {
        "name": "MCP Server with LangGraph",
        "version": settings.service_version,
        "transport": "streamable-http",
        "protocol": "mcp",
        "endpoints": {
            "auth": {
                "login": "/auth/login",
                "refresh": "/auth/refresh",
            },
            "message": "/message",
            "tools": "/tools",
            "resources": "/resources",
            "health": "/health",
        },
        "capabilities": {
            "tools": {"listSupported": True, "callSupported": True},
            "resources": {"listSupported": True, "readSupported": True},
            "streaming": True,
            "authentication": {
                "methods": ["jwt"],
                "tokenRefresh": True,
                "providers": [settings.auth_provider],
            },
        },
    }


@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
async def login(request: LoginRequest) -> LoginResponse:
    """
    Authenticate user and return JWT token

    This endpoint accepts username and password, validates credentials,
    and returns a JWT token that can be used for subsequent tool calls.

    The token should be included in the 'token' field of all tool call requests.

    Example:
        POST /auth/login
        {
            "username": "alice",
            "password": "alice123"
        }

        Response:
        {
            "access_token": "eyJ...",
            "token_type": "bearer",
            "expires_in": 3600,
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["user", "premium"]
        }
    """
    with tracer.start_as_current_span("auth.login") as span:
        span.set_attribute("auth.username", request.username)

        # Get MCP server instance (which has auth middleware)
        mcp_server_instance = get_mcp_server()

        # Authenticate user via configured provider
        auth_result = await mcp_server_instance.auth.user_provider.authenticate(request.username, request.password)

        if not auth_result.authorized:
            logger.warning(
                "Login failed", extra={"username": request.username, "reason": auth_result.reason, "error": auth_result.error}
            )
            metrics.auth_failures.add(1)
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {auth_result.reason or auth_result.error or 'invalid credentials'}",
            )

        # Create JWT token
        # For InMemoryUserProvider, use the create_token method
        # For KeycloakUserProvider, tokens are returned directly in auth_result
        if auth_result.access_token:
            # Keycloak provider returns token directly
            access_token = auth_result.access_token
            expires_in = auth_result.expires_in or 3600
        else:
            # InMemoryUserProvider needs to create token
            try:
                access_token = mcp_server_instance.auth.create_token(
                    username=request.username, expires_in=settings.jwt_expiration_seconds
                )
                expires_in = settings.jwt_expiration_seconds
            except Exception as e:
                logger.error(f"Failed to create token: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to create authentication token")

        logger.info(
            "Login successful",
            extra={
                "username": request.username,
                "user_id": auth_result.user_id,
                "provider": type(mcp_server_instance.auth.user_provider).__name__,
            },
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user_id=auth_result.user_id or "",
            username=auth_result.username or request.username,
            roles=auth_result.roles or [],
        )


@app.post("/auth/refresh", response_model=RefreshTokenResponse, tags=["auth"])
async def refresh_token(request: RefreshTokenRequest) -> RefreshTokenResponse:
    """
    Refresh authentication token

    Supports two refresh methods:
    1. Keycloak: Uses refresh_token to get new access token
    2. InMemory: Validates current token and issues new one

    Example (Keycloak):
        POST /auth/refresh
        {
            "refresh_token": "eyJ..."
        }

    Example (InMemory):
        POST /auth/refresh
        {
            "current_token": "eyJ..."
        }

    Response:
        {
            "access_token": "eyJ...",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "eyJ..."  // Keycloak only
        }
    """
    with tracer.start_as_current_span("auth.refresh") as span:
        mcp_server_instance = get_mcp_server()

        # Handle Keycloak refresh token
        if request.refresh_token:
            if not isinstance(mcp_server_instance.auth.user_provider, KeycloakUserProvider):
                logger.warning("Refresh token provided but provider is not Keycloak")
                raise HTTPException(
                    status_code=400,
                    detail="Refresh tokens are only supported with KeycloakUserProvider. "
                    "Current provider does not support refresh tokens.",
                )

            try:
                # Use KeycloakUserProvider's refresh_token method
                result = await mcp_server_instance.auth.user_provider.refresh_token(request.refresh_token)

                if not result.get("success"):
                    raise HTTPException(status_code=401, detail=f"Token refresh failed: {result.get('error')}")

                tokens = result["tokens"]

                logger.info("Token refreshed via Keycloak")

                return RefreshTokenResponse(
                    access_token=tokens["access_token"],
                    token_type="bearer",
                    expires_in=tokens.get("expires_in", 300),
                    refresh_token=tokens.get("refresh_token"),
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Token refresh failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Token refresh failed")

        # Handle InMemory token refresh (verify current token and issue new one)
        elif request.current_token:
            try:
                # Verify current token
                token_verification = await mcp_server_instance.auth.verify_token(request.current_token)

                if not token_verification.valid:
                    logger.warning("Current token invalid for refresh", extra={"error": token_verification.error})
                    raise HTTPException(status_code=401, detail=f"Invalid token: {token_verification.error}")

                # Extract user info from token
                if not token_verification.payload or "username" not in token_verification.payload:
                    raise HTTPException(status_code=401, detail="Invalid token: missing username")

                username = token_verification.payload["username"]
                span.set_attribute("auth.username", username)

                # Issue new token
                new_token = mcp_server_instance.auth.create_token(
                    username=username, expires_in=settings.jwt_expiration_seconds
                )

                logger.info("Token refreshed for user", extra={"username": username})

                return RefreshTokenResponse(
                    access_token=new_token,
                    token_type="bearer",
                    expires_in=settings.jwt_expiration_seconds,
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Token refresh failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Token refresh failed")

        else:
            raise HTTPException(
                status_code=400, detail="Either 'refresh_token' (Keycloak) or 'current_token' (InMemory) must be provided"
            )


async def stream_jsonrpc_response(data: dict[str, Any]) -> AsyncIterator[str]:
    """
    Stream a JSON-RPC response in chunks

    Yields newline-delimited JSON for streaming responses
    """
    # For now, send the complete response
    # In the future, this could stream token-by-token for LLM responses
    yield json.dumps(data) + "\n"


@app.post("/message", response_model=None)
async def handle_message(request: Request) -> JSONResponse | StreamingResponse:
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
                # Use public API instead of private _tool_manager
                tools = await get_mcp_server().list_tools_public()
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"tools": [tool.model_dump(mode="json") for tool in tools]},
                }
                return JSONResponse(response)

            elif method == "tools/call":
                params = message.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                # Check if client supports streaming
                accept_header = request.headers.get("accept", "")
                supports_streaming = "text/event-stream" in accept_header or "application/x-ndjson" in accept_header

                # Use public API instead of private _tool_manager
                result = await get_mcp_server().call_tool_public(tool_name, arguments)

                response_data = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"content": [item.model_dump(mode="json") for item in result]},
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
                # Use public API instead of private _resource_manager
                resources = await get_mcp_server().list_resources_public()
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"resources": [res.model_dump(mode="json") for res in resources]},
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
            status_code=200,  # JSON-RPC errors should return 200 with error in body
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if "message" in locals() else None,
                "error": {"code": -32001, "message": str(e)},
            },
        )
    except ValueError as e:
        # Validation errors (missing fields, invalid arguments)
        logger.warning(f"Validation error: {e}")
        return JSONResponse(
            status_code=200,  # JSON-RPC errors should return 200 with error in body
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if "message" in locals() else None,
                "error": {"code": -32602, "message": f"Invalid params: {str(e)}"},
            },
        )
    except HTTPException as e:
        # HTTP exceptions (unknown methods, etc.)
        logger.warning(f"HTTP exception: {e.detail}")
        return JSONResponse(
            status_code=200,  # JSON-RPC errors should return 200 with error in body
            content={
                "jsonrpc": "2.0",
                "id": message.get("id") if "message" in locals() else None,
                "error": {"code": -32601 if e.status_code == 400 else -32603, "message": e.detail},
            },
        )
    except json.JSONDecodeError as e:
        # Invalid JSON in request body
        logger.warning(f"JSON parse error: {e}")
        return JSONResponse(
            status_code=400,  # Parse errors can return 400
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error: Invalid JSON"},
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
async def list_tools() -> dict[str, Any]:
    """List available tools (convenience endpoint)"""
    # Use public API instead of private _tool_manager
    tools = await get_mcp_server().list_tools_public()
    return {"tools": [tool.model_dump(mode="json") for tool in tools]}


@app.get("/resources")
async def list_resources() -> dict[str, Any]:
    """List available resources (convenience endpoint)"""
    # Use public API instead of private _resource_manager
    resources = await get_mcp_server().list_resources_public()
    return {"resources": [res.model_dump(mode="json") for res in resources]}


# Include health check routes
from mcp_server_langgraph.health.checks import app as health_app  # noqa: E402

app.mount("/health", health_app)

# Include GDPR compliance routes
from mcp_server_langgraph.api.gdpr import router as gdpr_router  # noqa: E402

app.include_router(gdpr_router)


def main() -> None:
    """Entry point for console script"""
    # Initialize observability system before creating server
    from mcp_server_langgraph.core.config import settings
    from mcp_server_langgraph.observability.telemetry import init_observability

    # Initialize with settings and enable file logging if configured
    init_observability(settings=settings, enable_file_logging=getattr(settings, "enable_file_logging", False))

    # SECURITY: Validate CORS configuration before starting server
    settings.validate_cors_config()

    logger.info(f"Starting MCP StreamableHTTP server on port {settings.get_secret('PORT', fallback='8000')}")

    port_str = settings.get_secret("PORT", fallback="8000")
    port = int(port_str) if port_str else 8000

    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 - Required for containerized deployment
        port=port,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
