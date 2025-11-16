"""
MCP Server implementation for LangGraph agent with OpenFGA and Infisical

Implements Anthropic's best practices for writing tools for agents:
- Token-efficient responses with truncation
- Search-focused tools instead of list-all
- Response format control (concise vs detailed)
- Namespaced tools for clarity
- High-signal information in responses
"""

import asyncio
import time
from typing import Any, Literal

from langchain_core.messages import HumanMessage
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl, BaseModel, Field

from mcp_server_langgraph.auth.factory import create_auth_middleware
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.core.agent import AgentState, get_agent_graph
from mcp_server_langgraph.core.config import Settings, settings
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.utils.response_optimizer import format_response


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
    user_id: str = Field(
        description=(
            "User identifier for authentication and authorization. "
            "Accepts both plain usernames ('alice') and OpenFGA-prefixed IDs ('user:alice'). "
            "The system will normalize both formats automatically."
        )
    )
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

    query: str = Field(
        description="Search query to filter conversations. Empty string returns recent conversations.",
        min_length=0,
        max_length=500,
    )
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


class MCPAgentServer:
    """MCP Server exposing LangGraph agent with OpenFGA authorization"""

    def __init__(
        self,
        openfga_client: OpenFGAClient | None = None,
        auth: AuthMiddleware | None = None,
    ) -> None:
        """
        Initialize MCP Agent Server with optional dependency injection.

        Args:
            openfga_client: Optional OpenFGA client for authorization.
                           If None, creates one from settings.
            auth: Optional pre-configured AuthMiddleware instance.
                  If provided, this takes precedence over creating auth from settings.
                  This enables dependency injection for testing and custom configurations.

        Example:
            # Default creation (production):
            server = MCPAgentServer()

            # Custom auth injection (testing):
            custom_auth = AuthMiddleware(user_provider=custom_provider, ...)
            server = MCPAgentServer(auth=custom_auth)

        OpenAI Codex Finding (2025-11-16):
        ===================================
        Added `auth` parameter for constructor-based dependency injection.
        This allows tests to inject pre-configured AuthMiddleware with registered users,
        fixing the "user not found" failures in integration tests.
        """
        self.server = Server("langgraph-agent")

        # Initialize OpenFGA client
        self.openfga = openfga_client or self._create_openfga_client()

        # Initialize auth middleware
        if auth is not None:
            # Use injected auth (dependency injection pattern)
            logger.info("Using injected AuthMiddleware instance")
            self.auth = auth

            # If injected auth doesn't have OpenFGA but we have a client, update it
            # This handles the case where auth is injected but openfga_client is also provided
            if self.openfga is not None and self.auth.openfga is None:
                logger.info("Updating injected auth with provided OpenFGA client")
                self.auth.openfga = self.openfga
        else:
            # Create auth using factory (respects settings.auth_provider)
            # Validate JWT secret is configured for in-memory auth provider
            # Keycloak uses RS256 with JWKS (public key crypto) and doesn't need JWT_SECRET_KEY
            if settings.auth_provider == "inmemory" and not settings.jwt_secret_key:
                raise ValueError(
                    "CRITICAL: JWT secret key not configured for in-memory auth provider. "
                    "Set JWT_SECRET_KEY environment variable or configure via Infisical. "
                    "The in-memory auth provider requires a secure secret key for HS256 token signing."
                )

            # SECURITY: Fail-closed pattern - require OpenFGA in production
            if settings.environment == "production" and self.openfga is None:
                raise ValueError(
                    "CRITICAL: OpenFGA authorization is required in production mode. "
                    "Configure OPENFGA_STORE_ID and OPENFGA_MODEL_ID environment variables, "
                    "or set ENVIRONMENT=development for local testing. "
                    "Fallback authorization is not secure enough for production use."
                )

            self.auth = create_auth_middleware(settings, openfga_client=self.openfga)

        self._setup_handlers()

    def _create_openfga_client(self, settings_override: Settings | None = None) -> OpenFGAClient | None:
        """
        Create OpenFGA client from settings.

        Args:
            settings_override: Optional settings override for testing/dependency injection.
                              If None, uses global settings.

        Returns:
            OpenFGAClient instance or None if not configured
        """
        _settings = settings_override or settings

        if _settings.openfga_store_id and _settings.openfga_model_id:
            logger.info(
                "Initializing OpenFGA client",
                extra={"store_id": _settings.openfga_store_id, "model_id": _settings.openfga_model_id},
            )
            return OpenFGAClient(
                api_url=_settings.openfga_api_url,
                store_id=_settings.openfga_store_id,
                model_id=_settings.openfga_model_id,
            )
        else:
            logger.warning("OpenFGA not configured, authorization will use fallback mode")
            return None

    async def list_tools_public(self) -> list[Tool]:
        """
        Public method to list available tools (used for testing and external access).

        Returns the same tools list as the MCP protocol handler.
        """
        tools = [
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

        # Add search_tools for progressive discovery (Anthropic best practice)
        tools.append(
            Tool(
                name="search_tools",
                description=(
                    "Search and discover available tools using progressive disclosure. "
                    "Query by keyword or category instead of loading all tool definitions. "
                    "Saves 98%+ tokens compared to list-all approach. "
                    "Detail levels: minimal (name+desc), standard (+params), full (+schema). "
                    "Categories: calculator, search, filesystem, execution. "
                    "Response time: <1 second."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (keyword)"},
                        "category": {"type": "string", "description": "Tool category filter"},
                        "detail_level": {
                            "type": "string",
                            "enum": ["minimal", "standard", "full"],
                            "description": "Level of detail in results",
                        },
                    },
                },
            )
        )

        # Add execute_python if code execution is enabled
        if settings.enable_code_execution:
            from mcp_server_langgraph.tools.code_execution_tools import ExecutePythonInput

            tools.append(
                Tool(
                    name="execute_python",
                    description=(
                        "Execute Python code in a secure sandboxed environment. "
                        "Security: Import whitelist, no eval/exec, resource limits (CPU, memory, timeout). "
                        "Backends: docker-engine (local/dev) or kubernetes (production). "
                        "Network: Configurable isolation (none/allowlist/unrestricted). "
                        "Response time: 1-30 seconds depending on code complexity. "
                        "Use for data processing, calculations, and Python-specific tasks."
                    ),
                    inputSchema=ExecutePythonInput.model_json_schema(),
                )
            )

        return tools

    async def call_tool_public(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Public method to call tools (used for testing and external access).

        This method contains the core tool invocation logic including authentication,
        authorization, and routing. The MCP protocol handler delegates to this method.

        Args:
            name: Name of the tool to call
            arguments: Tool arguments including 'token' for authentication

        Returns:
            List of TextContent responses from the tool

        Raises:
            PermissionError: If authentication or authorization fails
            ValueError: If the tool name is unknown
        """
        with tracer.start_as_current_span("mcp.call_tool", attributes={"tool.name": name}) as span:
            from mcp_server_langgraph.core.security import sanitize_for_logging

            logger.info(f"Tool called: {name}", extra={"tool": name, "args": sanitize_for_logging(arguments)})
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
            elif name == "search_tools":
                return await self._handle_search_tools(arguments, span)
            elif name == "execute_python":
                return await self._handle_execute_python(arguments, span, user_id)
            else:
                raise ValueError(f"Unknown tool: {name}")

    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers"""

        @self.server.list_tools()  # type: ignore[misc,no-untyped-call]  # MCP library decorator lacks type stubs
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
                return await self.list_tools_public()

        @self.server.call_tool()  # type: ignore[misc]
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls with OpenFGA authorization and tracing"""
            return await self.call_tool_public(name, arguments)

        @self.server.list_resources()  # type: ignore[misc,no-untyped-call]  # MCP library decorator lacks type stubs
        async def list_resources() -> list[Resource]:
            """List available resources"""
            with tracer.start_as_current_span("mcp.list_resources"):
                return [Resource(uri=AnyUrl("agent://config"), name="Agent Configuration", mimeType="application/json")]

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
            initial_state: AgentState = {
                "messages": [HumanMessage(content=message)],  # Use HumanMessage, not dict
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

                # Record conversation metadata in store for search functionality
                try:
                    from mcp_server_langgraph.core.storage.conversation_store import get_conversation_store

                    store = get_conversation_store()
                    # Count messages in result
                    message_count = len(result.get("messages", []))
                    # Extract title from first few words of user message
                    title = message[:50] + "..." if len(message) > 50 else message

                    await store.record_conversation(
                        thread_id=thread_id, user_id=user_id, message_count=message_count, title=title
                    )

                    logger.debug(f"Recorded conversation metadata for {thread_id}")
                except Exception as e:
                    # Non-critical - don't fail the request
                    logger.debug(f"Failed to record conversation metadata: {e}")

                return [TextContent(type="text", text=formatted_response)]

            except Exception as e:
                logger.error(f"Error processing chat: {e}", extra={"error": str(e), "thread_id": thread_id}, exc_info=True)
                metrics.failed_calls.add(1, {"tool": "agent_chat", "error": type(e).__name__})
                span.record_exception(e)
                raise

    async def _handle_get_conversation(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
        """Retrieve conversation history from checkpointer"""
        with tracer.start_as_current_span("agent.get_conversation"):
            thread_id = arguments["thread_id"]

            # Check if user can view this conversation
            conversation_resource = f"conversation:{thread_id}"

            can_view = await self.auth.authorize(user_id=user_id, relation="viewer", resource=conversation_resource)

            if not can_view:
                logger.warning("User cannot view conversation", extra={"user_id": user_id, "thread_id": thread_id})
                raise PermissionError(f"Not authorized to view conversation {thread_id}")

            # Retrieve conversation state from checkpointer
            try:
                # Get the checkpointer from agent_graph
                graph = get_agent_graph()  # type: ignore[func-returns-value]
                if not hasattr(graph, "checkpointer") or graph.checkpointer is None:
                    logger.warning("Checkpointing not enabled, cannot retrieve conversation history")
                    return [
                        TextContent(
                            type="text",
                            text=f"Conversation history not available for thread {thread_id}. "
                            "Checkpointing is disabled. Enable it by setting ENABLE_CHECKPOINTING=true.",
                        )
                    ]

                # Get state from checkpointer
                config = {"configurable": {"thread_id": thread_id}}
                state_snapshot = await graph.aget_state(config)

                if not state_snapshot or not state_snapshot.values:
                    logger.info("No conversation history found", extra={"thread_id": thread_id})
                    return [
                        TextContent(
                            type="text",
                            text=f"No conversation history found for thread {thread_id}. "
                            "This thread may not exist or has no messages yet.",
                        )
                    ]

                # Extract messages from state
                messages = state_snapshot.values.get("messages", [])

                if not messages:
                    return [
                        TextContent(
                            type="text",
                            text=f"Thread {thread_id} exists but has no messages yet.",
                        )
                    ]

                # Format messages for display
                formatted_messages = []
                for i, msg in enumerate(messages, 1):
                    role = "unknown"
                    content = str(msg)

                    if hasattr(msg, "type"):
                        role = msg.type
                    elif hasattr(msg, "__class__"):
                        role = msg.__class__.__name__.replace("Message", "").lower()

                    if hasattr(msg, "content"):
                        content = msg.content

                    formatted_messages.append(f"{i}. [{role}] {content[:200]}{'...' if len(content) > 200 else ''}")

                # Build response
                response_text = (
                    f"Conversation history for thread {thread_id}\n"
                    f"Total messages: {len(messages)}\n"
                    f"User: {user_id}\n\n"
                    f"Messages:\n" + "\n".join(formatted_messages)
                )

                logger.info(
                    "Retrieved conversation history",
                    extra={"thread_id": thread_id, "message_count": len(messages), "user_id": user_id},
                )

                return [TextContent(type="text", text=response_text)]

            except Exception as e:
                logger.error(f"Failed to retrieve conversation: {e}", extra={"thread_id": thread_id}, exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"Error retrieving conversation {thread_id}: {str(e)}. "
                        "This may indicate a checkpointer issue or the conversation may not exist.",
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

            # Initialize all_conversations for logging
            all_conversations = []

            # Try to get conversations from OpenFGA first, fall back to conversation store
            try:
                # Get all conversations user can view from OpenFGA
                all_conversations = await self.auth.list_accessible_resources(
                    user_id=user_id, relation="viewer", resource_type="conversation"
                )

                # Filter conversations based on query
                # Normalize query and conversation names to handle spaces/underscores/hyphens
                if query:
                    normalized_query = query.lower().replace(" ", "_").replace("-", "_")
                    filtered_conversations = [
                        conv
                        for conv in all_conversations
                        if (
                            query.lower() in conv.lower()
                            or normalized_query in conv.lower().replace(" ", "_").replace("-", "_")
                        )
                    ]
                else:
                    filtered_conversations = all_conversations

            except Exception:
                # Fall back to conversation store
                logger.info("Using conversation store for search (OpenFGA unavailable or returning mock data)")

                try:
                    from mcp_server_langgraph.core.storage.conversation_store import get_conversation_store

                    store = get_conversation_store()
                    metadata_list = await store.search_conversations(user_id=user_id, query=query, limit=limit)

                    # Convert metadata to conversation IDs
                    filtered_conversations = [f"conversation:{m.thread_id}" for m in metadata_list]

                except Exception as e:
                    logger.warning(f"Conversation store also unavailable: {e}")
                    # Ultimate fallback: empty list
                    filtered_conversations = []

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

    async def _handle_search_tools(self, arguments: dict[str, Any], span: Any) -> list[TextContent]:
        """
        Handle search_tools invocation for progressive tool discovery.

        Implements Anthropic best practice for token-efficient tool discovery.
        """
        with tracer.start_as_current_span("tools.search"):
            from mcp_server_langgraph.tools.tool_discovery import search_tools

            # Extract arguments
            query = arguments.get("query")
            category = arguments.get("category")
            detail_level = arguments.get("detail_level", "minimal")

            logger.info(
                "Searching tools",
                extra={"query": query, "category": category, "detail_level": detail_level},
            )

            # Execute search_tools
            result = search_tools.invoke(
                {
                    "query": query,
                    "category": category,
                    "detail_level": detail_level,
                }
            )

            span.set_attribute("tools.query", query or "")
            span.set_attribute("tools.category", category or "")
            span.set_attribute("tools.detail_level", detail_level)

            return [TextContent(type="text", text=result)]

    async def _handle_execute_python(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
        """
        Handle execute_python invocation for secure code execution.

        Implements sandboxed Python execution with validation and resource limits.
        """
        with tracer.start_as_current_span("code.execute"):
            from mcp_server_langgraph.tools.code_execution_tools import execute_python

            # Extract arguments
            code = arguments.get("code", "")
            timeout = arguments.get("timeout")

            logger.info(
                "Executing Python code",
                extra={
                    "user_id": user_id,
                    "code_length": len(code),
                    "timeout": timeout,
                },
            )

            # Execute code
            start_time = time.time()
            result = execute_python.invoke({"code": code, "timeout": timeout})
            execution_time = time.time() - start_time

            span.set_attribute("code.length", len(code))
            span.set_attribute("code.execution_time", execution_time)
            span.set_attribute("code.success", "success" in result.lower())

            metrics.code_executions.add(1, {"user_id": user_id, "success": "success" in result.lower()})

            return [TextContent(type="text", text=result)]

    async def run(self) -> None:
        """Run the MCP server"""
        logger.info("Starting MCP Agent Server")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())


async def main() -> None:
    """Main entry point"""
    # Initialize observability system before creating server
    from mcp_server_langgraph.core.config import settings
    from mcp_server_langgraph.observability.telemetry import init_observability

    # Initialize with settings and enable file logging if configured
    init_observability(settings=settings, enable_file_logging=getattr(settings, "enable_file_logging", False))

    server = MCPAgentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
