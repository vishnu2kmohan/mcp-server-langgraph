"""
Test conversation retrieval from checkpointer.

Ensures that _handle_get_conversation properly retrieves conversation
history from the LangGraph checkpointer.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer


@pytest.fixture
def mock_auth():
    """Mock authentication middleware."""
    auth_mock = AsyncMock()
    auth_mock.authenticate.return_value = {"authorized": True, "user_id": "alice"}
    auth_mock.authorize.return_value = True
    return auth_mock


@pytest.fixture
def mock_openfga():
    """Mock OpenFGA client."""
    return MagicMock()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_retrieval_success(mock_auth, mock_openfga):
    """Test successful conversation retrieval."""
    # Create server instance
    server = MCPAgentServer(openfga_client=mock_openfga)
    server.auth = mock_auth

    # Mock agent_graph.aget_state to return conversation state
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

    with patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()  # Checkpointing enabled
        mock_graph.aget_state = AsyncMock(return_value=mock_state)
        mock_get_graph.return_value = mock_graph

        # Create mock span
        mock_span = MagicMock()

        # Call handler
        arguments = {"thread_id": "test-thread-123", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")

        # Verify result
        assert len(result) == 1
        assert "Conversation history for thread test-thread-123" in result[0].text
        assert "Total messages: 4" in result[0].text
        assert "Hello, how are you?" in result[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_retrieval_no_checkpointer(mock_auth, mock_openfga):
    """Test conversation retrieval when checkpointing is disabled."""
    server = MCPAgentServer(openfga_client=mock_openfga)
    server.auth = mock_auth

    with patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.checkpointer = None  # Checkpointing disabled
        mock_get_graph.return_value = mock_graph

        mock_span = MagicMock()

        arguments = {"thread_id": "test-thread-123", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")

        assert len(result) == 1
        assert "Checkpointing is disabled" in result[0].text
        assert "ENABLE_CHECKPOINTING=true" in result[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_retrieval_not_found(mock_auth, mock_openfga):
    """Test conversation retrieval when thread doesn't exist."""
    server = MCPAgentServer(openfga_client=mock_openfga)
    server.auth = mock_auth

    # Mock empty state (conversation not found)
    mock_state = MagicMock()
    mock_state.values = None

    with patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_state)
        mock_get_graph.return_value = mock_graph

        mock_span = MagicMock()

        arguments = {"thread_id": "nonexistent-thread", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")

        assert len(result) == 1
        assert "No conversation history found" in result[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_retrieval_empty_messages(mock_auth, mock_openfga):
    """Test conversation retrieval when thread exists but has no messages."""
    server = MCPAgentServer(openfga_client=mock_openfga)
    server.auth = mock_auth

    # Mock state with empty messages
    mock_state = MagicMock()
    mock_state.values = {"messages": [], "next_action": "end"}

    with patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_state)
        mock_get_graph.return_value = mock_graph

        mock_span = MagicMock()

        arguments = {"thread_id": "empty-thread", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")

        assert len(result) == 1
        assert "has no messages yet" in result[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_retrieval_authorization_failure(mock_auth, mock_openfga):
    """Test conversation retrieval with authorization failure."""
    server = MCPAgentServer(openfga_client=mock_openfga)
    server.auth = mock_auth

    # Mock authorization to return False
    mock_auth.authorize.return_value = False

    mock_span = MagicMock()

    arguments = {"thread_id": "test-thread-123", "user_id": "alice"}

    with pytest.raises(PermissionError, match="Not authorized to view conversation"):
        await server._handle_get_conversation(arguments, mock_span, "alice")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_retrieval_error_handling(mock_auth, mock_openfga):
    """Test conversation retrieval error handling."""
    server = MCPAgentServer(openfga_client=mock_openfga)
    server.auth = mock_auth

    with patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.checkpointer = MagicMock()
        mock_graph.aget_state = AsyncMock(side_effect=Exception("Database error"))
        mock_get_graph.return_value = mock_graph

        mock_span = MagicMock()

        arguments = {"thread_id": "test-thread-123", "user_id": "alice"}
        result = await server._handle_get_conversation(arguments, mock_span, "alice")

        # Should return error message, not raise
        assert len(result) == 1
        assert "Error retrieving conversation" in result[0].text
        assert "Database error" in result[0].text
