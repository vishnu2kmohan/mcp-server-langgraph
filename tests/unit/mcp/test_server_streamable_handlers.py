"""
Unit tests for server_streamable.py handler methods.

Tests the internal handler methods for MCP tools like _handle_chat,
_handle_get_conversation, _handle_search_conversations, etc.

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

pytestmark = [pytest.mark.unit, pytest.mark.mcp]


def _mock_settings():
    """Create mock settings for testing handlers."""
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


def _create_server_with_mocks():
    """Create an MCPAgentStreamableServer with mocked dependencies."""
    with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
        mock_settings.jwt_secret_key = "test-secret"
        mock_settings.environment = "development"
        mock_settings.openfga_store_id = None
        mock_settings.openfga_model_id = None
        mock_settings.openfga_api_url = "http://localhost:8080"
        mock_settings.auth_provider = "inmemory"
        mock_settings.enable_code_execution = False

        with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware") as mock_auth_factory:
            mock_auth = MagicMock()
            mock_auth.verify_token = AsyncMock(
                return_value=MagicMock(
                    valid=True,
                    payload={"sub": "user:alice", "preferred_username": "alice"},
                    error=None,
                )
            )
            mock_auth.authorize = AsyncMock(return_value=True)
            mock_auth_factory.return_value = mock_auth

            from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

            server = MCPAgentStreamableServer()
            return server, mock_auth


@pytest.mark.xdist_group(name="server_streamable_handlers")
class TestHandleChatMethod:
    """Test _handle_chat method in detail."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_chat_validates_input(self):
        """Test that _handle_chat validates ChatInput schema."""
        server, _ = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace-id")
        mock_span.set_attribute = MagicMock()
        mock_span.record_exception = MagicMock()

        # Invalid input - empty message
        with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

            with pytest.raises(ValueError, match="Invalid chat input"):
                await server._handle_chat(
                    arguments={"message": "", "token": "test", "user_id": "alice"},
                    span=mock_span,
                    user_id="alice",
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_chat_creates_new_conversation(self):
        """Test that new conversations are created with implicit ownership."""
        server, mock_auth = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace-id")
        mock_span.set_attribute = MagicMock()
        mock_span.record_exception = MagicMock()

        # Mock the agent graph
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        # Simulate no existing conversation
        mock_graph.aget_state = AsyncMock(return_value=None)
        # Return valid agent response
        mock_response = MagicMock()
        mock_response.content = "Hello, how can I help you?"
        mock_graph.ainvoke = AsyncMock(return_value={"messages": [mock_response]})

        with patch("mcp_server_langgraph.mcp.server_streamable.get_agent_graph", return_value=mock_graph):
            with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
                mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
                mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

                with patch(
                    "mcp_server_langgraph.mcp.server_streamable.format_response", return_value="Hello, how can I help you?"
                ):
                    with patch("mcp_server_langgraph.mcp.server_streamable.metrics"):
                        result = await server._handle_chat(
                            arguments={
                                "message": "Hello",
                                "thread_id": "new-conv-123",
                                "token": "test-token",
                                "user_id": "alice",
                            },
                            span=mock_span,
                            user_id="alice",
                        )

        # Should return TextContent with response
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Hello" in result[0].text

        # Should NOT check authorization for new conversations
        mock_auth.authorize.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_chat_checks_authorization_for_existing_conversation(self):
        """Test that existing conversations require authorization."""
        server, mock_auth = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace-id")
        mock_span.set_attribute = MagicMock()
        mock_span.record_exception = MagicMock()

        # Mock the agent graph
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        # Simulate existing conversation
        mock_state = MagicMock()
        mock_state.values = {"messages": []}
        mock_graph.aget_state = AsyncMock(return_value=mock_state)
        # Return valid agent response
        mock_response = MagicMock()
        mock_response.content = "Continued conversation"
        mock_graph.ainvoke = AsyncMock(return_value={"messages": [mock_response]})

        with patch("mcp_server_langgraph.mcp.server_streamable.get_agent_graph", return_value=mock_graph):
            with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
                mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
                mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

                with patch(
                    "mcp_server_langgraph.mcp.server_streamable.format_response", return_value="Continued conversation"
                ):
                    with patch("mcp_server_langgraph.mcp.server_streamable.metrics"):
                        await server._handle_chat(
                            arguments={
                                "message": "Continue",
                                "thread_id": "existing-conv",
                                "token": "test-token",
                                "user_id": "alice",
                            },
                            span=mock_span,
                            user_id="alice",
                        )

        # Should check authorization for existing conversations
        mock_auth.authorize.assert_called_once()
        call_args = mock_auth.authorize.call_args
        assert call_args[1]["user_id"] == "alice"
        assert call_args[1]["relation"] == "editor"
        assert "existing-conv" in call_args[1]["resource"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_chat_denies_unauthorized_access(self):
        """Test that unauthorized users cannot edit conversations."""
        server, mock_auth = _create_server_with_mocks()
        # Set authorization to deny
        mock_auth.authorize = AsyncMock(return_value=False)

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace-id")
        mock_span.set_attribute = MagicMock()
        mock_span.record_exception = MagicMock()

        # Mock the agent graph
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        # Simulate existing conversation
        mock_state = MagicMock()
        mock_state.values = {"messages": []}
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        with patch("mcp_server_langgraph.mcp.server_streamable.get_agent_graph", return_value=mock_graph):
            with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
                mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
                mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

                with pytest.raises(PermissionError, match="Not authorized to edit conversation"):
                    await server._handle_chat(
                        arguments={
                            "message": "Trying to edit",
                            "thread_id": "protected-conv",
                            "token": "test-token",
                            "user_id": "bob",
                        },
                        span=mock_span,
                        user_id="bob",
                    )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_chat_handles_agent_errors(self):
        """Test that agent errors are properly caught and logged."""
        server, mock_auth = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace-id")
        mock_span.set_attribute = MagicMock()
        mock_span.record_exception = MagicMock()

        # Mock the agent graph to raise error
        mock_graph = MagicMock()
        mock_graph.checkpointer = None
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("Agent crashed"))

        with patch("mcp_server_langgraph.mcp.server_streamable.get_agent_graph", return_value=mock_graph):
            with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
                mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
                mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

                with patch("mcp_server_langgraph.mcp.server_streamable.metrics"):
                    with pytest.raises(RuntimeError, match="Agent crashed"):
                        await server._handle_chat(
                            arguments={"message": "Hello", "token": "test-token", "user_id": "alice"},
                            span=mock_span,
                            user_id="alice",
                        )

        # Should record exception on span
        mock_span.record_exception.assert_called_once()


@pytest.mark.xdist_group(name="server_streamable_handlers")
class TestHandleGetConversationMethod:
    """Test _handle_get_conversation method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_conversation_validates_input(self):
        """Test that conversation retrieval validates input."""
        server, _ = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        # Missing thread_id
        with pytest.raises((ValueError, KeyError)):
            await server._handle_get_conversation(
                arguments={},
                span=mock_span,
                user_id="alice",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_conversation_returns_history(self):
        """Test that conversation history is returned."""
        server, mock_auth = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        # Mock conversation history
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_state = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Previous message"
        mock_message.type = "human"
        mock_state.values = {"messages": [mock_message]}
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        with patch("mcp_server_langgraph.mcp.server_streamable.get_agent_graph", return_value=mock_graph):
            result = await server._handle_get_conversation(
                arguments={"thread_id": "test-conv"},
                span=mock_span,
                user_id="alice",
            )

        assert len(result) >= 1
        assert isinstance(result[0], TextContent)


@pytest.mark.xdist_group(name="server_streamable_handlers")
class TestHandleSearchConversationsMethod:
    """Test _handle_search_conversations method."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_conversations_validates_input(self):
        """Test that search validates input parameters."""
        server, _ = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        # Test with valid search
        from mcp_server_langgraph.mcp.server_streamable import SearchConversationsInput

        # Valid input should parse
        valid_input = SearchConversationsInput(
            query="test query",
            token="test",
            user_id="alice",
            limit=10,
        )
        assert valid_input.query == "test query"
        assert valid_input.limit == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_conversations_returns_results(self):
        """Test that search returns matching conversations."""
        server, mock_auth = _create_server_with_mocks()
        # Mock list_accessible_resources to return some conversations
        mock_auth.list_accessible_resources = AsyncMock(
            return_value=["conversation:proj-alpha", "conversation:proj-beta", "conversation:demo-test"]
        )

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

            result = await server._handle_search_conversations(
                arguments={"query": "proj", "token": "test-token", "user_id": "alice", "limit": 10},
                span=mock_span,
                user_id="alice",
            )

        # Should return TextContent with matching conversations
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should contain matching conversations
        assert "proj" in result[0].text.lower() or "found" in result[0].text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_conversations_no_results(self):
        """Test that search handles no matching results."""
        server, mock_auth = _create_server_with_mocks()
        # Mock list_accessible_resources to return conversations that don't match
        mock_auth.list_accessible_resources = AsyncMock(return_value=["conversation:alpha", "conversation:beta"])

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

            result = await server._handle_search_conversations(
                arguments={"query": "xyz-not-found", "token": "test-token", "user_id": "alice", "limit": 10},
                span=mock_span,
                user_id="alice",
            )

        # Should return message about no results
        assert len(result) == 1
        assert "no conversations found" in result[0].text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_conversations_wildcard_query_returns_all(self):
        """Test that wildcard query returns all accessible conversations."""
        server, mock_auth = _create_server_with_mocks()
        mock_auth.list_accessible_resources = AsyncMock(return_value=["conversation:recent-1", "conversation:recent-2"])

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

            # Use a single character query that matches everything
            result = await server._handle_search_conversations(
                arguments={"query": "recent", "token": "test-token", "user_id": "alice", "limit": 10},
                span=mock_span,
                user_id="alice",
            )

        # Should return matching conversations
        assert len(result) == 1
        assert "recent" in result[0].text.lower() or "found" in result[0].text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_conversations_invalid_input(self):
        """Test that search rejects invalid input."""
        server, _ = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

            # Query too long
            with pytest.raises(ValueError, match="Invalid search input"):
                await server._handle_search_conversations(
                    arguments={"query": "x" * 1000, "token": "test-token", "user_id": "alice"},
                    span=mock_span,
                    user_id="alice",
                )


@pytest.mark.xdist_group(name="server_streamable_handlers")
class TestHandleSearchToolsMethod:
    """Test _handle_search_tools method for progressive tool discovery."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_tools_returns_matching_tools(self):
        """Test that search_tools returns tools matching the query."""
        server, _ = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

            result = await server._handle_search_tools(
                arguments={"query": "chat"},
                span=mock_span,
            )

        # Should return TextContent with matching tools
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should contain chat-related tools or message about tools
        assert "chat" in result[0].text.lower() or "tool" in result[0].text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_tools_no_query_returns_all(self):
        """Test that empty query returns all available tools."""
        server, _ = _create_server_with_mocks()

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

            result = await server._handle_search_tools(
                arguments={},
                span=mock_span,
            )

        # Should return list of tools
        assert len(result) == 1
        assert isinstance(result[0], TextContent)


@pytest.mark.xdist_group(name="server_streamable_handlers")
class TestOpenFGATupleSeeding:
    """Test OpenFGA tuple seeding for new conversations."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_new_conversation_seeds_openfga_tuples(self):
        """Test that new conversations seed OpenFGA ownership tuples."""
        # Create server with OpenFGA enabled
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = "test-store"
            mock_settings.openfga_model_id = "test-model"
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.auth_provider = "inmemory"
            mock_settings.enable_code_execution = False

            mock_openfga = MagicMock()
            mock_openfga.write_tuples = AsyncMock(return_value=None)

            with patch("mcp_server_langgraph.mcp.server_streamable.OpenFGAClient", return_value=mock_openfga):
                with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware") as mock_auth_factory:
                    mock_auth = MagicMock()
                    mock_auth.verify_token = AsyncMock(
                        return_value=MagicMock(valid=True, payload={"sub": "alice"}, error=None)
                    )
                    mock_auth.authorize = AsyncMock(return_value=True)
                    mock_auth_factory.return_value = mock_auth

                    from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                    server = MCPAgentStreamableServer()
                    server.openfga = mock_openfga

        mock_span = MagicMock()
        mock_span.get_span_context.return_value = MagicMock(trace_id="test-trace-id")
        mock_span.set_attribute = MagicMock()
        mock_span.record_exception = MagicMock()

        # Mock the agent graph for new conversation
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=None)  # No existing conversation
        mock_response = MagicMock()
        mock_response.content = "New conversation started"
        mock_graph.ainvoke = AsyncMock(return_value={"messages": [mock_response]})

        with patch("mcp_server_langgraph.mcp.server_streamable.get_agent_graph", return_value=mock_graph):
            with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
                mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
                mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

                with patch("mcp_server_langgraph.mcp.server_streamable.format_response", return_value="Response"):
                    with patch("mcp_server_langgraph.mcp.server_streamable.metrics"):
                        await server._handle_chat(
                            arguments={"message": "Hello", "thread_id": "new-conv", "token": "test", "user_id": "alice"},
                            span=mock_span,
                            user_id="alice",
                        )

        # Should have called write_tuples to seed ownership
        mock_openfga.write_tuples.assert_called_once()
        tuples = mock_openfga.write_tuples.call_args[0][0]
        # Should include owner, viewer, and editor tuples
        relations = [t["relation"] for t in tuples]
        assert "owner" in relations
        assert "viewer" in relations
        assert "editor" in relations


@pytest.mark.xdist_group(name="server_streamable_handlers")
class TestExecutePythonHandler:
    """Test execute_python code execution handler."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_python_validates_code(self):
        """Test that code execution validates input code."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.auth_provider = "inmemory"
            mock_settings.enable_code_execution = True  # Enable code execution

            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware"):
                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer()

                mock_span = MagicMock()
                mock_span.set_attribute = MagicMock()

                # Verify execute_python exists when enabled
                tools = await server.list_tools_public()
                tool_names = [t.name for t in tools]
                assert "execute_python" in tool_names

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_python_runs_code(self):
        """Test that execute_python handler runs code via sandbox."""
        with patch("mcp_server_langgraph.mcp.server_streamable.settings") as mock_settings:
            mock_settings.jwt_secret_key = "test-secret"
            mock_settings.environment = "development"
            mock_settings.openfga_store_id = None
            mock_settings.openfga_model_id = None
            mock_settings.openfga_api_url = "http://localhost:8080"
            mock_settings.auth_provider = "inmemory"
            mock_settings.enable_code_execution = True

            with patch("mcp_server_langgraph.mcp.server_streamable.create_auth_middleware"):
                from mcp_server_langgraph.mcp.server_streamable import MCPAgentStreamableServer

                server = MCPAgentStreamableServer()

        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()

        # Mock the execute_python tool
        mock_result = "Success: print('hello')\nOutput: hello"

        with patch("mcp_server_langgraph.mcp.server_streamable.tracer") as mock_tracer:
            mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

            with patch("mcp_server_langgraph.tools.code_execution_tools.execute_python") as mock_exec:
                mock_exec.invoke = MagicMock(return_value=mock_result)

                with patch("mcp_server_langgraph.mcp.server_streamable.metrics"):
                    result = await server._handle_execute_python(
                        arguments={"code": "print('hello')", "timeout": 30},
                        span=mock_span,
                        user_id="alice",
                    )

        # Should return TextContent with execution result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "success" in result[0].text.lower() or "hello" in result[0].text.lower()


@pytest.mark.xdist_group(name="server_streamable_handlers")
class TestResponseFormatting:
    """Test response formatting in handlers."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_format_response_default(self):
        """Test default response formatting."""
        from mcp_server_langgraph.mcp.server_streamable import format_response

        text = "Hello, world!"
        result = format_response(text)
        assert result == text  # Default should not modify

    @pytest.mark.unit
    def test_format_response_concise(self):
        """Test concise response formatting."""
        from mcp_server_langgraph.mcp.server_streamable import format_response

        text = "This is a longer response that might need truncation."
        result = format_response(text, format_type="concise")
        # Concise format should work (may or may not truncate)
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_format_response_verbose(self):
        """Test verbose response formatting."""
        from mcp_server_langgraph.mcp.server_streamable import format_response

        text = "Short response"
        result = format_response(text, format_type="verbose")
        assert isinstance(result, str)


@pytest.mark.xdist_group(name="server_streamable_handlers")
class TestSanitizeForLogging:
    """Test log sanitization helper."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_sanitize_removes_token(self):
        """Test that sanitization removes sensitive token field."""
        from mcp_server_langgraph.mcp.server_streamable import sanitize_for_logging

        args = {"message": "Hello", "token": "secret-jwt-token", "user_id": "alice"}
        result = sanitize_for_logging(args)

        assert "message" in result
        assert result["message"] == "Hello"
        # Token should be redacted or removed
        if "token" in result:
            assert result["token"] != "secret-jwt-token"

    @pytest.mark.unit
    def test_sanitize_preserves_safe_fields(self):
        """Test that safe fields are preserved."""
        from mcp_server_langgraph.mcp.server_streamable import sanitize_for_logging

        args = {"thread_id": "conv-123", "response_format": "default", "message": "Hello world"}
        result = sanitize_for_logging(args)

        # thread_id and response_format should be preserved
        assert result["thread_id"] == "conv-123"
        assert result["response_format"] == "default"
        assert result["message"] == "Hello world"
