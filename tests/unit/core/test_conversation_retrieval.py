"""
Test conversation retrieval from checkpointer.

Ensures that _handle_get_conversation properly retrieves conversation
history from the LangGraph checkpointer.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer
from tests.helpers.async_mock_helpers import configured_async_mock

pytestmark = [pytest.mark.unit]


@pytest.mark.xdist_group(name="conversation_retrieval")
class TestConversationRetrieval:
    """Test suite for conversation retrieval from checkpointer."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication middleware."""
        auth_mock = configured_async_mock(return_value=None)
        auth_mock.authenticate.return_value = {"authorized": True, "user_id": "alice"}
        auth_mock.authorize.return_value = True
        return auth_mock

    @pytest.fixture
    def mock_openfga(self):
        """Mock OpenFGA client with async check_permission."""
        mock = MagicMock()
        # check_permission is awaited, so must be AsyncMock
        mock.check_permission = AsyncMock(return_value=True)
        return mock

    @pytest.mark.asyncio
    async def test_conversation_retrieval_success(self, mock_auth, mock_openfga):
        """Test successful conversation retrieval."""
        # Create mock graph and inject into server
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_state = MagicMock()
        mock_state.values = {
            "messages": [
                HumanMessage(content="Hello, how are you?"),
                AIMessage(content="I'm doing well, thank you!"),
                HumanMessage(content="What's the weather like?"),
                AIMessage(content="I don't have access to weather data, but I can help with other questions."),
            ],
            "next_action": "end",
            "user_id": "alice",
        }
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        server = MCPAgentServer(openfga_client=mock_openfga, agent_graph=mock_graph)
        server.auth = mock_auth

        mock_span = MagicMock()
        arguments = {"thread_id": "test-thread-123", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")
        assert len(result) == 1
        assert "Conversation history for thread test-thread-123" in result[0].text
        assert "Total messages: 4" in result[0].text
        assert "Hello, how are you?" in result[0].text

    @pytest.mark.asyncio
    async def test_conversation_retrieval_no_checkpointer(self, mock_auth, mock_openfga):
        """Test conversation retrieval when checkpointing is disabled."""
        # Create mock graph with checkpointer disabled
        mock_graph = MagicMock()
        mock_graph.checkpointer = None

        server = MCPAgentServer(openfga_client=mock_openfga, agent_graph=mock_graph)
        server.auth = mock_auth

        mock_span = MagicMock()
        arguments = {"thread_id": "test-thread-123", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")
        assert len(result) == 1
        assert "Checkpointing is disabled" in result[0].text
        assert "ENABLE_CHECKPOINTING=true" in result[0].text

    @pytest.mark.asyncio
    async def test_conversation_retrieval_not_found(self, mock_auth, mock_openfga):
        """Test conversation retrieval when thread doesn't exist."""
        # Create mock state with no values (thread doesn't exist)
        mock_state = MagicMock()
        mock_state.values = None

        # Create mock graph with checkpointer enabled
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        server = MCPAgentServer(openfga_client=mock_openfga, agent_graph=mock_graph)
        server.auth = mock_auth

        mock_span = MagicMock()
        arguments = {"thread_id": "nonexistent-thread", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")
        assert len(result) == 1
        assert "No conversation history found" in result[0].text

    @pytest.mark.asyncio
    async def test_conversation_retrieval_empty_messages(self, mock_auth, mock_openfga):
        """Test conversation retrieval when thread exists but has no messages."""
        # Create mock state with empty messages list
        mock_state = MagicMock()
        mock_state.values = {"messages": [], "next_action": "end"}

        # Create mock graph with checkpointer enabled
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        server = MCPAgentServer(openfga_client=mock_openfga, agent_graph=mock_graph)
        server.auth = mock_auth

        mock_span = MagicMock()
        arguments = {"thread_id": "empty-thread", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")
        assert len(result) == 1
        assert "has no messages yet" in result[0].text

    @pytest.mark.asyncio
    async def test_conversation_retrieval_authorization_failure(self, mock_auth, mock_openfga):
        """Test conversation retrieval with authorization failure."""
        server = MCPAgentServer(openfga_client=mock_openfga)
        server.auth = mock_auth
        mock_auth.authorize.return_value = False
        # OpenFGA check also needs to deny access
        mock_openfga.check_permission = AsyncMock(return_value=False)
        mock_span = MagicMock()
        arguments = {"thread_id": "test-thread-123", "user_id": "alice"}
        with pytest.raises(PermissionError, match="Not authorized to view conversation"):
            await server._handle_get_conversation(arguments, mock_span, "alice")

    @pytest.mark.asyncio
    async def test_conversation_retrieval_error_handling(self, mock_auth, mock_openfga):
        """Test conversation retrieval error handling."""
        # Create mock graph that raises an error
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_graph.aget_state = AsyncMock(side_effect=Exception("Database error"))

        server = MCPAgentServer(openfga_client=mock_openfga, agent_graph=mock_graph)
        server.auth = mock_auth

        mock_span = MagicMock()
        arguments = {"thread_id": "test-thread-123", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")
        assert len(result) == 1
        assert "Error retrieving conversation" in result[0].text
        assert "Database error" in result[0].text
