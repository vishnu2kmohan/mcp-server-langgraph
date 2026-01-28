"""
MCP Server implementation for LangGraph agent with OpenFGA and Infisical

Implements Anthropic's best practices for writing tools for agents:
- Token-efficient responses with truncation
- Search-focused tools instead of list-all
- Response format control (concise vs detailed)
- Namespaced tools for clarity
- High-signal information in responses

Phase 2.1 SRP decomposition: Handler logic extracted to mcp/handlers/ modules.
"""

import asyncio
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl

from mcp_server_langgraph.auth.factory import create_auth_middleware
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.core.agent import cleanup_checkpointer, create_agent_graph
from mcp_server_langgraph.core.config import Settings, settings
from mcp_server_langgraph.core.dependencies import get_openfga_client
from mcp_server_langgraph.mcp.handlers import ChatToolHandler, ConversationToolHandler, ExecutionToolHandler
from mcp_server_langgraph.mcp.models import ChatInput, SearchConversationsInput
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class MCPAgentServer:
    """MCP Server exposing LangGraph agent with OpenFGA authorization"""

    def __init__(
        self,
        openfga_client: OpenFGAClient | None = None,
        auth: AuthMiddleware | None = None,
        settings: Settings | None = None,
        agent_graph: Any | None = None,
    ) -> None:
        """
        Initialize MCP Agent Server with optional dependency injection.

        Args:
            openfga_client: Optional OpenFGA client for authorization.
                           If None, creates one from settings.
            auth: Optional pre-configured AuthMiddleware instance.
                  If provided, this takes precedence over creating auth from settings.
                  This enables dependency injection for testing and custom configurations.
            settings: Optional Settings instance for runtime configuration.
                     If provided, enables dynamic feature toggling (e.g., code execution).
                     If None, uses global settings. This allows tests to inject custom
                     configuration without module reloading.
            agent_graph: Optional pre-created agent graph instance.
                        If provided, uses this graph instead of creating one.
                        This enables dependency injection for testing.
                        If None, creates a new graph using create_agent_graph().

        Example:
            # Default creation (production):
            server = MCPAgentServer()

            # Custom auth injection (testing):
            custom_auth = AuthMiddleware(user_provider=custom_provider, ...)
            server = MCPAgentServer(auth=custom_auth)

            # Custom settings injection (testing):
            test_settings = Settings(enable_code_execution=True)
            server = MCPAgentServer(settings=test_settings)

            # Custom agent graph injection (testing):
            mock_graph = create_mock_agent_graph()
            server = MCPAgentServer(agent_graph=mock_graph)

        OpenAI Codex Finding (2025-11-16):
        ===================================
        Added `auth` parameter for constructor-based dependency injection.
        This allows tests to inject pre-configured AuthMiddleware with registered users,
        fixing the "user not found" failures in integration tests.

        Added `settings` parameter (2025-11-16):
        ========================================
        Enables runtime configuration without module reloading. Fixes code execution
        tool visibility issues in integration tests where ENABLE_CODE_EXECUTION env
        var changes didn't take effect due to module-level settings caching.

        Added `agent_graph` parameter (2025-12-18):
        ============================================
        Migrated from deprecated get_agent_graph() singleton to create_agent_graph() DI.
        This eliminates deprecation warnings and enables proper instance-level lifecycle.
        """
        # Store settings for runtime configuration
        # NOTE: When settings=None, we must reference the module-level 'settings'
        # imported at the top of this file. This allows tests to mock settings via
        # @patch("mcp_server_langgraph.mcp.server_stdio.settings", ...)
        # Using sys.modules[__name__] to avoid self-import (CodeQL py/import-own-module)
        self.settings = settings if settings is not None else sys.modules[__name__].settings

        self.server = Server("langgraph-agent")

        # Initialize agent graph (DI or create new)
        if agent_graph is not None:
            self.agent_graph = agent_graph
        else:
            self.agent_graph = create_agent_graph(settings=self.settings)

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
            if self.settings.auth_provider == "inmemory" and not self.settings.jwt_secret_key:
                msg = (
                    "CRITICAL: JWT secret key not configured for in-memory auth provider. "
                    "Set JWT_SECRET_KEY environment variable or configure via Infisical. "
                    "The in-memory auth provider requires a secure secret key for HS256 token signing."
                )
                raise ValueError(msg)

            # SECURITY: Fail-closed pattern - require OpenFGA in production
            if self.settings.environment == "production" and self.openfga is None:
                msg = (
                    "CRITICAL: OpenFGA authorization is required in production mode. "
                    "Configure OPENFGA_STORE_ID and OPENFGA_MODEL_ID environment variables, "
                    "or set ENVIRONMENT=development for local testing. "
                    "Fallback authorization is not secure enough for production use."
                )
                raise ValueError(msg)

            self.auth = create_auth_middleware(self.settings, openfga_client=self.openfga)

        # Initialize tool handlers (Phase 2.1 SRP decomposition)
        self._chat_handler = ChatToolHandler(auth=self.auth, agent_graph=self.agent_graph)
        self._conversation_handler = ConversationToolHandler(auth=self.auth, agent_graph=self.agent_graph)
        self._execution_handler = ExecutionToolHandler(auth=self.auth, agent_graph=self.agent_graph)

        self._setup_handlers()

    def _create_openfga_client(self, settings_override: Settings | None = None) -> OpenFGAClient | None:
        """Create OpenFGA client from centralized dependency.

        Uses the centralized get_openfga_client from core.dependencies which:
        - Supports store_id OR store_name (dynamic lookup)
        - Supports model_id (optional, fetches latest if not set)
        - Handles OIDC authentication automatically

        Args:
            settings_override: Ignored (kept for API compatibility).
                              The centralized dependency uses global settings.

        Returns:
            OpenFGAClient instance or None if not configured
        """
        client = get_openfga_client()
        if client:
            logger.info("Initializing OpenFGA client")
        else:
            logger.warning("OpenFGA not configured, authorization will use fallback mode")
        return client

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
        # Use runtime settings evaluation (not module-level cached value)
        if self.settings.enable_code_execution:
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
                msg = (
                    "Authentication token required. Provide 'token' parameter with a valid JWT. "
                    "Obtain token via /auth/login endpoint or external authentication service."
                )
                raise PermissionError(msg)

            # Verify JWT token
            token_verification = await self.auth.verify_token(token)

            if not token_verification.valid:
                logger.warning("Token verification failed", extra={"error": token_verification.error})
                metrics.auth_failures.add(1)
                msg = f"Invalid authentication token: {token_verification.error or 'token verification failed'}"
                raise PermissionError(msg)

            # Extract user_id from validated token payload
            if not token_verification.payload or "sub" not in token_verification.payload:
                logger.error("Token payload missing 'sub' claim")
                metrics.auth_failures.add(1)
                msg = "Invalid token: missing user identifier"
                raise PermissionError(msg)

            # Extract username with defensive fallback
            # Priority: preferred_username > username claim > sub parsing
            username = token_verification.payload.get("preferred_username")
            if not username:
                # Try 'username' claim (alternative standard claim)
                username = token_verification.payload.get("username")
            if not username:
                # Fallback: extract from sub if it's in "user:username" format
                sub = token_verification.payload.get("sub", "")
                if sub.startswith("user:"):
                    username = sub.split(":", 1)[1]
                elif sub and ":" not in sub:
                    # Log warning for UUID-style subs (may cause issues)
                    logger.warning(
                        f"Using sub as username fallback (may be UUID): {sub[:8]}...",
                        extra={"sub_prefix": sub[:8]},
                    )
                    username = sub
                else:
                    msg = "Invalid token: cannot extract username from claims"
                    raise PermissionError(msg)

            # Normalize user_id to "user:username" format for OpenFGA compatibility
            user_id = f"user:{username}" if not username.startswith("user:") else username
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
                msg = f"Not authorized to execute {resource}"
                raise PermissionError(msg)

            logger.info("Authorization granted", extra={"user_id": user_id, "resource": resource})

            # Route to appropriate handler (with backward compatibility)
            # Phase 2.1: Delegating to decomposed handlers instead of inline methods
            if name == "agent_chat" or name == "chat":  # Support old name for compatibility
                return await self._chat_handler.handle(arguments, span, user_id)
            elif name == "conversation_get" or name == "get_conversation":
                return await self._conversation_handler.handle_get_conversation(arguments, span, user_id)
            elif name == "conversation_search" or name == "list_conversations":
                return await self._conversation_handler.handle_search_conversations(arguments, span, user_id)
            elif name == "search_tools":
                return await self._execution_handler.handle_search_tools(arguments, span)
            elif name == "execute_python":
                return await self._execution_handler.handle_execute_python(arguments, span, user_id)
            else:
                msg = f"Unknown tool: {name}"
                raise ValueError(msg)

    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers"""

        @self.server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
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

        @self.server.call_tool()  # type: ignore[untyped-decorator]
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls with OpenFGA authorization and tracing"""
            return await self.call_tool_public(name, arguments)

        @self.server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
        async def list_resources() -> list[Resource]:
            """List available resources"""
            with tracer.start_as_current_span("mcp.list_resources"):
                return [Resource(uri=AnyUrl("agent://config"), name="Agent Configuration", mimeType="application/json")]

    def cleanup(self) -> None:
        """
        Cleanup server resources.

        Releases checkpointer resources (Redis connections, etc.) held by the agent graph.
        Call this when shutting down the server to prevent resource leaks.

        Added 2025-12-18: Part of migration from get_agent_graph() singleton to DI pattern.
        """
        if hasattr(self.agent_graph, "checkpointer") and self.agent_graph.checkpointer is not None:
            cleanup_checkpointer(self.agent_graph.checkpointer)
            logger.debug("Agent graph checkpointer cleaned up")

    # NOTE: _handle_* methods delegated to mcp/handlers/ modules in Phase 2.1 SRP decomposition.
    # These wrapper methods are retained for test backward compatibility.
    # - ChatToolHandler: handles agent_chat
    # - ConversationToolHandler: handles conversation_get, conversation_search
    # - ExecutionToolHandler: handles execute_python, search_tools

    async def _handle_chat(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
        """Delegate to ChatToolHandler (wrapper for test backward compatibility)."""
        return await self._chat_handler.handle(arguments, span, user_id)

    async def _handle_get_conversation(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
        """Delegate to ConversationToolHandler (wrapper for test backward compatibility)."""
        return await self._conversation_handler.handle_get_conversation(arguments, span, user_id)

    async def _handle_search_conversations(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
        """Delegate to ConversationToolHandler (wrapper for test backward compatibility)."""
        return await self._conversation_handler.handle_search_conversations(arguments, span, user_id)

    async def _handle_search_tools(self, arguments: dict[str, Any], span: Any) -> list[TextContent]:
        """Delegate to ExecutionToolHandler (wrapper for test backward compatibility)."""
        return await self._execution_handler.handle_search_tools(arguments, span)

    async def _handle_execute_python(self, arguments: dict[str, Any], span: Any, user_id: str) -> list[TextContent]:
        """Delegate to ExecutionToolHandler (wrapper for test backward compatibility)."""
        return await self._execution_handler.handle_execute_python(arguments, span, user_id)

    async def run(self) -> None:
        """Run the MCP server"""
        logger.info("Starting MCP Agent Server")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())


async def main() -> None:
    """Main entry point.

    v26: Full bootstrap for semantic indexing and other services.
    Canonical startup: sync_mcp_tools() THEN index_all_tools().
    """
    # Initialize observability system before creating server
    from mcp_server_langgraph.observability.telemetry import init_observability

    # Initialize with settings and enable file logging if configured
    init_observability(settings=settings, enable_file_logging=getattr(settings, "enable_file_logging", False))

    # Full bootstrap for semantic indexing and other services (v26)
    from mcp_server_langgraph.bootstrap import bootstrap_all
    from mcp_server_langgraph.bootstrap.semantic import index_all_tools
    from mcp_server_langgraph.tools.unified_registry import sync_mcp_tools

    state = await bootstrap_all(settings)

    try:
        # Sync MCP tools and index (canonical startup sequence)
        await sync_mcp_tools()
        logger.info("MCP tools synced to unified registry")

        await index_all_tools()
        logger.info("All tools indexed for semantic search")
    except Exception as e:
        logger.warning(f"MCP sync/index failed (non-fatal): {e}")

    try:
        server = MCPAgentServer()
        await server.run()
    finally:
        # Cleanup on shutdown
        await state.cleanup()
        logger.info("MCP server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
