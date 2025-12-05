"""
Unit Tests for MCP StdIO Server

Tests the MCPAgentServer implementation including initialization, authentication,
authorization, and tool handlers for the stdio-based MCP server.

Target coverage: 85%+ on src/mcp_server_langgraph/mcp/server_stdio.py
"""

import gc
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from mcp.types import TextContent

from tests.conftest import get_user_id
from tests.helpers.async_mock_helpers import configured_async_mock

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_settings():
    """Mock settings with all required fields"""
    settings = MagicMock()
    settings.jwt_secret_key = "test-secret-key"
    settings.environment = "development"
    settings.openfga_store_id = "test-store-id"
    settings.openfga_model_id = "test-model-id"
    settings.openfga_api_url = "http://localhost:8080"
    settings.auth_provider = "in_memory"
    return settings


@pytest.fixture
def mock_openfga_client():
    """Mock OpenFGA client for authorization tests"""
    client = configured_async_mock(return_value=None)
    client.check.return_value = {"allowed": True}
    client.list_objects.return_value = {"objects": ["tool:agent_chat"]}
    return client


@pytest.fixture
def mock_auth_middleware():
    """Mock authentication middleware"""
    auth = configured_async_mock(return_value=None)
    verification_result = MagicMock()
    verification_result.valid = True
    verification_result.payload = {"sub": get_user_id("alice"), "exp": 9999999999}
    verification_result.error = None
    auth.verify_token.return_value = verification_result
    auth.authorize.return_value = True
    return auth


@pytest.fixture
def mock_tracer():
    """Mock OpenTelemetry tracer"""
    tracer = MagicMock()
    span = MagicMock()
    span.get_span_context.return_value = MagicMock(trace_id=123456)
    span.set_attribute = MagicMock()
    span.record_exception = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span
    return (tracer, span)


@pytest.fixture
def mock_agent_graph():
    """Mock LangGraph agent graph"""
    graph = configured_async_mock(return_value=None)
    checkpointer = configured_async_mock(return_value=None)
    graph.checkpointer = checkpointer
    state_snapshot = MagicMock()
    state_snapshot.values = {"messages": []}
    graph.aget_state.return_value = state_snapshot
    graph.ainvoke.return_value = {
        "messages": [HumanMessage(content="Hello"), AIMessage(content="Hi there! How can I help you today?")],
        "next_action": "",
        "user_id": get_user_id("alice"),
    }
    return graph


@pytest.mark.mcp
@pytest.mark.xdist_group(name="unit_mcp_stdio_server_tests")
class TestMCPAgentServerInitialization:
    """Tests for MCPAgentServer.__init__"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    def test_init_success_with_openfga(self, mock_create_auth, mock_settings_patch, mock_settings, mock_auth_middleware):
        """Test successful initialization with OpenFGA client"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = mock_settings.openfga_store_id
        mock_settings_patch.openfga_model_id = mock_settings.openfga_model_id
        mock_settings_patch.openfga_api_url = mock_settings.openfga_api_url
        mock_settings_patch.auth_provider = mock_settings.auth_provider
        mock_create_auth.return_value = mock_auth_middleware
        with patch("mcp_server_langgraph.mcp.server_stdio.OpenFGAClient"):
            server = MCPAgentServer()
            assert server.server is not None
            assert server.auth == mock_auth_middleware
            mock_create_auth.assert_called_once()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.OpenFGAClient")
    def test_init_fails_without_jwt_secret_inmemory(self, mock_openfga_class, mock_settings_patch):
        """Test initialization fails without JWT secret for in-memory auth provider"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = ""
        mock_settings_patch.environment = "development"
        mock_settings_patch.openfga_store_id = "test-store"
        mock_settings_patch.openfga_model_id = "test-model"
        mock_settings_patch.openfga_api_url = "http://localhost:8080"
        mock_settings_patch.auth_provider = "inmemory"
        mock_openfga_class.return_value = configured_async_mock(return_value=None)
        with pytest.raises(ValueError, match="JWT secret key not configured for in-memory auth provider"):
            MCPAgentServer()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.OpenFGAClient")
    def test_init_succeeds_without_jwt_secret_keycloak(self, mock_openfga_class, mock_settings_patch):
        """Test initialization succeeds without JWT secret when using Keycloak (uses RS256)"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = ""
        mock_settings_patch.environment = "development"
        mock_settings_patch.openfga_store_id = "test-store"
        mock_settings_patch.openfga_model_id = "test-model"
        mock_settings_patch.openfga_api_url = "http://localhost:8080"
        mock_settings_patch.auth_provider = "keycloak"
        mock_openfga_class.return_value = configured_async_mock(return_value=None)
        try:
            server = MCPAgentServer()
            assert server is not None
        except ValueError as e:
            if "JWT secret key" in str(e):
                pytest.fail(f"Should not require JWT_SECRET_KEY for Keycloak auth: {e}")

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    def test_init_fails_production_without_openfga(self, mock_settings_patch):
        """Test initialization fails in production without OpenFGA (fail-closed)"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = "test-secret"
        mock_settings_patch.environment = "production"
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.openfga_api_url = "http://localhost:8080"
        mock_settings_patch.auth_provider = "keycloak"
        with pytest.raises(ValueError, match="OpenFGA authorization is required in production"):
            MCPAgentServer()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.logger")
    def test_init_warns_without_openfga_in_dev(self, mock_logger, mock_create_auth, mock_settings_patch):
        """Test initialization warns but succeeds without OpenFGA in development"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = "test-secret"
        mock_settings_patch.environment = "development"
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_create_auth.return_value = configured_async_mock(return_value=None)
        server = MCPAgentServer()
        assert server is not None
        assert server.openfga is None
        mock_logger.warning.assert_called_with("OpenFGA not configured, authorization will use fallback mode")


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="unit_mcp_stdio_server_tests")
class TestListTools:
    """Tests for list_tools_public()"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    async def test_list_tools_returns_all_tools(self, mock_create_auth, mock_settings_patch, mock_settings):
        """Test that list_tools_public returns core tools plus optional tools"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_settings_patch.enable_code_execution = getattr(mock_settings, "enable_code_execution", False)
        mock_create_auth.return_value = configured_async_mock(return_value=None)
        server = MCPAgentServer()
        tools = await server.list_tools_public()
        assert len(tools) >= 4, f"Expected at least 4 tools, got {len(tools)}: {[t.name for t in tools]}"
        tool_names = [tool.name for tool in tools]
        assert "agent_chat" in tool_names
        assert "conversation_get" in tool_names
        assert "conversation_search" in tool_names
        assert "search_tools" in tool_names
        agent_chat_tool = next(t for t in tools if t.name == "agent_chat")
        assert "inputSchema" in agent_chat_tool.model_dump()
        assert "message" in str(agent_chat_tool.inputSchema)
        assert "token" in str(agent_chat_tool.inputSchema)
        assert "user_id" in str(agent_chat_tool.inputSchema)


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.auth
@pytest.mark.xdist_group(name="unit_mcp_stdio_server_tests")
class TestToolAuthentication:
    """Tests for JWT authentication in call_tool handler"""

    @pytest.fixture(autouse=True)
    def setup_auth(self, disable_auth_skip):
        """
        Use monkeypatch-based fixture for automatic MCP_SKIP_AUTH cleanup.

        The disable_auth_skip fixture sets MCP_SKIP_AUTH=false and automatically
        cleans up after the test, preventing environment pollution in xdist workers.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
    @patch("mcp_server_langgraph.mcp.server_stdio.metrics")
    async def test_call_tool_missing_token(
        self, mock_metrics, mock_tracer_module, mock_create_auth, mock_settings_patch, mock_settings, mock_tracer
    ):
        """Test tool call fails without authentication token"""
        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_auth = configured_async_mock(return_value=None)
        mock_create_auth.return_value = mock_auth
        tracer, span = mock_tracer
        mock_tracer_module.start_as_current_span.return_value.__enter__.return_value = span
        mock_metrics.tool_calls = MagicMock()
        mock_metrics.tool_calls.add = MagicMock()
        mock_metrics.auth_failures = MagicMock()
        mock_metrics.auth_failures.add = MagicMock()
        arguments = {"message": "Hello", "user_id": "alice"}
        with pytest.raises(PermissionError, match="Authentication token required"):
            token = arguments.get("token")
            if not token:
                raise PermissionError("Authentication token required. Provide 'token' parameter with a valid JWT.")

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
    @patch("mcp_server_langgraph.mcp.server_stdio.metrics")
    async def test_call_tool_invalid_token(
        self, mock_metrics, mock_tracer_module, mock_create_auth, mock_settings_patch, mock_settings, mock_tracer
    ):
        """Test tool call fails with invalid JWT token"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_auth = configured_async_mock(return_value=None)
        verification_result = MagicMock()
        verification_result.valid = False
        verification_result.error = "Invalid signature"
        mock_auth.verify_token.return_value = verification_result
        mock_create_auth.return_value = mock_auth
        tracer, span = mock_tracer
        mock_tracer_module.start_as_current_span.return_value.__enter__.return_value = span
        mock_metrics.auth_failures = MagicMock()
        mock_metrics.auth_failures.add = MagicMock()
        server = MCPAgentServer()
        token = "invalid_token"
        result = await server.auth.verify_token(token)
        assert result.valid is False
        assert result.error == "Invalid signature"


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.auth
@pytest.mark.xdist_group(name="unit_mcp_stdio_server_tests")
class TestToolAuthorization:
    """Tests for OpenFGA authorization in call_tool handler"""

    @pytest.fixture(autouse=True)
    def setup_auth(self, disable_auth_skip):
        """
        Use monkeypatch-based fixture for automatic MCP_SKIP_AUTH cleanup.

        The disable_auth_skip fixture sets MCP_SKIP_AUTH=false and automatically
        cleans up after the test, preventing environment pollution in xdist workers.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    async def test_authorization_check_for_tool(self, mock_create_auth, mock_settings_patch, mock_settings):
        """Test OpenFGA authorization check for tool execution"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_auth = configured_async_mock(return_value=None)
        mock_auth.authorize.return_value = True
        mock_create_auth.return_value = mock_auth
        server = MCPAgentServer()
        authorized = await server.auth.authorize(user_id=get_user_id("alice"), relation="executor", resource="tool:agent_chat")
        assert authorized is True
        mock_auth.authorize.assert_called_once_with(
            user_id=get_user_id("alice"), relation="executor", resource="tool:agent_chat"
        )

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    async def test_authorization_denied(self, mock_create_auth, mock_settings_patch, mock_settings):
        """Test authorization denial prevents tool execution"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_auth = configured_async_mock(return_value=None)
        mock_auth.authorize.return_value = False
        mock_create_auth.return_value = mock_auth
        server = MCPAgentServer()
        authorized = await server.auth.authorize(user_id=get_user_id("bob"), relation="executor", resource="tool:agent_chat")
        assert authorized is False


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="unit_mcp_stdio_server_tests")
class TestHandleChat:
    """Tests for _handle_chat() method"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
    @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
    @patch("mcp_server_langgraph.mcp.server_stdio.format_response")
    async def test_handle_chat_new_conversation(
        self,
        mock_format_response,
        mock_tracer_module,
        mock_get_graph,
        mock_create_auth,
        mock_settings_patch,
        mock_settings,
        mock_auth_middleware,
        mock_agent_graph,
        mock_tracer,
    ):
        """Test chat handler creates new conversation successfully"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_create_auth.return_value = mock_auth_middleware
        mock_get_graph.return_value = mock_agent_graph
        tracer, span = mock_tracer
        mock_tracer_module.start_as_current_span.return_value.__enter__.return_value = span
        mock_format_response.return_value = "Formatted response"
        mock_agent_graph.aget_state.return_value = None
        server = MCPAgentServer()
        arguments = {
            "message": "Hello, how are you?",
            "token": "valid_jwt_token",
            "user_id": get_user_id("alice"),
            "thread_id": "conv_123",
            "response_format": "concise",
        }
        result = await server._handle_chat(arguments, span, get_user_id("alice"))
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].text == "Formatted response"
        mock_agent_graph.ainvoke.assert_called_once()
        mock_format_response.assert_called_once()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
    @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
    async def test_handle_chat_existing_conversation_authorized(
        self,
        mock_tracer_module,
        mock_get_graph,
        mock_create_auth,
        mock_settings_patch,
        mock_settings,
        mock_auth_middleware,
        mock_agent_graph,
        mock_tracer,
    ):
        """Test chat handler with existing conversation checks editor permission"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_auth_middleware.authorize.return_value = True
        mock_create_auth.return_value = mock_auth_middleware
        mock_get_graph.return_value = mock_agent_graph
        tracer, span = mock_tracer
        mock_tracer_module.start_as_current_span.return_value.__enter__.return_value = span
        state_snapshot = MagicMock()
        state_snapshot.values = {"messages": [HumanMessage(content="Previous message")]}
        mock_agent_graph.aget_state.return_value = state_snapshot
        server = MCPAgentServer()
        arguments = {
            "message": "Follow-up question",
            "token": "valid_jwt_token",
            "user_id": get_user_id("alice"),
            "thread_id": "existing_conv",
            "response_format": "detailed",
        }
        with patch("mcp_server_langgraph.mcp.server_stdio.format_response", return_value="Response"):
            result = await server._handle_chat(arguments, span, get_user_id("alice"))
            assert isinstance(result, list)
            mock_auth_middleware.authorize.assert_called_with(
                user_id=get_user_id("alice"), relation="editor", resource="conversation:existing_conv"
            )

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
    @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
    async def test_handle_chat_existing_conversation_unauthorized(
        self,
        mock_tracer_module,
        mock_get_graph,
        mock_create_auth,
        mock_settings_patch,
        mock_settings,
        mock_auth_middleware,
        mock_agent_graph,
        mock_tracer,
    ):
        """Test chat handler denies access to unauthorized existing conversation"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_auth_middleware.authorize.return_value = False
        mock_create_auth.return_value = mock_auth_middleware
        mock_get_graph.return_value = mock_agent_graph
        tracer, span = mock_tracer
        mock_tracer_module.start_as_current_span.return_value.__enter__.return_value = span
        state_snapshot = MagicMock()
        state_snapshot.values = {"messages": []}
        mock_agent_graph.aget_state.return_value = state_snapshot
        server = MCPAgentServer()
        arguments = {
            "message": "Trying to access",
            "token": "valid_jwt_token",
            "user_id": get_user_id("eve"),
            "thread_id": "alice_private_conv",
            "response_format": "concise",
        }
        with pytest.raises(PermissionError, match="Not authorized to edit conversation"):
            await server._handle_chat(arguments, span, get_user_id("eve"))

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
    async def test_handle_chat_invalid_input(
        self, mock_tracer_module, mock_create_auth, mock_settings_patch, mock_settings, mock_tracer
    ):
        """Test chat handler validates input with Pydantic schema"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_create_auth.return_value = configured_async_mock(return_value=None)
        tracer, span = mock_tracer
        mock_tracer_module.start_as_current_span.return_value.__enter__.return_value = span
        server = MCPAgentServer()
        arguments = {"token": "valid_jwt_token"}
        with pytest.raises(ValueError, match="Invalid chat input"):
            await server._handle_chat(arguments, span, get_user_id("alice"))


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="unit_mcp_stdio_server_tests")
class TestResponseFormatting:
    """Tests for response format control (concise vs detailed)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
    @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
    @patch("mcp_server_langgraph.mcp.server_stdio.format_response")
    async def test_concise_format_applied(
        self,
        mock_format_response,
        mock_tracer_module,
        mock_get_graph,
        mock_create_auth,
        mock_settings_patch,
        mock_settings,
        mock_agent_graph,
        mock_tracer,
    ):
        """Test concise response format is applied"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_create_auth.return_value = configured_async_mock(return_value=None)
        mock_get_graph.return_value = mock_agent_graph
        tracer, span = mock_tracer
        mock_tracer_module.start_as_current_span.return_value.__enter__.return_value = span
        mock_format_response.return_value = "Concise response"
        server = MCPAgentServer()
        arguments = {
            "message": "Test message",
            "token": "token",
            "user_id": get_user_id("alice"),
            "response_format": "concise",
        }
        await server._handle_chat(arguments, span, get_user_id("alice"))
        mock_format_response.assert_called_once()
        args, kwargs = mock_format_response.call_args
        assert kwargs.get("format_type") == "concise" or args[1] == "concise"


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.xdist_group(name="unit_mcp_stdio_server_tests")
class TestErrorHandling:
    """Tests for error handling in MCP server"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @patch("mcp_server_langgraph.mcp.server_stdio.settings")
    @patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
    @patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
    @patch("mcp_server_langgraph.mcp.server_stdio.tracer")
    @patch("mcp_server_langgraph.mcp.server_stdio.metrics")
    async def test_handle_chat_agent_error(
        self,
        mock_metrics,
        mock_tracer_module,
        mock_get_graph,
        mock_create_auth,
        mock_settings_patch,
        mock_settings,
        mock_agent_graph,
        mock_tracer,
    ):
        """Test error handling when agent execution fails"""
        from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer

        mock_settings_patch.jwt_secret_key = mock_settings.jwt_secret_key
        mock_settings_patch.environment = mock_settings.environment
        mock_settings_patch.openfga_store_id = ""
        mock_settings_patch.openfga_model_id = ""
        mock_settings_patch.auth_provider = "in_memory"
        mock_create_auth.return_value = configured_async_mock(return_value=None)
        mock_agent_graph.ainvoke.side_effect = Exception("LLM API error")
        mock_get_graph.return_value = mock_agent_graph
        tracer, span = mock_tracer
        mock_tracer_module.start_as_current_span.return_value.__enter__.return_value = span
        mock_metrics.failed_calls = MagicMock()
        mock_metrics.failed_calls.add = MagicMock()
        server = MCPAgentServer()
        arguments = {"message": "Test", "token": "token", "user_id": get_user_id("alice")}
        with pytest.raises(Exception, match="LLM API error"):
            await server._handle_chat(arguments, span, get_user_id("alice"))
        span.record_exception.assert_called_once()
