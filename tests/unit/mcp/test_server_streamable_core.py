"""
Unit tests for server_streamable.py core functionality.

Tests the MCPAgentStreamableServer class, authentication, and tool handling.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

pytestmark = [pytest.mark.unit, pytest.mark.mcp]


def _mock_settings():
    """Create mock settings for testing."""
    mock = MagicMock()
    mock.jwt_secret_key = "test-secret-key-for-unit-tests"
    mock.environment = "development"
    mock.openfga_store_id = None
    mock.openfga_model_id = None
    mock.openfga_api_url = "http://localhost:8080"
    mock.jwt_expiration_seconds = 3600
    mock.auth_provider = "inmemory"
    mock.service_version = "1.0.0"
    mock.enable_code_execution = False
    return mock


@pytest.mark.xdist_group(name="server_streamable")
class TestMCPAgentStreamableServerInit:
    """Test MCPAgentStreamableServer initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_init_requires_jwt_secret(self):
        """Test that server initialization fails without JWT secret."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = None
            mock_settings.environment = "development"
            # Provide valid values for other settings that get checked
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.auth_provider = "inmemory"

            from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

            with pytest.raises(ValueError, match="JWT secret key not configured"):
                MCPAgentStreamableServer()

    @pytest.mark.unit
    def test_init_requires_openfga_in_production(self):
        """Test that production requires OpenFGA authorization."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "production"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None

            from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

            with pytest.raises(ValueError, match="OpenFGA authorization is required in production"):
                MCPAgentStreamableServer()

    @pytest.mark.unit
    def test_init_creates_openfga_client_when_configured(self):
        """Test that OpenFGA client is created when store/model IDs are set."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = "test-store"
            mock_settings.openfga_model_id = "test-model"
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.auth_provider = "inmemory"

            with patch("mcp_server_langgraph.mcp.server_streamable.OpenFGAClient") as mock_openfga:
                with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware"):
                    from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                    server = MCPAgentStreamableServer()
                    mock_openfga.assert_called_once_with(
                        api_url="http://localhost:8080",
                        store_id="test-store",
                        model_id="test-model",
                    )
                    assert server.openfga is not None


@pytest.mark.xdist_group(name="server_streamable")
class TestMCPAgentStreamableServerListTools:
    """Test list_tools_public method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_tools_returns_core_tools(self):
        """Test that list_tools returns core MCP tools."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.auth_provider = "inmemory"
            mock_settings.enable_code_execution = False

            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware"):
                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer()
                tools = await server.list_tools_public()

                tool_names = [t.name for t in tools]

                # Core tools should always be present
                assert "agent_chat" in tool_names
                assert "conversation_get" in tool_names
                assert "conversation_search" in tool_names
                assert "search_tools" in tool_names

                # Code execution should NOT be present when disabled
                assert "execute_python" not in tool_names

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_tools_includes_code_execution_when_enabled(self):
        """Test that execute_python is included when code execution is enabled."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.auth_provider = "inmemory"
            mock_settings.enable_code_execution = True

            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware"):
                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer()
                tools = await server.list_tools_public()

                tool_names = [t.name for t in tools]
                assert "execute_python" in tool_names


@pytest.mark.xdist_group(name="server_streamable")
class TestMCPAgentStreamableServerCallTool:
    """Test call_tool_public method with authentication."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_requires_token(self):
        """Test that call_tool fails without authentication token."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.auth_provider = "inmemory"

            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware"):
                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer()

                with pytest.raises(PermissionError, match="Authentication token required"):
                    await server.call_tool_public("agent_chat", {"message": "hello"})

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_validates_token(self):
        """Test that call_tool validates the JWT token."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.auth_provider = "inmemory"

            mock_auth = MagicMock()
            mock_auth.verify_token = AsyncMock(return_value=MagicMock(valid=False, error="Invalid token"))

            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware", return_value=mock_auth):
                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer()

                with pytest.raises(PermissionError, match="Invalid authentication token"):
                    await server.call_tool_public(
                        "agent_chat",
                        {"message": "hello", "token": "invalid-token", "user_id": "alice"},
                    )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool_raises_error(self):
        """Test that calling unknown tool raises ValueError."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.auth_provider = "inmemory"

            mock_auth = MagicMock()
            mock_auth.verify_token = AsyncMock(
                return_value=MagicMock(
                    valid=True,
                    payload={"sub": "user:alice", "preferred_username": "alice"},
                    error=None,
                )
            )
            mock_auth.authorize = AsyncMock(return_value=True)

            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware", return_value=mock_auth):
                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer()

                with pytest.raises(ValueError, match="Unknown tool"):
                    await server.call_tool_public(
                        "nonexistent_tool",
                        {"token": "valid-token", "user_id": "alice"},
                    )


@pytest.mark.xdist_group(name="server_streamable")
class TestMCPAgentStreamableServerListResources:
    """Test list_resources_public method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_resources_returns_config_resource(self):
        """Test that list_resources returns agent configuration resource."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.auth_provider = "inmemory"

            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware"):
                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer()
                resources = await server.list_resources_public()

                assert len(resources) == 1
                assert resources[0].name == "Agent Configuration"
                assert "agent://config" in str(resources[0].uri)


@pytest.mark.xdist_group(name="server_streamable")
class TestChatInputValidation:
    """Test ChatInput model validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_chat_input_requires_message(self):
        """Test that ChatInput requires non-empty message."""
        from pydantic import ValidationError

        from mcp_server_langgraph.mcp.server_streamable import ChatInput

        with pytest.raises(ValidationError):
            ChatInput(message="", token="test", user_id="alice")

    @pytest.mark.unit
    def test_chat_input_limits_message_length(self):
        """Test that ChatInput enforces max message length."""
        from pydantic import ValidationError

        from mcp_server_langgraph.mcp.server_streamable import ChatInput

        with pytest.raises(ValidationError):
            ChatInput(message="x" * 10001, token="test", user_id="alice")

    @pytest.mark.unit
    def test_chat_input_validates_thread_id_pattern(self):
        """Test that thread_id must match safe pattern."""
        from pydantic import ValidationError

        from mcp_server_langgraph.mcp.server_streamable import ChatInput

        # Valid thread_id
        input_valid = ChatInput(
            message="hello",
            token="test",
            user_id="alice",
            thread_id="conv_123-abc",
        )
        assert input_valid.thread_id == "conv_123-abc"

        # Invalid thread_id (SQL injection attempt)
        with pytest.raises(ValidationError):
            ChatInput(
                message="hello",
                token="test",
                user_id="alice",
                thread_id="'; DROP TABLE users; --",
            )

    @pytest.mark.unit
    def test_chat_input_effective_user_id(self):
        """Test effective_user_id property handles deprecated username."""
        from mcp_server_langgraph.mcp.server_streamable import ChatInput

        # user_id takes priority
        input1 = ChatInput(
            message="hello",
            token="test",
            user_id="alice",
            username="bob",  # deprecated
        )
        assert input1.effective_user_id == "alice"


@pytest.mark.xdist_group(name="server_streamable")
class TestSearchConversationsInput:
    """Test SearchConversationsInput model validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_search_input_limits_query_length(self):
        """Test that search query has max length."""
        from pydantic import ValidationError

        from mcp_server_langgraph.mcp.server_streamable import SearchConversationsInput

        with pytest.raises(ValidationError):
            SearchConversationsInput(
                query="x" * 501,
                token="test",
                user_id="alice",
            )

    @pytest.mark.unit
    def test_search_input_limits_result_count(self):
        """Test that limit parameter is bounded."""
        from pydantic import ValidationError

        from mcp_server_langgraph.mcp.server_streamable import SearchConversationsInput

        # Valid limit
        valid_input = SearchConversationsInput(
            query="test",
            token="test",
            user_id="alice",
            limit=25,
        )
        assert valid_input.limit == 25

        # Invalid limit (too high)
        with pytest.raises(ValidationError):
            SearchConversationsInput(
                query="test",
                token="test",
                user_id="alice",
                limit=100,
            )


@pytest.mark.xdist_group(name="server_streamable")
class TestGetMcpServer:
    """Test get_mcp_server lazy singleton."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_mcp_server_requires_observability(self):
        """Test that get_mcp_server fails if observability not initialized."""
        # Patch the is_initialized function in the telemetry module where it's imported from
        with patch("mcp_server_langgraph.observability.telemetry.is_initialized", return_value=False):
            from mcp_server_langgraph.mcp.server_streamable import get_mcp_server

            with pytest.raises(RuntimeError, match="Observability must be initialized"):
                get_mcp_server()
